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
                        id_libre, reseaux, blocs: [{id, libelle, aide, puces, dependances}], erreur_modele,
                        broches: {puce: [GPIO]}, erreur_broches: {puce: message}, groupes: [{id, singulier, gabarit}]}  (editeur des entrees/sorties)
    GET  /modele/etat   {ajouts, disparues, divergentes, a_completer, erreur} : bandeau du modele (A6) ; ajouts = cles
                        fusionnees d'office au demarrage, erreur = modele illisible (rien n'est alors fusionne ni ecrit)
    GET  /interrompues  operations arretees en plein vol (marque restee dans leur sauvegarde)
    POST /apercu        {reponses} -> {persist, autoexec, refus, avertissements} (sans mot de passe, sans ecriture)
    POST /prepare       {reponses} -> assistant_persist_creation.prepare : diff, empreinte (vide si refus precoce), refus
    POST /creation      {reponses, empreinte} -> assistant_persist_creation.cree ; 409 si build, empreinte perimee, refus
    POST /modele/prepare {} -> {diff, empreinte, retraits, alignements} : retraits et alignements proposes, rien d'ecrit
        {relue: chemin} -> {diff, empreinte} : retrait de ce chemin de a_completer (400 s'il n'y est pas) ; idem a /applique
    POST /modele/applique {empreinte} -> {applique, retraits, alignements} ; 409 si build, empreinte perimee, rien a faire
    POST /interrompue/acquitte {nom} -> {acquitte: true} ; 400 nom inconnu
    GET  /env?nom=      assistant_persist_modification.charge_env : reponses relues de la carte ; 404 inconnu, 400 illisible
    POST /modification/prepare {env, reponses} -> {diff, empreinte, vide, chemins, avertissements, refus} (sans ecriture)
    POST /modification {env, reponses, empreinte} -> {modifie, diff, sauvegarde} ; 409 build, empreinte, ecart inapplicable ;
        400 aucun changement
    POST /suppression/prepare {env} -> fichiers_berry_suppression.prepare_suppression + elements (liste lisible)
    POST /suppression {env, empreinte} -> {supprime, dossier_sauvegarde, sauvegarde} ; 409 ; 404 env inconnu
(+ cartes dans GET /parc : [{env, dossier, puce}])
`reponses` = les champs de assistant_persist_generation.Reponses (puce, lieu, nom obligatoires) ; `elements` =
{groupe: [element, ...]} et `elements_groupe` = {groupe: {reglage: valeur}} (groupes de assistant_persist_elements).
"""

import argparse
import dataclasses
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import acces_web
import assistant_persist_creation as apc
import assistant_persist_elements as ape
import assistant_persist_generation as gen
import assistant_persist_modele as apm
import assistant_persist_modification as apm2
import assistant_persist_parc as parc
import assistant_persist_relue as apr
from annuaire_outils import hote_autorise
import fichiers_berry_creation as fbc
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi
import fichiers_berry_sauvegarde as fbs
import fichiers_berry_suppression as fbx

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


def _forme_elements(cle, valeur):
    """elements : {groupe: [objet]} ; elements_groupe : {groupe: objet}. Les groupes sont ceux de GROUPES_ELEMENTS."""
    if not isinstance(valeur, dict):
        raise ValueError(f"{cle} : objet attendu")
    for groupe, contenu in valeur.items():
        if groupe not in ape.GROUPES_ELEMENTS:
            raise ValueError(f"{cle} : groupe inconnu {groupe!r} ({', '.join(ape.GROUPES_ELEMENTS)} attendus)")
        if cle == "elements" and not (isinstance(contenu, list) and all(isinstance(e, dict) for e in contenu)):
            raise ValueError(f"{cle}.{groupe} : liste d'objets attendue")
        if cle == "elements_groupe" and not isinstance(contenu, dict):
            raise ValueError(f"{cle}.{groupe} : objet attendu")


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
        elif cle in ("elements", "elements_groupe"):
            _forme_elements(cle, valeur)
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


def demarre_modele(racine, builds_en_cours=None):
    """Fusion AUTOMATIQUE des cles nouvelles du parc dans le modele (decision 14), sans validation, ecrite par une
    Transaction (nature modele-auto). Liste des chemins ajoutes ; [] si le parc est couvert, si le modele est
    illisible (ni fusion ni reecriture : le bandeau rouge le dit) ou si un build tourne (ecriture du depot refusee)."""
    modele, _ = _modele(racine)
    if modele is None:
        return []
    if builds_en_cours is not None:
        builds = builds_en_cours()
        if builds is None or builds:
            print("Modele : fusion des cles nouvelles reportee (build en cours ou indetectable).", flush=True)
            return []
    neuf, ajouts = apm.fusionne_nouvelles(racine, modele)
    if ajouts:
        apm.ecrit_modele(racine, neuf, apm.NATURE_AUTO)
        print(f"Modele : {len(ajouts)} cle(s) nouvelle(s) du parc ajoutee(s), a completer.", flush=True)
    return ajouts


def demarre_sur(racine, builds_en_cours=None):
    """(ajouts, erreur) : demarre_modele, mais toute exception (OSError, ImportError de build_serie...) reporte la
    fusion au lieu d'arreter l'outil ; le message va dans /modele/etat.erreur."""
    try:
        return demarre_modele(racine, builds_en_cours), ""
    except Exception as exc:
        message = f"fusion du modele impossible : {type(exc).__name__} : {exc}"
        print(f"Modele : {message}.", flush=True)
        return [], message


def etat_modele(racine, ajouts, erreur_demarrage=""):
    """Etat pour le bandeau : calcule a chaque lecture (le parc et le modele peuvent changer pendant la session)."""
    modele, erreur = _modele(racine)
    if modele is None:
        return {"ajouts": [], "disparues": [], "divergentes": {}, "a_completer": [], "erreur": erreur}
    e = apm.ecarts(racine, modele)
    return {"ajouts": list(ajouts), "disparues": e["disparues"], "divergentes": e["divergentes"],
            "a_completer": apm.a_completer(modele), "erreur": erreur_demarrage,
            "valeurs": {c: apr.valeur_affichee(modele, c) for c in apm.a_completer(modele)}}


def donnees_parc(racine):
    modele, erreur = _modele(racine)
    ini, bases = fbi.lit_sections(racine), {p: [] for p in parc.PREFIXES}
    for env in ini.envs_cenv():
        puce = next((p for p, pre in parc.PREFIXES.items() if env.split("-")[0] == pre), None)
        if puce and fbe.est_base(env):
            bases[puce].append(env)
    broches, erreurs_broches = {}, {}
    for p in parc.PREFIXES:                         # configGlobal.be reformate : la page s'ouvre, l'erreur est affichee
        try:
            broches[p] = ape.broches_valides(p, racine)
        except ValueError as exc:
            broches[p], erreurs_broches[p] = [], str(exc)
    blocs = [{k: b.get(k, "") for k in ("id", "libelle", "aide", "puces", "dependances")}
             for b in (modele["blocs"] if modele else [])]
    return {"puces": list(parc.PREFIXES), "bases": bases,
            "base_defaut": {p: parc.base_par_defaut(racine, p) for p in parc.PREFIXES},
            "maitres": parc.maitres(racine), "ids_pris": {str(i): d for i, d in parc.ids_pris(racine).items()},
            "id_libre": parc.id_libre(racine), "reseaux": parc.reseaux(racine), "blocs": blocs, "erreur_modele": erreur,
            "broches": broches, "erreur_broches": erreurs_broches, "cartes": apm2.cartes(racine),
            "groupes": [{"id": g, "singulier": ape.singulier(modele, g), "gabarit": ape.gabarits_elements(modele)[g]}
                        for g in ape.GROUPES_ELEMENTS] if modele else []}


def _env_de(demande):
    env = demande.get("env")
    if not isinstance(env, str) or not env:
        raise ValueError("env : chaine non vide attendue")
    return env


def _empreinte_de(demande, refaire):
    empreinte = demande.get("empreinte")
    if not isinstance(empreinte, str) or not empreinte:
        raise ValueError(f"empreinte : chaine non vide attendue (refaire {refaire})")
    return empreinte


def elements_supprimes(racine, prep):
    """Liste lisible des elements retires, tiree du diff de prepare_suppression (en-tetes `--- fichier`)."""
    env, touches = prep["env"], re.findall(r"^--- (\S+)", prep["diff"], re.M)
    res = [f"section [env:{env}] de {fbi.FICHIER_CENV}"]
    if fbc.FICHIER_H in touches:
        define = fbx.define_de(fbi.lit_sections(racine), env)
        res.append(f"section de {fbc.FICHIER_H}" + (f" ({define})" if define else ""))
    if fbx.OVERRIDE in touches:
        res.append(f"reference a {env} ou a son dossier dans {fbx.OVERRIDE} (default_envs, data_dir)")
    if prep["dossier_sauvegarde"]:
        res.append(f"dossier {prep['dossier']} renomme en {prep['dossier_sauvegarde']}")
    return res


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
        if chemin in ("/prepare", "/creation"):
            apm.charge_modele(racine)                  # modele illisible : 400 qui cite le fichier et sa ligne
        if chemin == "/prepare":
            return apc.prepare(racine, reponses_de(demande))
        if chemin == "/creation":
            empreinte = demande.get("empreinte")
            if not isinstance(empreinte, str) or not empreinte:
                raise ValueError("empreinte : chaine non vide attendue (refaire « Voir le diff »)")
            return apc.cree(racine, reponses_de(demande), empreinte, builds_en_cours)
        if chemin == "/modification/prepare":
            return apm2.prepare_modification(racine, _env_de(demande), reponses_de(demande))
        if chemin == "/modification":
            return apm2.modifie(racine, _env_de(demande), reponses_de(demande),
                                _empreinte_de(demande, "« Voir le diff »"), builds_en_cours)
        if chemin == "/suppression/prepare":
            prep = fbx.prepare_suppression(racine, _env_de(demande))
            return {**prep, "elements": elements_supprimes(racine, prep)}
        if chemin == "/suppression":
            return fbx.supprime(racine, _env_de(demande), _empreinte_de(demande, "le diff"), builds_en_cours)
        if chemin == "/modele/prepare":
            if "relue" in demande:
                return apr.propose_relue(racine, demande["relue"])
            return apm.propose_mise_a_jour(racine, apm.charge_modele(racine))      # ValueError si illisible -> 400
        if chemin == "/modele/applique":
            empreinte = demande.get("empreinte")
            if not isinstance(empreinte, str) or not empreinte:
                raise ValueError("empreinte : chaine non vide attendue (refaire « Mettre a jour le modele »)")
            builds = builds_en_cours()
            if builds is None or builds:
                raise RuntimeError("un build tourne ou n'est pas detectable : modele non modifie")
            if "relue" in demande:
                return apr.applique_relue(racine, demande["relue"], empreinte)
            return apm.applique_mise_a_jour(racine, empreinte)
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

        def _controle(self):
            """acces.controle, puis le Host d'un client local (DNS rebinding, comme l'annuaire). False : reponse envoyee."""
            if not acces.controle(self):
                return False
            if not hote_autorise(self, acces.port):
                self.close_connection = True
                self._envoie(403, b"Hote refuse")
                return False
            return True

        def do_GET(self):
            if not self._controle():
                return
            chemin = urlsplit(self.path).path
            try:
                if chemin == "/":
                    self._envoie(200, page().encode("utf-8"), "text/html; charset=utf-8")
                elif chemin == "/execution":
                    self._json({"en_cours": False})
                elif chemin == "/parc":
                    self._json(donnees_parc(racine))
                elif chemin == "/env":
                    self._json(apm2.charge_env(racine, _env_de({"env": (parse_qs(urlsplit(self.path).query).get("nom") or [""])[0]})))
                elif chemin == "/modele/etat":
                    self._json(etat_modele())
                elif chemin == "/interrompues":
                    self._json({"interrompues": fbs.interrompues()})
                else:
                    self._envoie(404, b"introuvable")
            except KeyError as erreur:
                self._erreur_inattendue(erreur)
            except LookupError as erreur:
                self._envoie(404, str(erreur).encode("utf-8"))
            except ValueError as erreur:
                self._envoie(400, str(erreur).encode("utf-8"))
            except Exception as erreur:                     # fichier verrouille, JSON tronque... : le dire
                self._erreur_inattendue(erreur)

        def do_POST(self):
            if not self._controle():
                return
            if self.headers.get("X-Assistant-Persist") != "1" or not acces.origine_autorisee(self):
                self.close_connection = True
                self._envoie(403, b"refuse")
                return
            try:
                try:
                    longueur = int(self.headers.get("Content-Length", "0") or 0)
                except ValueError:
                    longueur = -1
                if longueur < 0:                              # non entier ou negatif : read(-1) attendrait la fin du flux
                    self.close_connection = True              # corps non lu : la connexion ne doit pas resservir
                    raise ValueError("Content-Length invalide (entier positif attendu)")
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
    ajouts, erreur_demarrage = demarre_sur(DEPOT, builds_en_cours_defaut)    # la page s'ouvre quand meme
    try:
        serveur = ThreadingHTTPServer((acces.hote, args.http),
                                      fabrique_gestionnaire(acces, DEPOT, builds_en_cours_defaut, lambda: etat_modele(DEPOT, ajouts, erreur_demarrage)))
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
