"""Banc des remarques de l'atelier des ecrans (atelier_ecrans_remarques.py), plan atelier-ecrans A7.

UTILISATION (aucune carte, aucun vrai claude ; ~1 min)
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_ecrans_remarques.py

Copie temporaire du depot mise sous git (le controle « rien n'a change » lit git status) ; `claude` remplace par un
faux programme (FAUX_CLAUDE = ok | inconnu | attribut | ecrit | code | lent | illisible). Verifie : epingler, repondre,
refuser ; propositions valides ecrites par le MODULE dans remarques.json ; id inconnu, attribut hors catalogue, police
non compilee rejetes ; faux claude qui modifie un fichier du depot -> rejet, remarques.json intact ; claude absent, code
d'erreur, delai depasse -> echec ; second lancement pendant un traitement -> refus ; options de lecture seule passees ;
routes HTTP (dont le refus du lancement depuis un autre appareil). Code de sortie 0 = vert.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import acces_web                         # noqa: E402
import atelier_ecrans_catalogue as cat    # noqa: E402
import atelier_ecrans_description as aed  # noqa: E402
import atelier_ecrans_ecriture as aee     # noqa: E402
import atelier_ecrans_remarques as aer    # noqa: E402
import atelier_ecrans_web as aew          # noqa: E402
import test_atelier_ecrans_web as taw     # noqa: E402

ENV = "tasmota32s3-bureau-ecran-debits-pac"
ECHECS = []
POLICE_28 = "A:sd/polices/RobotoCondensed-Regular.ttf-28"
FAUX = r'''
import json, os, sys, time
mode = os.environ.get("FAUX_CLAUDE", "ok")
open(os.environ["FAUX_CLAUDE_ARGV"], "w").write(json.dumps({"argv": sys.argv[1:], "stdin": sys.stdin.read()}))
op = {"op": "modifie", "page": 1, "id": 11, "attributs": {"text_font": "%s"}}
if mode == "inconnu": op["id"] = 999
if mode == "attribut": op["attributs"] = {"couleur_magique": 1}
if mode == "police": op["attributs"] = {"text_font": 22}
if mode == "ecrit": open("platformio_override.ini", "a").write("\n; ecrit par le faux claude\n")
if mode == "code": sys.exit(3)
if mode == "lent": time.sleep(30)
rep = {"propositions": [{"remarque": 1, "texte": "Police 28 pour le nom de la voie.", "operations": [op]},
                        {"remarque": 77, "texte": "remarque qui n'existe pas", "operations": []}]}
texte = "pas du json" if mode == "illisible" else "Voici :\n```json\n" + json.dumps(rep) + "\n```"
print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": texte}))
''' % POLICE_28


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)


def leve(f, libelle, motif=""):
    try:
        f()
    except (ValueError, RuntimeError) as e:
        verifie(motif in str(e), True, libelle + (f"  [{e}]" if motif not in str(e) else ""))
        return
    verifie("pas d'exception", "exception", libelle)


def attend_fin(t, delai=60):
    limite = time.monotonic() + delai
    while t.etat()["etat"] == "en_cours" and time.monotonic() < limite:
        time.sleep(0.1)
    return t.etat()


def git(racine, *args):
    subprocess.run(["git", "-c", "user.name=banc", "-c", "user.email=banc@local", "-c", "core.autocrlf=false", *args],
                   cwd=racine, capture_output=True, check=True)


def test_actions(racine):
    verifie(aer.charge(racine, ENV), [], "charge : pas de fichier -> liste vide")
    r = aer.agit(racine, ENV, {"action": "epingle", "cible": {"page": 1, "objet": 11}, "texte": "Noms trop petits de loin"})
    verifie((r[0]["id"], r[0]["cible"], r[0]["etat"]), (1, {"page": 1, "objet": 11}, "ouverte"), "epingle : sur un objet")
    aer.agit(racine, ENV, {"action": "epingle", "cible": {"page": 1, "zone": [24, 500, 976, 30]}, "texte": "Ligne d'alerte ici"})
    aer.agit(racine, ENV, {"action": "epingle", "cible": {"page": 2}, "texte": "Page trop chargee"})
    verifie([x["id"] for x in aer.charge(racine, ENV)], [1, 2, 3], "epingle : ids successifs, fichier ecrit")
    leve(lambda: aer.agit(racine, ENV, {"action": "epingle", "cible": {"page": 1, "objet": 999}, "texte": "x"}), "epingle : objet inconnu refuse", "absent")
    leve(lambda: aer.agit(racine, ENV, {"action": "epingle", "cible": {"page": 9}, "texte": "x"}), "epingle : page inconnue refusee", "page 9")
    leve(lambda: aer.agit(racine, ENV, {"action": "epingle", "cible": {"page": 1, "zone": [0, 0, 0, 5]}, "texte": "x"}), "epingle : zone vide refusee", "zone")
    leve(lambda: aer.agit(racine, ENV, {"action": "epingle", "cible": {"page": 1}, "texte": "  "}), "epingle : texte vide refuse", "vide")
    leve(lambda: aer.agit(racine, ENV, {"action": "efface"}), "action inconnue refusee", "inconnue")
    nouvelle = {**aed.charge(racine, ENV)}
    nouvelle["objets"] = nouvelle["objets"] + [{"id": 66, "page": 1, "type": "btn", "x": 0, "y": 0, "l": 40, "h": 40, "attributs": {}}]
    r = aer.agit(racine, ENV, {"action": "epingle", "cible": {"page": 1, "objet": 66}, "texte": "Nouveau bouton", "description": nouvelle})
    verifie(r[-1]["cible"], {"page": 1, "objet": 66}, "epingle : objet pas encore ecrit, valide contre la description de la page")
    r = aer.agit(racine, ENV, {"action": "refuse", "id": 3})
    verifie(r[2]["etat"], "refusee", "refuse")
    r = aer.agit(racine, ENV, {"action": "repond", "id": 3, "texte": "Finalement si"})
    verifie((r[2]["etat"], r[2]["reponses"][0]["texte"]), ("ouverte", "Finalement si"), "repond : reponse gardee, remarque rouverte")
    aer.agit(racine, ENV, {"action": "refuse", "id": 3})
    aer.agit(racine, ENV, {"action": "refuse", "id": 4})


def test_propositions(racine):
    import atelier_ecrans_catalogue as cat
    desc, catalogue, rq = aed.charge(racine, ENV), cat.charge(racine), aer.charge(racine, ENV)
    bonne = {"remarque": 1, "texte": "t", "operations": [{"op": "modifie", "page": 1, "id": 11, "attributs": {"text_font": POLICE_28}}]}
    ok, err = aer.valide_propositions(json.dumps({"propositions": [bonne]}), desc, catalogue, rq)
    verifie((len(ok), err), (1, []), "proposition valide retenue")
    for libelle, op, motif in [
            ("id inconnu", {"op": "modifie", "page": 1, "id": 999, "attributs": {}}, "inconnu"),
            ("meme id sur une autre page (id 11 absent de la page 3)", {"op": "modifie", "page": 3, "id": 11, "attributs": {}}, "inconnu"),
            ("attribut hors catalogue", {"op": "modifie", "page": 1, "id": 11, "attributs": {"couleur_magique": 1}}, "hors catalogue"),
            ("police non compilee", {"op": "modifie", "page": 1, "id": 11, "attributs": {"text_font": 22}}, "22"),
            ("objet sorti de l'ecran", {"op": "modifie", "page": 1, "id": 11, "x": 2000}, "refusee"),
            ("op inconnue", {"op": "deplace", "page": 1, "id": 11}, "inconnue")]:
        ok, err = aer.valide_propositions({"propositions": [{**bonne, "operations": [op]}]}, desc, catalogue, rq)
        verifie((len(ok), len(err) == 1 and motif in err[0]), (0, True), "proposition rejetee : " + libelle + ("" if err and motif in err[0] else f" {err}"))
    ok, err = aer.valide_propositions({"propositions": [{**bonne, "remarque": 2 + 1}]}, desc, catalogue, rq)
    verifie(len(ok), 0, "proposition rejetee : remarque pas ouverte")
    verifie(aer.valide_propositions("rien de lisible", desc, catalogue, rq)[1][0].startswith("aucun JSON"), True, "sortie illisible rejetee")
    nouvelle = aer.applique(desc, bonne)
    verifie((aer._objet(nouvelle, 1, 11)["attributs"]["text_font"], aer._objet(desc, 1, 11)["attributs"]["text_font"]), (POLICE_28, 24),
            "applique : copie modifiee, description d'origine intacte")
    retire = aer.applique(desc, {"operations": [{"op": "retire", "page": 2, "id": 12}]})
    verifie((aer._objet(retire, 2, 12), aer._objet(retire, 1, 12) is not None), (None, True), "applique : retire l'objet (page 2, id 12) seulement")


def lance(racine, mode, argv, delai=60, programme=None):
    os.environ["FAUX_CLAUDE"] = mode
    t = aer.Traitement(racine, programme=programme or [sys.executable, str(racine.parent / "faux_claude.py")], delai=delai)
    t.lance(ENV)
    return t, attend_fin(t)


def test_traitement(racine, argv):
    avant = aer.chemin(racine, ENV).read_bytes()
    _, e = lance(racine, "ecrit", argv)
    verifie((e["etat"], "modifies pendant le traitement (platformio_override.ini)" in e["message"]), ("fini", True),
            f"traitement pendant qu'un fichier du depot change -> propositions gardees, avertissement ({e['message'][-90:]})")
    git(racine, "checkout", "--", "platformio_override.ini")
    aer.chemin(racine, ENV).write_bytes(avant)
    for mode, motif in [("code", "code 3"), ("illisible", "aucun JSON"), ("inconnu", "inconnu"), ("attribut", "hors catalogue")]:
        _, e = lance(racine, mode, argv)
        verifie((e["etat"], motif in e["message"]), ("echec", True), f"traitement {mode} -> echec ({e['message'][:90]})")
        verifie(aer.chemin(racine, ENV).read_bytes() == avant, True, f"traitement {mode} : remarques.json intact")
    _, e = lance(racine, "ok", argv, programme=[str(racine / "pas_de_claude.exe")])
    verifie((e["etat"], "impossible" in e["message"]), ("echec", True), "claude absent -> echec")
    os.environ["FAUX_CLAUDE"] = "lent"
    t = aer.Traitement(racine, programme=[sys.executable, str(racine.parent / "faux_claude.py")], delai=3)
    t.lance(ENV)
    leve(lambda: t.lance(ENV), "second lancement pendant un traitement refuse", "deja en cours")
    e = attend_fin(t, 30)
    verifie((e["etat"], "delai" in e["message"]), ("echec", True), "delai depasse -> echec")
    _, e = lance(racine, "ok", argv)
    rq = aer.charge(racine, ENV)
    verifie((e["etat"], rq[0]["etat"], rq[0]["proposition"]["operations"][0]["attributs"]), ("fini", "proposee", {"text_font": POLICE_28}),
            f"traitement ok : proposition ecrite par le module ({e['message'][:80]})")
    verifie("1 rejetee" in e["message"], True, "traitement ok : la proposition vers une remarque inconnue est rejetee")
    a = json.loads(Path(argv).read_text())
    verifie([x for x in ("--tools", "Read,Grep,Glob", "--permission-mode", "dontAsk", "--strict-mcp-config") if x in a["argv"]],
            ["--tools", "Read,Grep,Glob", "--permission-mode", "dontAsk", "--strict-mcp-config"], "options de lecture seule passees")
    reg = a["argv"][a["argv"].index("--settings") + 1] if "--settings" in a["argv"] else None
    verifie(reg and json.loads(Path(reg).read_text(encoding="utf-8")), {"disableAllHooks": True}, "hooks de l'utilisateur coupes (--settings)")
    verifie(("bypassPermissions" in a["argv"], "ouvertes : [1, 2]" in a["stdin"]), (False, True), "jamais bypassPermissions ; consigne par l'entree standard")
    verifie(any(p.name == "traitements.log" for p in (Path(os.environ["OUTILS_TASMOTA_DOSSIER"]) / "atelier_ecrans").iterdir()), True, "journal ecrit")


def test_routes(racine):
    class Banc(taw.Banc):
        def __init__(self, t):           # serveur sur la copie deja preparee
            import threading
            from http.server import ThreadingHTTPServer
            import socket
            self.racine, self.morte, self.appels = racine, False, []
            with socket.socket() as s:
                s.bind(("127.0.0.1", 0))
                self.port = s.getsockname()[1]
            self.trait = aer.Traitement(racine, programme=[sys.executable, str(racine.parent / "faux_claude.py")])
            g = aew.fabrique_gestionnaire(acces_web.Acces(self.port, True, "banc"), racine, get=self.get, traitement=self.trait,
                                          builds_en_cours=lambda: [])    # jamais les vrais processus : banc hermetique
            self.serveur = ThreadingHTTPServer(("127.0.0.1", self.port), g)
            threading.Thread(target=self.serveur.serve_forever, daemon=True).start()
    b = Banc(None)
    try:
        s, r = b.requete("GET", f"/remarques?env={ENV}")
        verifie((s, len(r["remarques"]), r["traitement"]["etat"]), (200, 4, "libre"), "GET /remarques")
        verifie(b.requete("GET", "/remarques?env=inconnu")[0], 400, "GET /remarques : env inconnu -> 400")
        s, r = b.requete("POST", "/remarques", {"env": ENV, "action": "epingle", "cible": {"page": 3}, "texte": "Boutons plus grands"})
        verifie((s, r["remarques"][-1]["id"]), (200, 5), "POST /remarques : epingle")
        verifie(b.requete("POST", "/remarques", {"env": ENV, "action": "epingle"}, entetes={})[0], 403, "POST sans en-tete anti-CSRF -> 403")
        s, r = b.requete("POST", "/remarques/appliquer", {"env": ENV, "id": 1, "description": aed.charge(racine, ENV)})
        verifie((s, aer._objet(r["description"], 1, 11)["attributs"]["text_font"], r["remarques"][0]["etat"]), (200, POLICE_28, "proposee"),
                "POST /remarques/appliquer : description modifiee rendue, remarque encore proposee (rien d'ecrit)")
        verifie((aer._objet(aed.charge(racine, ENV), 1, 11)["attributs"]["text_font"], aer.charge(racine, ENV)[0]["etat"]), (24, "proposee"),
                "appliquer : ni ecran.json ni remarques.json ecrits")
        appliquee = r["description"]
        s, d = b.requete("POST", "/diff", {"env": ENV, "description": appliquee})
        ecrire = {"env": ENV, "description": appliquee, "empreinte": d["empreinte"],
                  "empreinte_description": aed.empreinte(aed.chemin(racine, ENV).read_bytes())}
        verifie((b.requete("POST", "/ecrire", {**ecrire, "remarques": ["1"]})[0], aer._objet(aed.charge(racine, ENV), 1, 11)["attributs"]["text_font"]),
                (400, 24), "POST /ecrire : remarques mal formees -> 400, rien d'ecrit")
        s, r = b.requete("POST", "/ecrire", {**ecrire, "remarques": [1]})
        verifie((s, r["remarques"][0]["etat"], aer.charge(racine, ENV)[0]["etat"], aer._objet(aed.charge(racine, ENV), 1, 11)["attributs"]["text_font"]),
                (200, "appliquee", "appliquee", POLICE_28), "POST /ecrire avec la remarque 1 : ecrit, remarque appliquee")
        verifie(b.requete("POST", "/remarques/appliquer", {"env": ENV, "id": 1, "description": {}})[0], 400, "appliquer deux fois -> 400")
        os.environ["FAUX_CLAUDE"] = "ok"
        s, r = b.requete("POST", "/remarques/traiter", {"env": ENV})
        verifie((s, r["etat"]), (200, "en_cours"), "POST /remarques/traiter : lance")
        attend_fin(b.trait)
        e = b.requete("GET", "/remarques/etat")[1]
        verifie((e["etat"], "pas ouverte" in e["message"]), ("echec", True), "GET /remarques/etat : remarque 1 deja appliquee, proposition rejetee")
        reel = aew.depuis_ce_pc
        aew.depuis_ce_pc = lambda h: False          # appareil du reseau muni du jeton : acces.controle le laisse passer
        try:
            s, r = b.requete("POST", "/remarques/traiter", {"env": ENV})
        finally:
            aew.depuis_ce_pc = reel
        verifie((s, "ce PC" in str(r)), (403, True), "lancement refuse depuis un autre appareil")
    finally:
        b.ferme()


def etat_depart(racine):
    """Copie hermetique : sans les remarques du vrai depot, nom de la voie 1 (page 1, objet 11) en police 24 quelle que
    soit la description du depot (la remarque 1 du faux claude le passe en 28)."""
    for f in racine.glob("outils_docs/atelier_ecrans/cartes/*/remarques.json"):
        f.unlink()
    d = aed.charge(racine, ENV)
    aer._objet(d, 1, 11)["attributs"]["text_font"] = 24
    noms = aee.chemins(ENV)                  # ecran.json et les deux interfaces generees, coherents entre eux
    for nom, octets in aee.generes(d, cat.charge(racine)).items():
        (racine / noms[nom]).write_bytes(octets)


def main():
    with tempfile.TemporaryDirectory(prefix="banc_atelier_remarques_") as t:
        racine = Path(t) / "depot"
        racine.mkdir()
        taw.copie(racine)
        etat_depart(racine)
        git(racine, "init", "-q")
        git(racine, "add", "-A")
        git(racine, "commit", "-q", "-m", "copie")
        (Path(t) / "faux_claude.py").write_text(FAUX, encoding="utf-8")
        argv = str(Path(t) / "argv.json")
        os.environ["FAUX_CLAUDE_ARGV"] = argv
        os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(t) / "donnees")
        test_actions(racine)
        test_propositions(racine)
        test_traitement(racine, argv)
        git(racine, "add", "-A")
        git(racine, "commit", "-q", "-m", "remarques")
        test_routes(racine)
    print(f"\n{len(ECHECS)} echec(s) : " + ("VERT" if not ECHECS else "ROUGE"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
