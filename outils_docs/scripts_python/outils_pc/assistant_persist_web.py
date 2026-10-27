"""Page web « Assistant persist » : pose des questions et cree l'env d'une nouvelle carte (spec 2026-10-27 §5.3).

UTILISATION
    python outils_docs/scripts_python/outils_pc/assistant_persist_web.py [--http 7900] [--local] [--sans-navigateur]
    L'annuaire des outils (port 7600) la lance, ou la cible Custom « Assistant persist (page web) ».
    Regle d'acces : acces_web.py (ce PC sans jeton, autre appareil avec le jeton du lien de la console).

Rien n'est ecrit sans « Creer l'env » : couper la page ne laisse rien a moitie fait. Toute creation est refusee
pendant un build. Les POST passent un par un (verrou) : deux creations simultanees ne s'ecrasent pas, la seconde
voit son empreinte perimee. Les mots de passe ne sortent JAMAIS du serveur : l'apercu est calcule avec
secrets=None ("***"), le diff et les refus d'assistant_persist_creation sont masques.

Routes (les POST exigent l'en-tete X-Assistant-Persist: 1 et la meme origine ; JSON) :
    GET  /              la page (assistant_persist_page.PAGE)
    GET  /execution     {en_cours: false} : la cible Custom l'interroge pour savoir si la page tourne
    GET  /parc          {puces, bases: {puce: [env]}, base_defaut: {puce: env}, maitres, ids_pris: {id: [dossier]},
                        id_libre, reseaux, blocs: [{id, libelle, aide, puces, dependances}], erreur_modele}
    GET  /modele/etat   etat du modele (bandeau, fusion) : rempli par A6, {} ici
    GET  /interrompues  operations arretees en plein vol (marque restee dans leur sauvegarde)
    POST /apercu        {reponses} -> {persist, autoexec, refus, avertissements} (sans mot de passe, sans ecriture)
    POST /prepare       {reponses} -> assistant_persist_creation.prepare : diff, empreinte (vide si refus precoce), refus
    POST /creation      {reponses, empreinte} -> assistant_persist_creation.cree ; 409 si build, empreinte perimee, refus
    POST /interrompue/acquitte {nom} -> {acquitte: true} ; 400 nom inconnu
`reponses` = les champs de assistant_persist_generation.Reponses (puce, lieu, nom obligatoires).
"""

import argparse
import dataclasses
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import acces_web
import assistant_persist_creation as apc
import assistant_persist_generation as gen
import assistant_persist_modele as apm
import assistant_persist_parc as parc
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi
import fichiers_berry_sauvegarde as fbs

PORT_DEFAUT = 7900
DEPOT = Path(__file__).resolve().parents[3]
MAX_CORPS = 64 * 1024
CHAMPS = {f.name: f for f in dataclasses.fields(gen.Reponses)}
LISTES = ("blocs", "metiers")


def page():
    import assistant_persist_page
    return assistant_persist_page.PAGE


def builds_en_cours_defaut():
    import build_serie                          # meme detection que la page build (garde_build du depot)
    return build_serie.builds_en_cours_defaut()


def reponses_de(demande):
    """Reponses depuis le corps JSON ; ValueError (-> 400) si une forme ou une puce est fausse."""
    brut = demande.get("reponses")
    if not isinstance(brut, dict):
        raise ValueError("reponses : objet attendu")
    inconnus = sorted(set(brut) - set(CHAMPS))
    if inconnus:
        raise ValueError("reponses : champ(s) inconnu(s) : " + ", ".join(inconnus))
    for obligatoire in ("puce", "lieu", "nom"):
        if obligatoire not in brut:
            raise ValueError(f"reponses : {obligatoire} manquant")
    for cle, valeur in brut.items():
        if cle in LISTES:
            if not isinstance(valeur, list) or not all(isinstance(x, str) for x in valeur):
                raise ValueError(f"{cle} : liste de chaines attendue")
        elif cle == "id":
            if type(valeur) is not int:
                raise ValueError("id : entier attendu")
        elif cle == "squelettes":
            if type(valeur) is not bool:
                raise ValueError("squelettes : booleen attendu")
        elif not isinstance(valeur, str):
            raise ValueError(f"{cle} : chaine attendue")
    if brut["puce"] not in parc.PREFIXES:
        raise ValueError(f"puce inconnue : {brut['puce']!r} ({', '.join(parc.PREFIXES)} attendues)")
    return gen.Reponses(**brut)


def _modele(racine):
    """(modele, erreur) : le modele illisible n'empeche pas la page de s'ouvrir."""
    try:
        return apm.charge_modele(racine), ""
    except ValueError as exc:
        return None, str(exc)


def donnees_parc(racine):
    modele, erreur = _modele(racine)
    ini, bases = fbi.lit_sections(racine), {p: [] for p in parc.PREFIXES}
    for env in ini.envs_cenv():
        puce = next((p for p, pre in parc.PREFIXES.items() if env.split("-")[0] == pre), None)
        if puce and fbe.est_base(env):
            bases[puce].append(env)
    blocs = [{k: b.get(k, "") for k in ("id", "libelle", "aide", "puces", "dependances")}
             for b in (modele["blocs"] if modele else [])]
    return {"puces": list(parc.PREFIXES), "bases": bases,
            "base_defaut": {p: parc.base_par_defaut(racine, p) for p in parc.PREFIXES},
            "maitres": parc.maitres(racine), "ids_pris": {str(i): d for i, d in parc.ids_pris(racine).items()},
            "id_libre": parc.id_libre(racine), "reseaux": parc.reseaux(racine), "blocs": blocs, "erreur_modele": erreur}


def apercu(racine, r):
    """Persist et autoexec avec "***" a la place des mots de passe ; rien n'est ecrit ni lu des secrets."""
    res = {"persist": "", "autoexec": "", "refus": [], "avertissements": []}
    try:
        modele = apm.charge_modele(racine)
        v = gen.variables(racine, r)
        obj = gen.persist(modele, r, v, None)
        texte_auto, listes = gen.autoexec(modele, r), gen.listes_cenv(modele, r)
        res["refus"] = gen.coherence(modele, r, obj, texte_auto, listes, racine)
        res["persist"], res["autoexec"] = gen.texte_persist(obj, "\n"), texte_auto
    except (ValueError, KeyError) as exc:
        res["refus"].append(str(exc.args[0]) if isinstance(exc, KeyError) else str(exc))
        return res
    if r.role == "esclave" and r.id in parc.ids_pris(racine):
        res["avertissements"].append(f"id {r.id} deja pris par {', '.join(parc.ids_pris(racine)[r.id])} : deux "
                                     "esclaves de meme id se repondent l'un a l'autre")
    return res


def fabrique_gestionnaire(acces, racine, builds_en_cours, etat_modele):
    verrou = threading.Lock()

    def traite_post(chemin, demande):
        with verrou:                                  # verification de l'empreinte et ecriture, d'un seul tenant
            return _traite_post(chemin, demande)

    def _traite_post(chemin, demande):
        if chemin == "/apercu":
            return apercu(racine, reponses_de(demande))
        if chemin == "/prepare":
            return apc.prepare(racine, reponses_de(demande))
        if chemin == "/creation":
            empreinte = demande.get("empreinte")
            if not isinstance(empreinte, str) or not empreinte:
                raise ValueError("empreinte : chaine non vide attendue (refaire « Voir le diff »)")
            return apc.cree(racine, reponses_de(demande), empreinte, builds_en_cours)
        if chemin == "/interrompue/acquitte":
            nom = demande.get("nom")
            if not isinstance(nom, str) or not fbs.acquitte(nom):
                raise ValueError(f"operation interrompue inconnue : {nom!r}")
            return {"acquitte": True}
        raise LookupError(chemin)

    class Gestionnaire(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _envoie(self, statut, corps, type_mime="text/plain; charset=utf-8"):
            self.send_response(statut)
            self.send_header("Content-Type", type_mime)
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corps)

        def _json(self, donnees, statut=200):
            self._envoie(statut, json.dumps(donnees, ensure_ascii=False).encode("utf-8"), "application/json")

        def _erreur_inattendue(self, erreur):
            """500 avec le message, au lieu d'une connexion coupee (« outil injoignable » dans la page)."""
            self._envoie(500, f"erreur inattendue : {type(erreur).__name__} : {erreur}".encode("utf-8"))

        def do_GET(self):
            if not acces.controle(self):
                return
            chemin = urlsplit(self.path).path
            try:
                if chemin == "/":
                    self._envoie(200, page().encode("utf-8"), "text/html; charset=utf-8")
                elif chemin == "/execution":
                    self._json({"en_cours": False})
                elif chemin == "/parc":
                    self._json(donnees_parc(racine))
                elif chemin == "/modele/etat":
                    self._json(etat_modele())
                elif chemin == "/interrompues":
                    self._json({"interrompues": fbs.interrompues()})
                else:
                    self._envoie(404, b"introuvable")
            except ValueError as erreur:
                self._envoie(400, str(erreur).encode("utf-8"))
            except Exception as erreur:                     # fichier verrouille, JSON tronque... : le dire
                self._erreur_inattendue(erreur)

        def do_POST(self):
            if not acces.controle(self):
                return
            if self.headers.get("X-Assistant-Persist") != "1" or not acces.origine_autorisee(self):
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
    options = argparse.ArgumentParser(description="Page web de l'assistant de creation du persist d'une carte.")
    options.add_argument("--http", type=int, default=PORT_DEFAUT, help=f"port de la page (defaut {PORT_DEFAUT})")
    acces_web.ajoute_options(options)
    args = options.parse_args()

    # Nom de la fiche de presence, en litteral : identique a nom_acces de l'outil « assistant_persist »
    # (annuaire_registre.py), sinon la tuile ne retrouve pas l'outil ; test_annuaire le verifie sur cette ligne.
    acces = acces_web.Acces(args.http, args.local, "Assistant persist")
    try:
        serveur = ThreadingHTTPServer((acces.hote, args.http),
                                      fabrique_gestionnaire(acces, DEPOT, builds_en_cours_defaut, lambda: {}))
    except OSError as erreur:
        print(f"ERREUR : port {args.http} indisponible ({erreur}). L'outil tourne peut-etre deja.")
        return 1
    serveur.daemon_threads = True
    acces.annonce(not args.sans_navigateur)
    print("Ctrl+C pour arreter (rien n'est ecrit sans « Creer l'env »).", flush=True)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
