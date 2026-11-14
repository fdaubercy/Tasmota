"""Banc de etiquettes_qr_web (routes HTTP de la page « Etiquettes QR code », plan A4). Code de sortie 0 = vert.

Lancer avec le Python de PlatformIO depuis la racine du depot :
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_etiquettes_qr_web.py
Serveur dans un fil, sur un port libre, devant la COPIE temporaire du banc A3 (test_etiquettes_qr_ecriture.copie : .ini, .h,
cuve, porte, TV, gabarit) et la bibliotheque qr-code-styling. Le vrai depot n'est jamais ecrit ; detection des builds simulee.
"""

import http.client
import json
import re
import shutil
import socket
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer

import test_etiquettes_qr_ecriture as tqe          # pose OUTILS_TASMOTA_DOSSIER avant l'import des modules d'ecriture
import acces_web                                    # noqa: E402
import etiquettes_qr_web as eqw                     # noqa: E402

CUVE, PORTE, TV = tqe.CUVE, tqe.PORTE, tqe.TV
SECRET_INDEPENDANT = re.compile(r"pass|pwd|mdp|key|token|secret|psk", re.I)   # pas modele.SECRET : un temoin a part
verifie = tqe.verifie


class Banc:
    def __init__(self, dossier):
        self.racine = tqe.copie(dossier)
        lib = eqw.modele.DOSSIER / "lib" / "qr-code-styling.min.js"
        (self.racine / lib).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tqe.DEPOT / lib, self.racine / lib)
        self.builds = []
        # jamais le vrai gh (reseau) : un faux qui repond « Pages inactif » (404)
        eqw.publication.GH = [sys.executable, "-c", "import sys; sys.stderr.write('gh: Not Found (HTTP 404)'); sys.exit(1)"]
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        acces = acces_web.Acces(self.port, True, "Etiquettes QR code")
        self.serveur = ThreadingHTTPServer(("127.0.0.1", self.port),
                                           eqw.fabrique_gestionnaire(acces, self.racine, lambda: self.builds))
        self.serveur.daemon_threads = True
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()

    def requete(self, methode, chemin, corps=None, entetes=None, brut=None):
        h = dict(entetes if entetes is not None else ({"X-Etiquettes-QR": "1"} if methode == "POST" else {}))
        donnees = brut if brut is not None else json.dumps(corps).encode("utf-8") if corps is not None else None
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        try:
            c.request(methode, chemin, body=donnees, headers=h)
            r = c.getresponse()
            octets = r.read()
            self.type = r.getheader("Content-Type", "")
            try:
                return r.status, json.loads(octets.decode("utf-8"))
            except ValueError:
                return r.status, octets.decode("utf-8", "replace")
        finally:
            c.close()

    def ferme(self):
        self.serveur.shutdown()
        self.serveur.server_close()


def gabarit(b):
    return b.requete("GET", "/gabarit")[1]["gabarit"]


def test_page(b):
    statut, page = b.requete("GET", "/")
    verifie((statut, "<title>Étiquettes QR code</title>" in page, '<script src="/lib.js">' in page), (200, True, True), "GET / : la page et la bibliotheque")
    verifie(("mode: 'Byte'" in page, "new TextEncoder().encode" in page), (True, True), "page : texte en octets UTF-8, mode Byte")
    verifie(("function remplitParLieu" in page, 'id="theme"' in page, "innerHTML" in page), (True, True, False),
            "page : liste par lieu, interrupteur de theme, aucun innerHTML")
    statut, lib = b.requete("GET", "/lib.js")
    verifie((statut, "QRCodeStyling" in lib, b.type.startswith("application/javascript")), (200, True, True), "GET /lib.js : qr-code-styling du depot")
    verifie(b.requete("GET", "/inconnue")[0], 404, "GET /inconnue : 404")


def test_cartes(b):
    statut, d = b.requete("GET", "/cartes")
    cartes = {c["nom"]: c for c in d["cartes"]}
    verifie((statut, CUVE in cartes, PORTE in cartes, TV in cartes), (200, True, True, True), "GET /cartes : cuve, porte, TV")
    verifie((cartes[CUVE]["esp32"], cartes[TV]["esp32"], cartes[CUVE]["lieu"], cartes[TV]["lieu"]), (True, False, "garage", "rdc"),
            "GET /cartes : puce et lieu")
    verifie((any("-base" in n for n in cartes), len(d["lieux"]) > 0), (False, True), "GET /cartes : ni base, et la table des lieux")
    verifie((cartes[CUVE]["regle"], cartes[CUVE]["page"]), (False, False), "GET /cartes : cuve sans reglage propre ni page")


def test_reglage_persist(b):
    statut, r = b.requete("GET", "/reglage?env=" + CUVE)
    verifie((statut, r["reglage"] == gabarit(b), r["regle"], r["esp32"]), (200, True, False, True), "GET /reglage : cuve = gabarit commun")
    tv = b.requete("GET", "/reglage?env=" + TV)[1]
    verifie((tv["esp32"], "range_extender" in tv["champs"]), (False, False), "GET /reglage : TV, ESP8266, sans range extender")
    verifie("range_extender" in r["champs"], True, "GET /reglage : cuve, range extender actif propose")
    for env in ("inconnu", "../platformio", ""):
        verifie(b.requete("GET", "/reglage?env=" + env)[0], 404, f"GET /reglage?env={env!r} : 404")
    statut, p = b.requete("GET", "/persist?env=" + CUVE)
    chemins = [x["chemin"] for x in p["arbre"]]
    verifie((statut, len(chemins) > 20), (200, True), f"GET /persist : cuve, {len(chemins)} cles proposees")
    verifie([c for c in chemins if SECRET_INDEPENDANT.search(c)], [], "GET /persist : aucune cle sensible (motif independant)")
    brut = json.loads((b.racine / tqe.fbe.dossier_carte(CUVE) / "_persist.json").read_text(encoding="utf-8"))
    secrets = set()

    def fouille(n, sensible=False):
        if isinstance(n, dict):
            for k, v in n.items():
                fouille(v, sensible or bool(SECRET_INDEPENDANT.search(k)))
        elif isinstance(n, list):
            for v in n:
                fouille(v, sensible)
        elif sensible and isinstance(n, str) and len(n) >= 4:
            secrets.add(n)
    fouille(brut)
    vu = json.dumps(p, ensure_ascii=False)
    verifie((len(secrets) > 0, [s for s in secrets if s in vu]), (True, []), f"GET /persist : aucune des {len(secrets)} valeurs secretes de la cuve")
    verifie(b.requete("GET", "/persist?env=" + TV)[1]["arbre"], [], "GET /persist : TV sans persist, liste vide")


def test_csrf(b):
    corps = {"env": CUVE, "reglage": gabarit(b)}
    verifie(b.requete("POST", "/apercu", corps, entetes={})[0], 403, "POST sans en-tete X-Etiquettes-QR : 403")
    verifie(b.requete("POST", "/apercu", corps, entetes={"X-Etiquettes-QR": "1", "Origin": "http://evil.example"})[0], 403,
            "POST d'une autre origine : 403")
    verifie(b.requete("POST", "/apercu", entetes={"X-Etiquettes-QR": "1", "Content-Length": "999999999"}, brut=b"")[0], 400,
            "POST trop gros : 400")
    verifie(b.requete("POST", "/apercu", entetes={"X-Etiquettes-QR": "1", "Content-Length": "-1"}, brut=b"")[0], 400,
            "POST Content-Length negatif : 400")
    verifie(b.requete("POST", "/apercu", brut=b"[1]")[0], 400, "POST corps non objet : 400")
    verifie(b.requete("POST", "/impression", {"impressions": [None], "taille_mm": 25})[0], 400, "POST /impression : element nul, 400")


def test_apercu(b):
    g = gabarit(b)
    statut, a = b.requete("POST", "/apercu", {"env": CUVE, "reglage": g})
    verifie((statut, a["erreurs"], a["correction"], a["verdict"]["niveau"]), (200, [], "M", "lisible"), "POST /apercu : cuve lisible, correction M")
    verifie(a["texte"].startswith("Hostname : ") and " · IP : " in a["texte"], True, f"POST /apercu : texte lu {a['texte']!r}")
    g2 = json.loads(json.dumps(g))
    g2["lignes"].append({"source": "libre", "texte": "Été / garage €"})
    a2 = b.requete("POST", "/apercu", {"env": CUVE, "reglage": g2})[1]
    verifie(a2["verdict"]["octets"], len(a2["texte"].encode("utf-8")), "POST /apercu : octets comptes en UTF-8")
    g3 = dict(g, taille_mm=5)
    verifie(bool(b.requete("POST", "/apercu", {"env": CUVE, "reglage": g3})[1]["erreurs"]), True, "POST /apercu : taille invalide -> erreurs")
    g4 = dict(g, lignes=[{"source": "libre", "texte": "x" * 120}] * 4, taille_mm=10)
    verifie(b.requete("POST", "/apercu", {"env": CUVE, "reglage": g4})[1]["verdict"]["niveau"], "trop_dense", "POST /apercu : ~490 octets sur 10 mm, trop dense")
    g5 = dict(g, lignes=[{"source": "libre", "texte": "x" * 120}] * 20)
    verifie(b.requete("POST", "/apercu", {"env": CUVE, "reglage": g5})[1]["verdict"]["niveau"], "trop_long", "POST /apercu : ~2450 octets, au-dela de la version 40 M")
    verifie(b.requete("POST", "/apercu", {"env": "inconnu", "reglage": g})[0], 404, "POST /apercu : carte inconnue, 404")


def test_ecriture(b):
    g = dict(gabarit(b), taille_mm=30)
    corps = {"env": CUVE, "reglage": g, "page_carte": False}
    statut, p = b.requete("POST", "/diff", corps)
    chemin = (eqw.modele.DOSSIER / "cartes" / (CUVE + ".json")).as_posix()
    verifie((statut, [f["chemin"] for f in p["fichiers"]], p["fichiers"][0]["ajouts"] > 0), (200, [chemin], True), "POST /diff : la surcharge de la cuve")
    verifie(b.requete("POST", "/diff", dict(corps, page_carte="oui"))[0], 400, "POST /diff : page_carte non booleen, 400")
    b.builds = ["pio run -e x"]
    verifie(b.requete("POST", "/ecrire", dict(corps, empreinte=p["empreinte"]))[0], 409, "POST /ecrire : build en cours, 409")
    b.builds = []
    verifie(b.requete("POST", "/ecrire", dict(corps, empreinte="perimee"))[0], 409, "POST /ecrire : empreinte perimee, 409")
    statut, e = b.requete("POST", "/ecrire", dict(corps, empreinte=p["empreinte"]))
    verifie((statut, e["ecrits"], (b.racine / chemin).is_file()), (200, [chemin], True), "POST /ecrire : surcharge ecrite")
    r = b.requete("GET", "/reglage?env=" + CUVE)[1]
    verifie((r["regle"], r["reglage"]["taille_mm"]), (True, 30), "GET /reglage apres ecriture : reglage propre relu")
    verifie(b.requete("POST", "/diff", corps)[1]["fichiers"], [], "POST /diff apres ecriture : rien a ecrire")
    verifie(b.requete("POST", "/diff", {"env": TV, "reglage": g, "page_carte": True})[0], 400, "POST /diff : page sur un ESP8266, 400")


def test_gabarit_impression(b):
    g = dict(gabarit(b), separateur=" = ")
    statut, p = b.requete("POST", "/gabarit/diff", {"gabarit": g})
    verifie((statut, [f["chemin"] for f in p["fichiers"]]), (200, [eqw.modele.GABARIT.as_posix()]), "POST /gabarit/diff")
    statut, _ = b.requete("POST", "/gabarit/ecrire", {"gabarit": g, "empreinte": p["empreinte"]})
    verifie((statut, gabarit(b)["separateur"]), (200, " = "), "POST /gabarit/ecrire : gabarit commun ecrit")
    corps = {"impressions": [{"env": CUVE, "reglage": gabarit(b)}, {"env": TV, "reglage": gabarit(b)}], "taille_mm": 25}
    statut, n = b.requete("POST", "/impression", corps)
    imp = tqe.eqe.lit_impressions(b.racine)
    verifie((statut, n["notees"], sorted(imp)), (200, sorted([CUVE, TV]), sorted([CUVE, TV])), "POST /impression : deux cartes notees")
    verifie("texte" in json.dumps(imp), False, "impressions.json : empreinte seulement, jamais le texte")
    verifie(b.requete("POST", "/impression", dict(corps, impressions=[]))[0], 400, "POST /impression : liste vide, 400")
    verifie(b.requete("POST", "/impression/annule", {"env": TV})[0], 200, "POST /impression/annule")
    verifie(sorted(tqe.eqe.lit_impressions(b.racine)), [CUVE], "impressions.json : TV retiree")
    premiere = tqe.eqe.lit_impressions(b.racine)[CUVE]
    b.requete("POST", "/impression", {"impressions": [{"env": CUVE, "reglage": dict(gabarit(b), separateur=" > ")}], "taille_mm": 30})
    verifie(tqe.eqe.lit_impressions(b.racine)[CUVE]["taille_mm"], 30, "reimpression de la cuve notee")
    b.requete("POST", "/impression/annule", {"env": CUVE})
    verifie(tqe.eqe.lit_impressions(b.racine)[CUVE], premiere, "annulation de la reimpression : note precedente remise")


def test_suivi(b):
    """A7 : badges de la liste (GET /suivi, local) et etat d'une carte (GET /etat, interroge la carte)."""
    statut, s = b.requete("GET", "/suivi")
    verifie((statut, s["suivi"].get(CUVE)), (200, {"a_reimprimer": False, "a_regenerer": False, "a_republier_fiche": False}),
            "GET /suivi : cuve imprimee avec le reglage actuel, rien a refaire")
    verifie(TV in s["suivi"], True, "GET /suivi : carte sans Berry suivie aussi (etiquette papier)")
    g = dict(gabarit(b), separateur=" - ")
    p = b.requete("POST", "/gabarit/diff", {"gabarit": g})[1]
    b.requete("POST", "/gabarit/ecrire", {"gabarit": g, "empreinte": p["empreinte"]})
    verifie(b.requete("GET", "/suivi")[1]["suivi"][CUVE]["a_reimprimer"], True, "separateur du gabarit change : cuve a reimprimer")
    statut, e = b.requete("GET", "/etat?env=" + CUVE)
    verifie((statut, e), (200, {"a_reimprimer": True, "a_regenerer": False, "carte": "sans_page"}),
            "GET /etat : sans page sur la carte, carte non interrogee")
    verifie(b.requete("GET", "/etat?env=Mauvais%20nom")[0], 404, "GET /etat : carte inconnue, 404 (comme /reglage)")


def test_publication(b, dossier):
    import test_etiquettes_qr_publication as tpub
    nu = tpub.en_depot(b.racine, tempfile.mkdtemp(dir=dossier, prefix="nu_"))   # hors de la copie (dossier = racine)
    g = dict(gabarit(b), contenu="lien", lignes=gabarit(b)["lignes"] + [{"source": "libre", "texte": "http://x/?token=abc"}])
    a = b.requete("POST", "/apercu", {"env": CUVE, "reglage": g})[1]
    verifie((a["texte"], any("fiche publique" in m and "abc" not in m for m in a["avertissements"])), (tpub.URL, True),
            "POST /apercu en mode lien : adresse de la fiche, ligne secrete signalee sans sa valeur")
    statut, p = b.requete("POST", "/publication/diff", {})
    verifie((statut, [f["chemin"] for f in p["fichiers"]], p["publies"], "contenu" in p), (200, [".nojekyll"], [], False),
            "POST /publication/diff : aucune carte en lien, .nojekyll seul, contenu non renvoye")
    g["lignes"].pop()
    e = b.requete("POST", "/diff", {"env": CUVE, "reglage": g, "page_carte": False})[1]
    b.requete("POST", "/ecrire", {"env": CUVE, "reglage": g, "page_carte": False, "empreinte": e["empreinte"]})
    statut, p = b.requete("POST", "/publication/diff", {})
    verifie((statut, p["publies"], p["refus"], p["url"]), (200, [CUVE], [], "https://proprio.github.io/Depot/"),
            "POST /publication/diff : cuve ecrite en lien, sa fiche prevue")
    verifie(b.requete("GET", "/suivi")[1]["suivi"][CUVE].get("a_republier_fiche"), True, "GET /suivi : fiche a republier (A11)")
    verifie(b.requete("GET", "/pages"), (200, {"actif": False, "url": None, "branche": None}), "GET /pages : Pages inactif (faux gh)")
    tqe_gh, eqw.publication.GH = eqw.publication.GH, [sys.executable, "-c", "import sys; sys.stderr.write('HTTP 401'); sys.exit(1)"]
    statut, pg = b.requete("GET", "/pages")
    eqw.publication.GH = tqe_gh
    verifie((statut, pg["actif"], "401" in pg.get("erreur", "")), (200, None, True), "GET /pages : gh en erreur, etat inconnu (pas de 409)")
    verifie(b.requete("POST", "/pages/activer", {})[0], 409, "POST /pages/activer : refus de gh rendu en 409")
    verifie(b.requete("POST", "/publier", {})[0], 400, "POST /publier sans empreinte : 400")
    b.builds = ["pio"]
    verifie(b.requete("POST", "/publier", {"empreinte": p["empreinte"]})[0], 409, "POST /publier pendant un build : 409")
    b.builds = []
    statut, r = b.requete("POST", "/publier", {"empreinte": p["empreinte"]})
    verifie((statut, r["sha"], tpub.arbre(nu)), (200, tpub.git(nu, "rev-parse", "refs/heads/etiquettes"), [".nojekyll", f"{CUVE}.html"]),
            "POST /publier : fiche poussee sur la branche etiquettes")
    verifie(b.requete("GET", "/suivi")[1]["suivi"][CUVE].get("a_republier_fiche"), False, "GET /suivi apres publication : a jour")


def main():
    dossier = tempfile.mkdtemp(prefix="banc_etiquettes_qr_web_")
    b = Banc(dossier)
    try:
        for test in (test_page, test_cartes, test_reglage_persist, test_csrf, test_apercu, test_ecriture, test_gabarit_impression, test_suivi):
            test(b)
        test_publication(b, dossier)                  # en dernier : fait de la copie un depot git
    finally:
        b.ferme()
        shutil.rmtree(dossier, ignore_errors=True)
    print(("VERT" if not tqe.ECHECS else f"ROUGE : {len(tqe.ECHECS)} echec(s)"))
    return 1 if tqe.ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
