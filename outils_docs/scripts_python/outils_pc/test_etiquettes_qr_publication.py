"""Banc de etiquettes_qr_publication (plan etiquettes-qrcode A10) : fiches publiques, branche `etiquettes`. Code 0 = vert.

Lancer avec le Python de PlatformIO depuis la racine du depot :
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_etiquettes_qr_publication.py
Tout se passe dans un depot temporaire (copie du banc d'ecriture) dont l'origin est un depot NU local : son URL lue est
https://github.com/Proprio/Depot.git, reecrite vers le depot nu par `url.<nu>.insteadOf`. Rien ne part sur le reseau.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import test_etiquettes_qr_ecriture as banc_ecr       # copie du depot et verifie() ; pose OUTILS_TASMOTA_DOSSIER
import build_envs                                     # noqa: E402
import etiquettes_qr_filtre_public as filtre          # noqa: E402
import etiquettes_qr_modele as modele                 # noqa: E402
import etiquettes_qr_publication as pub               # noqa: E402

CUVE = banc_ecr.CUVE
GITHUB = "https://github.com/Proprio/Depot.git"
URL = f"https://proprio.github.io/Depot/{CUVE}.html"
verifie, refuse, ECHECS = banc_ecr.verifie, banc_ecr.refuse, banc_ecr.ECHECS
SANS_BUILD = lambda: []
GITHUB_RACINE = None                                  # depot de test dont l'origin se lit https://github.com/Proprio/Depot.git


def git(depot, *args):
    return subprocess.run(["git", "-C", str(depot), *args], capture_output=True, check=True).stdout.decode("utf-8").strip()


def en_depot(racine, dossier):
    """Fait de la copie `racine` un depot git dont l'origin (lu https://github.com/Proprio/Depot.git) est un depot nu
    local cree dans `dossier` ; rend le chemin du depot nu. Aussi utilise par test_etiquettes_qr_web."""
    nu = Path(dossier) / "origin.git"
    git(dossier, "init", "--quiet", "--bare", str(nu))
    git(racine, "init", "--quiet", "-b", "development")
    git(racine, "config", "user.name", "banc")
    git(racine, "config", "user.email", "banc@exemple.invalid")
    git(racine, "config", "core.autocrlf", "false")
    git(racine, "remote", "add", "origin", GITHUB)
    git(racine, "config", f"url.{nu.as_posix()}.insteadOf", GITHUB)
    git(racine, "add", "-A")
    git(racine, "commit", "--quiet", "-m", "depart")
    git(racine, "push", "--quiet", "origin", "development")
    modele._url_depot.cache_clear()                    # adresse deja lue (None) avant que la copie soit un depot
    return nu


def prepare(dossier):
    racine = banc_ecr.copie(Path(dossier) / "travail")
    return racine, en_depot(racine, dossier)


def regle(racine, surcharge):
    chemin = modele.chemin_surcharge(racine, CUVE)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(surcharge), encoding="utf-8")


def temoin(racine, nu):
    """Ce qui ne doit JAMAIS bouger : arbre de travail, index, development local et distant."""
    fichiers = {k: v for k, v in banc_ecr.instantane(racine).items() if not k.startswith(".git/")}
    return (fichiers, git(racine, "status", "--porcelain"), git(racine, "rev-parse", "development"),
            git(nu, "rev-parse", "refs/heads/development"))


def arbre(nu, ref="refs/heads/etiquettes"):
    return sorted(git(nu, "ls-tree", "--name-only", ref).splitlines())


def test_adresse(racine):
    verifie(modele.url_fiche(racine, CUVE), URL, "url_fiche : <proprietaire en minuscules>.github.io/<depot>/<env>.html")
    with tempfile.TemporaryDirectory() as d:
        git(d, "init", "--quiet")
        git(d, "remote", "add", "origin", "https://x-access-token:JETON123@github.com/Proprio/Depot.git")
        verifie(modele.url_depot(d), "https://proprio.github.io/Depot/", "URL d'origin a jeton : jeton absent de l'adresse")
        git(d, "remote", "set-url", "origin", "git@github.com:Proprio/Depot.git")
        modele._url_depot.cache_clear()
        verifie(modele.url_depot(d), "https://proprio.github.io/Depot/", "URL d'origin en ssh")
        git(d, "remote", "set-url", "origin", "https://gitlab.com/Proprio/Depot.git")
        modele._url_depot.cache_clear()
        refuse(lambda: modele.url_fiche(d, CUVE), ValueError, "origin hors GitHub : pas d'adresse", "GitHub")


def test_publication(racine, nu):
    p = pub.prevoit_publication(racine, [CUVE])
    verifie(([f["chemin"] for f in p["fichiers"]], p["publies"]), ([".nojekyll"], []), "aucune carte en mode lien : .nojekyll seul")

    regle(racine, {"contenu": "lien", "lignes": [{"source": "standard", "cle": "hostname", "libelle": "Hostname"},
                                                 {"source": "libre", "texte": "<script>alert(1)</script>"}]})
    r = modele.resout(racine, CUVE, modele.charge_reglage(racine, CUVE))
    verifie(r["texte"], URL, "mode lien : le QR code porte l'adresse de la fiche")
    p = pub.prevoit_publication(racine, [CUVE])
    verifie((sorted(f["chemin"] for f in p["fichiers"]), p["refus"]), ([".nojekyll", f"{CUVE}.html"], []), "carte en lien : sa fiche prevue")
    f = p["contenu"][f"{CUVE}.html"]
    verifie(("&lt;script&gt;" in f, "<script" in f), (True, False), "valeur libre <script> rendue en texte")
    verifie(('name="robots" content="noindex' in f, "src=" in f or "href=" in f or "@import" in f), (True, False),
            "fiche noindex, sans ressource externe")
    verifie("Publiée le " in f and "prefers-color-scheme:dark" in f, True, "fiche datee, clair et sombre")

    refuse(lambda: pub.publie(racine, [CUVE], p["empreinte"], lambda: ["pio"]), RuntimeError, "build en cours : refus", "build")
    refuse(lambda: pub.publie(racine, [CUVE], "perimee", SANS_BUILD), RuntimeError, "empreinte perimee : refus", "changé")
    refuse(lambda: pub.publie(racine, [CUVE], p["empreinte"], lambda: None), RuntimeError,
           "detection des builds impossible : refus (comme la serie, qui attend)", "détection")
    avant = temoin(racine, nu)
    sha = pub.publie(racine, [CUVE], p["empreinte"], SANS_BUILD)
    verifie(git(nu, "rev-parse", "refs/heads/etiquettes"), sha, "branche etiquettes poussee sur origin")
    verifie(arbre(nu), [".nojekyll", f"{CUVE}.html"], "arbre publie : .nojekyll et la fiche")
    verifie(git(nu, "show", f"{sha}:{CUVE}.html") + "\n", f, "fiche publiee = fiche prevue, octet pour octet")
    verifie(temoin(racine, nu), avant, "arbre de travail, index et development intacts")
    verifie(git(nu, "rev-list", "--count", sha), "1", "branche orpheline (aucun parent de development)")

    p = pub.prevoit_publication(racine, [CUVE])
    verifie(p["fichiers"], [], "rien de change : rien a publier")
    verifie(pub.publie(racine, [CUVE], p["empreinte"], SANS_BUILD), None, "publication sans changement : aucun commit")
    vrai = pub.fiche_html
    pub.fiche_html = lambda *a, **k: vrai(*a, **{**k, "date": "2099-01-01"})
    try:
        verifie(pub.prevoit_publication(racine, [CUVE])["fichiers"], [], "meme fiche un autre jour : gardee telle quelle")
    finally:
        pub.fiche_html = vrai

    regle(racine, {"contenu": "lien", "lignes": [{"source": "libre", "texte": "http://x/?token=abc"}]})
    p = pub.prevoit_publication(racine, [CUVE])
    verifie(len(p["refus"]) == 1 and "abc" not in p["refus"][0]["raison"], True, "ligne secrete : refus nomme, valeur non recopiee")
    refuse(lambda: pub.publie(racine, [CUVE], p["empreinte"], SANS_BUILD), RuntimeError, "ligne refusee : publication refusee", "refusée")
    verifie(git(nu, "rev-parse", "refs/heads/etiquettes"), sha, "refus : branche inchangee")

    # Filtre de l'A2 sur TOUTE la ligne publiee (relecture du 2026-11-13) : secret du persist dans une ligne libre ou un
    # texte « avant », que controle_public ne reconnait pas (ni chiffre, ni mot annonciateur)
    chemin = build_envs.persist_carte(racine, CUVE)
    persist = json.loads(chemin.read_text(encoding="utf-8"))
    persist.setdefault("serveur", {})["essai"] = {"password": "soleilLevant"}       # cle secrete au sens de modele.SECRET
    verifie("soleilLevant" in modele._valeurs_secretes(persist, set()), True, "temoin : valeur secrete pour le filtre de l'A2")
    chemin.write_text(json.dumps(persist), encoding="utf-8")
    verifie(filtre.controle_public("AP soleilLevant"), None, "temoin : le filtre de valeur seul laisserait passer ce secret")
    for ligne, nom in (({"source": "libre", "texte": "AP soleilLevant"}, "ligne libre"),
                       ({"source": "standard", "cle": "hostname", "libelle": "Hôte", "avant": "soleilLevant "}, "texte avant")):
        regle(racine, {"contenu": "lien", "lignes": [ligne]})
        p = pub.prevoit_publication(racine, [CUVE])
        verifie((len(p["refus"]), any("soleilLevant" in r["raison"] for r in p["refus"])), (1, False),
                f"secret du persist dans une {nom} : refuse, sans recopie")
        vrai_sensible = modele._sensible
        modele._sensible = lambda *a: False
        try:
            verifie(pub.prevoit_publication(racine, [CUVE])["refus"], [], f"mutant sans le filtre de l'A2 ({nom}) : rouge")
        finally:
            modele._sensible = vrai_sensible
    regle(racine, {"contenu": "lien", "lignes": [{"source": "libre", "texte": "Garage"}]})
    f = pub.prevoit_publication(racine, [CUVE])["contenu"][f"{CUVE}.html"]
    verifie((f"<title>{CUVE}</title>" in f, "CAPTEURS-CUVE" in f), (True, False), "titre de la fiche = env (deja public dans l'adresse)")

    modele.chemin_surcharge(racine, CUVE).unlink()                # retour au texte (gabarit commun)
    p = pub.prevoit_publication(racine, [CUVE])
    verifie([(x["chemin"], x["apres"]) for x in p["fichiers"]], [(f"{CUVE}.html", None)], "carte repassee en texte : fiche retiree")
    sha2 = pub.publie(racine, [CUVE], p["empreinte"], SANS_BUILD)
    verifie((arbre(nu), git(nu, "rev-parse", f"{sha2}^")), ([".nojekyll"], sha), "fiche retiree au prochain envoi, par dessus la pointe")

    # Branche poussee d'ailleurs entre l'apercu et l'envoi : refus, rien d'ecrase
    regle(racine, {"contenu": "lien", "lignes": [{"source": "libre", "texte": "Garage"}]})
    p = pub.prevoit_publication(racine, [CUVE])
    ailleurs = git(nu, "commit-tree", f"{sha2}^{{tree}}", "-p", sha2, "-m", "ailleurs")
    git(nu, "update-ref", "refs/heads/etiquettes", ailleurs)
    refuse(lambda: pub.publie(racine, [CUVE], p["empreinte"], SANS_BUILD), RuntimeError, "branche bougee ailleurs : refus", "changé")
    verifie(git(nu, "rev-parse", "refs/heads/etiquettes"), ailleurs, "branche bougee ailleurs : rien d'ecrase")
    # Hors ligne (origin introuvable) : erreur lisible, pas de blocage
    git(racine, "config", "--remove-section", f"url.{nu.as_posix()}")
    git(racine, "config", f"url.{(nu.parent / 'absent.git').as_posix()}.insteadOf", GITHUB)
    refuse(lambda: pub.prevoit_publication(racine, [CUVE]), RuntimeError, "origin injoignable : erreur de lecture", "impossible")


FAUX_GH = r'''import json, os, sys
open(os.environ["FAUX_GH_TRACE"], "a", encoding="utf-8").write(json.dumps(sys.argv[1:]) + "\n")
sys.stdout.write(os.environ.get("FAUX_GH_SORTIE", ""))
sys.stderr.write(os.environ.get("FAUX_GH_ERREUR", ""))
sys.exit(int(os.environ.get("FAUX_GH_CODE", "0")))
'''


def test_suivi_et_tout(racine, nu):
    """A11 : fiche a republier (sans reseau), publication de toutes les fiches (page Build)."""
    verifie(pub.fiche_a_republier(racine, CUVE), False, "carte en texte, rien en ligne : rien a republier")
    regle(racine, {"contenu": "lien", "lignes": [{"source": "libre", "texte": "Garage"}]})
    verifie(pub.fiche_a_republier(racine, CUVE), True, "carte en lien sans fiche en ligne : a republier")
    sha = pub.publie_tout(racine, SANS_BUILD)
    verifie((bool(sha), pub.fiche_a_republier(racine, CUVE)), (True, False), "publie_tout : fiche en ligne, plus rien a republier")
    verifie(pub.publie_tout(racine, SANS_BUILD), None, "publie_tout sans changement : aucun commit")
    vrai = pub.fiche_html
    pub.fiche_html = lambda *a, **k: vrai(*a, **{**k, "date": "2099-01-01"})
    try:
        verifie(pub.fiche_a_republier(racine, CUVE), False, "autre jour, meme contenu : rien a republier")
    finally:
        pub.fiche_html = vrai
    regle(racine, {"contenu": "lien", "lignes": [{"source": "libre", "texte": "Garage nord"}]})
    verifie(pub.fiche_a_republier(racine, CUVE), True, "contenu change : a republier")
    regle(racine, {"contenu": "lien", "lignes": [{"source": "libre", "texte": "http://x/?token=abc"}]})
    refuse(lambda: pub.publie_tout(racine, SANS_BUILD), RuntimeError, "publie_tout : ligne refusee, rien d'envoye", "refusée")
    verifie(git(nu, "rev-parse", "refs/heads/etiquettes"), sha, "publie_tout refuse : branche inchangee")
    regle(racine, {"contenu": "texte"})
    verifie(pub.fiche_a_republier(racine, CUVE), True, "carte repassee en texte, fiche encore en ligne : a republier (retrait)")


def test_pages(dossier):
    """A11 : etat et activation de GitHub Pages par gh (faux gh : arguments notes, reponse imposee)."""
    script = Path(dossier) / "faux_gh.py"
    script.write_text(FAUX_GH, encoding="utf-8")
    trace = Path(dossier) / "trace_gh.txt"
    vrai_gh, env = pub.GH, dict(os.environ)
    pub.GH = [sys.executable, str(script)]
    os.environ["FAUX_GH_TRACE"] = str(trace)
    try:
        os.environ.update(FAUX_GH_SORTIE=json.dumps({"html_url": "https://proprio.github.io/Depot/", "source": {"branch": "etiquettes"}}),
                          FAUX_GH_CODE="0")
        verifie(pub.etat_pages(GITHUB_RACINE), {"actif": True, "url": "https://proprio.github.io/Depot/", "branche": "etiquettes"},
                "etat_pages : Pages actif, adresse et branche")
        os.environ.update(FAUX_GH_SORTIE='{"message":"Not Found"}', FAUX_GH_ERREUR="gh: Not Found (HTTP 404)", FAUX_GH_CODE="1")
        verifie(pub.etat_pages(GITHUB_RACINE)["actif"], False, "etat_pages : 404 = Pages inactif")
        os.environ.update(FAUX_GH_SORTIE="", FAUX_GH_ERREUR="gh: Bad credentials (HTTP 401)", FAUX_GH_CODE="1")
        refuse(lambda: pub.etat_pages(GITHUB_RACINE), RuntimeError, "etat_pages : autre erreur de gh rendue", "401")
        os.environ.update(FAUX_GH_SORTIE="{}", FAUX_GH_ERREUR="", FAUX_GH_CODE="0")
        pub.active_pages(GITHUB_RACINE)
        dernier = json.loads(trace.read_text(encoding="utf-8").splitlines()[-1])
        verifie(dernier, ["api", "-X", "POST", "repos/proprio/Depot/pages", "-f", "source[branch]=etiquettes", "-f", "source[path]=/"],
                "active_pages : POST repos/<proprietaire>/<depot>/pages, branche etiquettes, racine")
    finally:
        pub.GH = vrai_gh
        os.environ.clear()
        os.environ.update(env)


def principal():
    global GITHUB_RACINE
    with tempfile.TemporaryDirectory(prefix="etiquettes_qr_pub_") as d:
        racine, nu = prepare(d)
        GITHUB_RACINE = racine
        print("--- test_adresse")
        test_adresse(racine)
        print("--- test_publication")
        test_publication(racine, nu)
    with tempfile.TemporaryDirectory(prefix="etiquettes_qr_pub_") as d:
        racine, nu = prepare(d)
        GITHUB_RACINE = racine
        print("--- test_suivi_et_tout")
        test_suivi_et_tout(racine, nu)
        print("--- test_pages")
        test_pages(d)
    print("BANC_ETIQUETTES_QR_PUBLICATION:", f"ECHEC {len(ECHECS)} : " + " ; ".join(ECHECS) if ECHECS else "OK")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
