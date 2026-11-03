"""Atelier des graphiques (page web, port 7950) : pages de graphiques d'une carte S3/P4, apercu par le vrai moteur.

UTILISATION
    python outils_docs/scripts_python/outils_pc/atelier_graphiques_web.py [--http 7950] [--local] [--sans-navigateur]
    Regle d'acces : acces_web.py (ce PC sans jeton, autre appareil avec le jeton du lien de la console).

Assemble les modules du plan atelier-graphiques : series et valeurs de la carte (A4, lecture seule, repli sur le depot),
conseil de style (A5), validation de la description (A1), diff et ecriture du depot (A6, refusee pendant un build).
Rien n'est ecrit sans « Ecrire dans le depot » : couper l'outil ne laisse rien a moitie fait.

Routes (les POST exigent l'en-tete X-Atelier-Graphiques: 1 et la meme origine ; JSON) :
    GET  /             la page (atelier_graphiques_page.PAGE)
    GET  /envs         {envs: [{nom, ip, exclut_echarts, exclut_liquidfill}]} : cartes S3/P4 du cenv (« Mes cartes »)
    GET  /series       ?env= : atelier_graphiques_series.series ; carte muette -> les /valeurs suivantes sont simulees
                       sans attendre la carte, jusqu'a la prochaine lecture des series
    GET  /valeurs      ?env=&c=<chemins>&p=direct|jour|mois[&m=AAAA-MM][&n=<historique>] : formes de la carte
                       (/pages?f=valeurs, /histo) ; en-tete X-Source: carte|depot. Le DERNIER c l'emporte : la page
                       y ajoute les parametres d'URL du lecteur de la carte (paquets de 12 chemins en direct)
    GET  /description  ?env= : {description (null si aucune), solidifie, erreur}
    GET  /moteur/<nom> fichiers du moteur de data/sd (liste fermee MOTEUR) ; ECharts et liquidfill decompresses
    POST /conseil      {intention, series, destination, historique} -> atelier_graphiques_conseil.propose
    POST /valide       {description} -> {motifs}
    POST /diff         {env, description|null, solidifier} -> {fichiers: [{chemin, avant, apres, diff, ajouts,
                       retraits}], empreinte, signaux} ; description null = derniere page retiree
    POST /ecrire       {env, description|null, solidifier, empreinte} -> {ecrits} ; 409 si build ou empreinte perimee
Refus : 400 (saisie, motif en texte), 404 (env inconnu ou hors S3/P4), 409 (build, empreinte), 500 (inattendu).
"""

import argparse
import difflib
import gzip
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import acces_web
import atelier_graphiques_conseil as agc
import atelier_graphiques_description as agd
import atelier_graphiques_ecriture as age
import atelier_graphiques_series as ags
import build_envs
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi

PORT_DEFAUT = 7950
DEPOT = Path(__file__).resolve().parents[3]
MAX_CORPS = 64 * 1024
MAX_CHEMINS = agd.BORNES["graphiques"] * agd.BORNES["series"]
JS = "application/javascript; charset=utf-8"
MOTEUR = {"pages_graphiques.js": ("js/pages_graphiques.js", JS), "pages_graphiques_formule.js": ("js/pages_graphiques_formule.js", JS),
          "pages_graphiques.html": ("html/pages_graphiques.html", "text/html; charset=utf-8"),
          "pages_graphiques.css": ("css/pages_graphiques.css", "text/css; charset=utf-8"),
          "echarts.min.js": ("js/echarts.min.js.gz", JS), "echarts-liquidfill.min.js": ("js/echarts-liquidfill.min.js.gz", JS)}
ECHARTS, LIQUIDFILL = "echarts.min.js.gz", age.LIQUIDFILL
RE_MOIS = re.compile(r"\d{4}-(0[1-9]|1[0-2])")
RE_NOM = re.compile(r"[A-Za-z0-9_]{1,32}")


def builds_en_cours_defaut():
    import build_serie                          # meme detection que la page build (garde_build du depot)
    return build_serie.builds_en_cours_defaut()


def cartes(racine):
    """Noms des cartes S3/P4 du cenv (« Mes cartes »), dans l'ordre du fichier ; rapide (cenv seul)."""
    ini = fbi.lit_sections(racine)
    return ini, [e["nom"] for e in fbe.envs_proposes(racine) if e["famille"] == "cartes"
                 and any(s.startswith(("env:tasmota32s3", "env:tasmota32p4")) for s in ini.chaine(e["nom"]))]


def envs(racine):
    """Cartes S3/P4, avec leur adresse et l'exclusion d'ECharts et de liquidfill de leur FS (liste_envs : quelques s)."""
    ini, noms = cartes(racine)
    ips = {e.nom: e.ip for e in build_envs.liste_envs(racine)}
    res = []
    for nom in noms:
        exclus = {Path(x.chemin).name for x in fbi.resout(ini, nom, fbe.EXCLUDE)}
        res.append({"nom": nom, "ip": ips.get(nom, ""), "exclut_echarts": ECHARTS in exclus,
                    "exclut_liquidfill": LIQUIDFILL in exclus})
    return res


def env_atelier(racine, env):
    if env not in cartes(racine)[1]:
        raise LookupError(f"env inconnu ou hors cartes S3/P4 : {env!r}")
    return env


def description_de(racine, env):
    chemin = Path(racine) / fbe.dossier_carte(env) / age.DESCRIPTION
    ini = fbi.lit_sections(racine)
    solidifie = {Path(f).name for f in age.SOLIDES} <= {Path(x.chemin).name for x in fbi.resout(ini, env, fbe.SOLIDIFY)}
    if not chemin.is_file():
        return {"description": None, "solidifie": solidifie, "erreur": ""}
    try:
        return {"description": json.loads(chemin.read_text(encoding="utf-8")), "solidifie": solidifie, "erreur": ""}
    except (OSError, ValueError) as e:
        return {"description": None, "solidifie": solidifie, "erreur": f"{age.DESCRIPTION} illisible : {e}"}


def avec_diffs(prevu):
    for f in prevu["fichiers"]:
        lignes = list(difflib.unified_diff((f["avant"] or "").splitlines(), (f["apres"] or "").splitlines(),
                                           "a/" + f["chemin"], "b/" + f["chemin"], lineterm=""))
        f["diff"] = "\n".join(lignes)
        f["ajouts"] = sum(1 for l in lignes[2:] if l.startswith("+"))
        f["retraits"] = sum(1 for l in lignes[2:] if l.startswith("-"))
    return prevu


def parametres_valeurs(params):
    """(chemins, periode, mois, nom) valides d'une requete /valeurs ; ValueError sinon."""
    un = lambda k, defaut=None: params.get(k, [defaut])[-1]
    chemins = [c for c in (un("c", "") or "").split(",") if c]
    periode, mois, nom = un("p", "direct"), un("m"), un("n", ags.NOM)
    if periode not in ("direct", "jour", "mois"):
        raise ValueError(f"periode inconnue : {periode!r}")
    if mois is not None and not RE_MOIS.fullmatch(mois):
        raise ValueError(f"mois AAAA-MM attendu : {mois!r}")
    if not RE_NOM.fullmatch(nom):
        raise ValueError(f"nom d'historique invalide : {nom!r}")
    if len(chemins) > MAX_CHEMINS:
        raise ValueError(f"trop de series : {len(chemins)} > {MAX_CHEMINS}")
    for c in chemins:
        if not agd._chemin_ok(c):
            raise ValueError(f"chemin de serie invalide : {c!r}")
    return chemins, periode, mois, nom


def _muette(ip, chemin, delai):
    raise OSError("carte muette a la derniere lecture des series")


def fabrique_gestionnaire(acces, racine, builds_en_cours, get=None):
    verrou = threading.Lock()
    muettes = {}                                  # env -> True : series lues au depot, ne pas attendre la carte

    def corps_ecriture(demande):
        env = env_atelier(racine, demande.get("env"))
        desc, solidifier = demande.get("description"), demande.get("solidifier")
        if desc is not None and not isinstance(desc, dict):
            raise ValueError("description : objet ou null attendu")
        if not isinstance(solidifier, bool):
            raise ValueError("solidifier : vrai ou faux attendu")
        return env, desc, solidifier

    def traite_post(chemin, demande):
        if chemin == "/conseil":
            return agc.propose(demande.get("intention"), demande.get("series"), demande.get("destination"),
                               demande.get("historique"))
        if chemin == "/valide":
            return {"motifs": agd.valide(demande.get("description"))}
        if chemin == "/diff":
            with verrou:
                return avec_diffs(age.prevoit(racine, *corps_ecriture(demande)))
        if chemin == "/ecrire":
            empreinte = demande.get("empreinte")
            if not isinstance(empreinte, str):
                raise ValueError("empreinte : chaine attendue")
            with verrou:                          # verification de l'empreinte et ecriture, d'un seul tenant
                return {"ecrits": age.ecrit(racine, *corps_ecriture(demande), empreinte, builds_en_cours)}
        raise LookupError(chemin)

    class Gestionnaire(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _envoie(self, statut, corps, type_mime="text/plain; charset=utf-8", entetes=()):
            self.send_response(statut)
            self.send_header("Content-Type", type_mime)
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            for cle, valeur in entetes:
                self.send_header(cle, valeur)
            self.end_headers()
            self.wfile.write(corps)

        def _json(self, donnees, statut=200, entetes=()):
            self._envoie(statut, json.dumps(donnees, ensure_ascii=False).encode("utf-8"), "application/json", entetes)

        def _moteur(self, nom):
            if nom not in MOTEUR:                 # liste fermee : ni « .. » ni autre fichier du depot
                raise LookupError(f"fichier du moteur inconnu : {nom!r}")
            rel, mime = MOTEUR[nom]
            octets = (Path(racine) / "data" / "sd" / rel).read_bytes()
            self._envoie(200, gzip.decompress(octets) if rel.endswith(".gz") else octets, mime)

        def do_GET(self):
            if not acces.controle(self):
                return
            url = urlsplit(self.path)
            params = parse_qs(url.query)
            env = lambda: env_atelier(racine, params.get("env", [""])[0])
            try:
                if url.path == "/":
                    import atelier_graphiques_page
                    self._envoie(200, atelier_graphiques_page.PAGE.encode("utf-8"), "text/html; charset=utf-8")
                elif url.path == "/envs":
                    self._json({"envs": envs(racine)})
                elif url.path == "/series":
                    e = env()
                    s = ags.series(racine, e, get=get)
                    muettes[e] = s["source"] != "carte"
                    self._json(s)
                elif url.path == "/valeurs":
                    e = env()
                    chemins, periode, mois, nom = parametres_valeurs(params)
                    v = ags.valeurs(racine, e, chemins, periode, get=_muette if muettes.get(e) else get, nom=nom, mois=mois)
                    self._json(v, entetes=[("X-Source", v["source"])])
                elif url.path == "/description":
                    self._json(description_de(racine, env()))
                elif url.path.startswith("/moteur/"):
                    self._moteur(url.path[len("/moteur/"):])
                else:
                    self._envoie(404, b"introuvable")
            except (KeyError, IndexError) as erreur:       # LookupError, mais un bogue : pas un « introuvable »
                self._erreur_inattendue(erreur)
            except LookupError as erreur:
                self._envoie(404, str(erreur).encode("utf-8"))
            except ValueError as erreur:
                self._envoie(400, str(erreur).encode("utf-8"))
            except Exception as erreur:
                self._erreur_inattendue(erreur)

        def _erreur_inattendue(self, erreur):
            """500 avec le message, au lieu d'une connexion coupee (« outil injoignable » dans la page)."""
            self._envoie(500, f"erreur inattendue : {type(erreur).__name__} : {erreur}".encode("utf-8"))

        def do_POST(self):
            if not acces.controle(self):
                return
            if self.headers.get("X-Atelier-Graphiques") != "1" or not acces.origine_autorisee(self):
                self.close_connection = True
                self._envoie(403, b"refuse")
                return
            try:
                longueur = int(self.headers.get("Content-Length", "0") or 0)
                if longueur > MAX_CORPS:
                    self.close_connection = True              # corps non lu : la connexion ne doit pas resservir
                    self._envoie(413, "corps trop gros (64 Ko au plus)".encode("utf-8"))
                    return
                demande = json.loads(self.rfile.read(longueur).decode("utf-8") or "{}")
                if not isinstance(demande, dict):
                    raise ValueError("corps JSON attendu")
                self._json(traite_post(urlsplit(self.path).path, demande))
            except (KeyError, IndexError) as erreur:
                self._erreur_inattendue(erreur)
            except LookupError as erreur:
                self._envoie(404, str(erreur).encode("utf-8"))
            except (ValueError, TypeError) as erreur:
                self._envoie(400, str(erreur).encode("utf-8"))
            except RuntimeError as erreur:
                self._envoie(409, str(erreur).encode("utf-8"))
            except Exception as erreur:
                self._erreur_inattendue(erreur)

    return Gestionnaire


def principal():
    options = argparse.ArgumentParser(description="Atelier des graphiques : pages de graphiques des cartes S3/P4.")
    options.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(options)
    args = options.parse_args()
    acces = acces_web.Acces(args.http, args.local, "Atelier des graphiques")
    try:
        serveur = ThreadingHTTPServer((acces.hote, args.http), fabrique_gestionnaire(acces, DEPOT, builds_en_cours_defaut))
    except OSError as erreur:
        print(f"ERREUR : port {args.http} indisponible ({erreur}). L'outil tourne peut-etre deja.")
        return 1
    serveur.daemon_threads = True
    acces.annonce(not args.sans_navigateur)
    print("Ctrl+C pour arreter (rien n'est ecrit sans « Ecrire dans le depot »).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
