"""Sonde Chrome de la page de reglage des durees des volets, /volets (plan visuel-reglage-volets, A6).

UTILISATION (a la main ; aucun pio, aucune carte ; Chrome tourne ~60 s)
    %USERPROFILE%\\.platformio\\penv\\Scripts\\python.exe outils_docs/scripts_python/outils_pc/test_reglage_volets_chrome.py
        [--sd DOSSIER] [--capture DOSSIER]
Code de sortie 0 = vert. --sd : eprouve DOSSIER/{html,js,css}/reglageVolets.* au lieu de data/sd (temoin : copie sans
« Sinon, Annuler » -> rouge). Montage (serveur local + Chrome sans interface, Chrome tue meme en echec, profil
sonde_reglage_volets_*) repris de test_volets_chrome.py.

Le serveur simule joue la carte : GET /volets assemble la page comme data/fs/vrPages.be::route (style, gabarit,
window.VOLETS_REGLAGE = facade() + etat, script) ; GET /volets?f=etat rend l'etat de vrReglage.be::etatPage() pose par la
sonde ; POST /volets est note (action, id), applique l'etat suivant de la file et repond {"ok","message","etat"} (ou 500).
Scenarios : 2 boutons par les clics (POST, textes de chaque etape, chronometre, resultat avec MPU6050 et valeurs a
recopier), cadence de lecture (500 ms en reglage, 3 s sinon), carte injoignable (connexion coupee, puis carte lente :
message, rien de l'etat ni du resultat), 500 apres « debut » alors que l'etat dit « pret », 1 bouton, aucun bouton,
porte de garage en chronometre, arrets (sens inverse, bloque, arret, delai, refus), nom de volet avec balise (texte),
mode sombre lisible, largeur de 320 px, aucune erreur de la console.
"""

import argparse
import json
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[2]
sys.path.insert(0, str(ICI))
from test_volets_chrome import ECHECS, Montage, verifie   # serveur, Chrome et DevTools de la sonde d'A5

FACADES = {
    "rdc": {"toit": "deuxPans", "rafraichissement": 2345, "ouvertures": [
        {"id": 2, "nom": "Volet cuisine", "type": "fenetre", "place": 1, "inverse": 0, "tempsMontee": 25, "tempsDescente": 25, "inclinaison": None},
        {"id": 3, "nom": "Trappe <b>du</b> grenier", "type": "trappe", "place": 2, "inverse": 0, "tempsMontee": 20, "tempsDescente": 20,
         "inclinaison": {"ouvert": 85, "ferme": 3}},
        {"id": 1, "nom": "Volet porte d'entrée", "type": "porte", "place": 3, "inverse": 0, "tempsMontee": 25, "tempsDescente": 25, "inclinaison": None}]},
    "garage": {"toit": "unPan", "rafraichissement": 2345, "ouvertures": [
        {"id": 1, "nom": "Volet Roulant Garage", "type": "garage", "place": 1, "inverse": 1, "tempsMontee": 30, "tempsDescente": 30, "inclinaison": None}]},
}
MESSAGES = {     # vrReglage.MESSAGES : [moteur, chrono]
    "pret": ["Prêt : un appui fait monter le volet.", "Prêt : lancez la porte, puis cliquez « Départ »."],
    "montee": ["Montée : un appui à l'arrivée en haut arrête le volet.", "Montée : cliquez « Arrivée » quand la porte est en haut."],
    "haut": ["En haut après 24 s : un appui fait descendre le volet.", "En haut après 24 s : lancez la porte, puis cliquez « Départ »."],
    "descente": ["Descente : un appui à l'arrivée en bas arrête le volet.", "Descente : cliquez « Arrivée » quand la porte est en bas."]}
REPOS = {"actif": False, "etape": None}
TETE = ("<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1,"
        "user-scalable=no'/><title>Réglage des volets</title><style>:root{--c_bg:#252525;--c_frm:#4f4f4f;--c_ttl:#eaeaea;--c_txt:#eaeaea;"
        "--c_txtwrn:#ff5661;--c_txtscc:#008000;--c_btn:#1fa3ec;--c_btnoff:#08405e;--c_btntxt:#faffff;--c_btnhvr:#0e70a4;--c_btnrst:#d43535;"
        "--c_btnrsthvr:#931f1f;--c_in:#ddd;--c_intxt:#000;--c_csl:#1f1f1f;--c_csltxt:#65c115}"
        "div,fieldset,input,select{padding:5px;font-size:1em;}p{margin:0.5em 0;}select{width:100%;background:var(--c_in);color:var(--c_intxt);}"
        "body{text-align:center;font-family:verdana,sans-serif;background:var(--c_bg);}td{padding:0px;}"
        "button{border:0;border-radius:0.3rem;background:var(--c_btn);color:var(--c_btntxt);line-height:2.4rem;font-size:1.2rem;width:100%;}"
        ".bred{background:var(--c_btnrst);}a{color:var(--c_btn);text-decoration:none;}</style></head><body>"
        "<div id='conteneur' style='background:var(--c_bg);text-align:left;display:inline-block;color:var(--c_txt);min-width:340px;'>"
        "<div style='text-align:center;color:var(--c_ttl);'><h3>Sonde</h3><h2>Réglage des volets</h2></div>")
PIED = "<p></p><form action='/' method='get'><button>Menu principal</button></form></div></body></html>"


def etat(etape, id_=2, type_="moteur", boutons=(3, 4), chrono_ms=0, mesures=None, mpu=None, cause=None, message=None, cle="VR2"):
    """Etat de vrReglage.etatPage() ; message par defaut : celui de la carte pour l'etape."""
    chrono = type_ == "chrono"
    if message is None:
        message = MESSAGES.get(etape, ["", ""])[1 if chrono else 0]
    return {"actif": etape in ("pret", "montee", "haut", "descente"), "id": id_, "cle": cle, "nom": "Volet " + cle, "type": type_,
            "etape": etape, "chrono_ms": chrono_ms, "mesures": mesures or {}, "avant": {"tempsMontee": 25, "tempsDescente": 25},
            "boutons": [] if chrono else list(boutons), "mpu": mpu, "cause": cause, "message": message}


class CarteReglage(BaseHTTPRequestHandler):
    sd = RACINE / "data/sd"
    facade = FACADES["rdc"]
    etat = REPOS
    file = []            # etats poses par les POST suivants, dans l'ordre
    posts = []           # (action, id) recus
    lectures = 0         # GET ?f=etat recus
    code_post = 200
    refus = None         # message d'un ordre refuse par la carte (200, ok faux, etat inchange)
    panne = None         # None, "coupe" (connexion fermee sans reponse) ou "lente" (6 s sans reponse)

    def log_message(self, format, *args):
        pass

    def _envoie(self, code, type_, corps):
        corps = corps.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", type_)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def _fichier(self, rel):
        f = CarteReglage.sd / rel
        return f.read_text(encoding="utf-8") if f.is_file() else ""

    def _panne(self):
        if CarteReglage.panne == "lente":
            time.sleep(6)
        if CarteReglage.panne:
            self.close_connection = True
            return True
        return False

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path != "/volets":
            return self._envoie(404, "text/plain", "inconnu")
        if urllib.parse.parse_qs(url.query).get("f") == ["etat"]:
            CarteReglage.lectures += 1
            if not self._panne():
                self._envoie(200, "application/json", json.dumps(CarteReglage.etat))
            return
        d = dict(CarteReglage.facade, etat=CarteReglage.etat)
        self._envoie(200, "text/html; charset=utf-8", TETE + "<style>" + self._fichier("css/reglageVolets.css") + "</style>"
                     + self._fichier("html/reglageVolets.html") + "<script>window.VOLETS_REGLAGE=" + json.dumps(d).replace("</", "<\\/")
                     + ";</script><script>" + self._fichier("js/reglageVolets.js") + "</script>" + PIED)

    def do_POST(self):
        champs = urllib.parse.parse_qs(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
        CarteReglage.posts.append((champs.get("action", [""])[0], champs.get("id", [""])[0]))
        if self._panne():
            return
        if CarteReglage.refus:
            return self._envoie(200, "application/json", json.dumps({"ok": False, "message": CarteReglage.refus, "etat": CarteReglage.etat}))
        if CarteReglage.file:
            CarteReglage.etat = CarteReglage.file.pop(0)
        if CarteReglage.code_post == 500:
            return self._envoie(500, "application/json", json.dumps({"ok": False, "message": "Erreur interne de la carte"}))
        self._envoie(200, "application/json", json.dumps({"ok": True, "message": CarteReglage.etat.get("message", ""), "etat": CarteReglage.etat}))


# -- lecture de la page -------------------------------------------------------------------------------------------

LIT = """(() => { const t = id => { const e = document.getElementById(id); return e && e.offsetParent !== null ? e.textContent.trim() : ''; };
  const vu = s => { const e = document.querySelector(s); return !!e && e.offsetParent !== null; };
  return {etape: t('rv_etape'), message: t('rv_message'), chrono: t('rv_chrono'), question: t('rv_question'), cause: t('rv_cause'),
    resultat: t('rv_resultat'), recopie: t('rv_recopie'), injoignable: t('rv_injoignable'), appui: t('rv_appui'), note: t('rv_note'),
    aide: [...document.querySelectorAll('#rv [data-rv]')].filter(e => e.offsetParent !== null).map(e => e.getAttribute('data-rv')),
    aideTexte: [...document.querySelectorAll('#rv [data-rv]')].filter(e => e.offsetParent !== null).map(e => e.textContent).join(' '),
    debut: vu('#rv_debut'), suivant: vu('#rv_suivant') ? document.getElementById('rv_suivant').textContent.trim() : null,
    annuler: vu('#rv_annuler'), libre: !(document.getElementById('rv_debut') || {}).disabled, volet: (document.getElementById('rv_volet') || {}).value,
    choixBloque: !!(document.getElementById('rv_volet') || {}).disabled}; })()"""


def lit(m):
    return m.cdp.js(LIT) or {}


def attend_page(m, condition, delai=6.0):
    """Attend que condition(etat lu de la page) soit vraie ; renvoie le dernier etat lu."""
    limite = time.monotonic() + delai
    while True:
        p = lit(m)
        if (isinstance(p, dict) and "_exception_sonde" not in p and condition(p)) or time.monotonic() > limite:
            return p
        time.sleep(0.1)


def clic(m, bouton):
    m.cdp.js(f"document.getElementById('{bouton}').click(); 1")


def attend_post(n, delai=4.0):
    limite = time.monotonic() + delai
    while len(CarteReglage.posts) < n and time.monotonic() < limite:
        time.sleep(0.05)
    return CarteReglage.posts[n - 1] if len(CarteReglage.posts) >= n else None


def ouvre(m, facade, e, largeur=360):
    CarteReglage.facade, CarteReglage.etat, CarteReglage.file, CarteReglage.code_post, CarteReglage.panne = FACADES[facade], e, [], 200, None
    CarteReglage.refus = None
    m.cdp.appel("Emulation.setDeviceMetricsOverride", width=largeur, height=900, deviceScaleFactor=1, mobile=True)
    m.cdp.appel("Page.navigate", url="about:blank")
    time.sleep(0.2)
    return verifie(bool(m.ouvre("volets")), True, f"{facade} : page chargée")


def lectures_pendant(secondes):
    avant = CarteReglage.lectures
    time.sleep(secondes)
    return CarteReglage.lectures - avant


def capture(m, dossier, nom):
    if dossier:
        time.sleep(0.3)
        m.cdp.capture(str(Path(dossier) / nom))


QUESTION = {"montee": "Le volet monte-t-il ? Sinon, Annuler.", "descente": "Le volet descend-il ? Sinon, Annuler."}


def parcours(m, libelle, etats, boutons_attendus, par_clic, capture_montee=None):
    """Etapes pret -> montee -> haut -> descente : texte de l'etape, message de la carte, question du sens, chronometre,
    libelle du bouton d'etape. par_clic : l'etat suivant est pose par le POST du bouton (POST verifie), sinon par la sonde."""
    for i, (e, bouton) in enumerate(zip(etats, boutons_attendus)):
        et = e["etape"]
        if i and par_clic:
            CarteReglage.file = [e]
            n = len(CarteReglage.posts) + 1
            clic(m, "rv_suivant")
            verifie(attend_post(n), ("appui", str(e["id"])), f"{libelle} : POST appui -> {et}")
        elif i:
            CarteReglage.etat = e
        p = attend_page(m, lambda p: e["message"] in p.get("message", "") and p.get("suivant") == bouton)
        verifie([e["message"] in p.get("message", ""), p.get("suivant"), p.get("annuler"), p.get("debut")], [True, bouton, True, False],
                f"{libelle} : étape {et} : message de la carte, bouton « {bouton} », « Annuler », pas « Régler les durées »")
        q = p.get("question", "")
        verifie(QUESTION[et] in q if et in QUESTION else q, True if et in QUESTION else "", f"{libelle} : étape {et} : question du sens ({q!r})")
        if e["chrono_ms"]:
            verifie("1,5 s" in p.get("chrono", ""), True, f"{libelle} : étape {et} : chronomètre à 1,5 s ({p.get('chrono')!r})")
        if et == "montee" and capture_montee:
            capture_montee()


def sonde_deux_boutons(m, dossier):
    ouvre(m, "rdc", REPOS)
    time.sleep(0.4)
    p = lit(m)
    noms = m.cdp.js("[...document.querySelectorAll('#rv_volet option')].map(o => [o.value, o.textContent])")
    verifie(noms, [["2", "Volet cuisine"], ["3", "Trappe <b>du</b> grenier"], ["1", "Volet porte d'entrée"]],
            "rdc : choix du volet, noms en texte (balise affichée telle quelle)")
    verifie(m.cdp.js("[...document.querySelectorAll('#rv b')].some(b => b.textContent === 'du')"), False,
            "rdc : aucune balise venue de la carte insérée dans la page")
    verifie([p.get("aide"), p.get("debut"), p.get("suivant"), p.get("annuler"), p.get("etape")], [["inconnu"], True, None, False, ""],
            "rdc : avant le réglage : explications générales, « Régler les durées » seul")
    prep = m.cdp.js("document.getElementById('rv_preparation') ? document.getElementById('rv_preparation').textContent : ''")
    verifie(["fermé" in prep, "butée basse" in prep], [True, True], "rdc : préparation : volet fermé, en butée basse")
    n = lectures_pendant(2.5)
    verifie(n <= 1, True, f"rdc : hors réglage, état lu toutes les 3 s ({n} lecture(s) en 2,5 s)")

    CarteReglage.posts.clear()
    CarteReglage.file = [etat("pret")]
    clic(m, "rv_debut")
    verifie(attend_post(1), ("debut", "2"), "rdc : « Régler les durées » -> POST action=debut, id=2")
    p = attend_page(m, lambda p: p.get("aide") == ["moteur"])
    verifie([p.get("aide"), "l'un ou l'autre" in p.get("appui", ""), p.get("choixBloque")], [["moteur"], True, True],
            "rdc : 2 boutons : explications du volet à moteur, « l'un ou l'autre des deux boutons », choix bloqué")
    tout = m.cdp.js("document.getElementById('rv').innerText")
    verifie(["120 s" in p.get("aideTexte", ""), "Annuler" in p.get("aideTexte", ""), "persist de la carte" in tout], [True, True, True],
            "rdc : explications : délai de 120 s, annulation, ce qui est écrit")
    n = lectures_pendant(2.2)
    verifie(n >= 3, True, f"rdc : en réglage, état lu toutes les 500 ms ({n} lectures en 2,2 s)")

    etats = [etat("pret"), etat("montee", chrono_ms=1500), etat("haut", mesures={"tempsMontee": 24}), etat("descente", chrono_ms=1500,
             mesures={"tempsMontee": 24})]
    parcours(m, "rdc 2 boutons", etats, ["Étape suivante"] * 4, True, lambda: capture(m, dossier, "reglage_montee_2_boutons.png"))

    CarteReglage.file = [etat("fini", mesures={"tempsMontee": 24, "tempsDescente": 22}, mpu={"tempsMontee": 23.4, "tempsDescente": 21.8},
                              message="Durées écrites dans le persist de la carte : montée 24 s, descente 22 s.")]
    n = len(CarteReglage.posts) + 1
    clic(m, "rv_suivant")
    verifie(attend_post(n), ("appui", "2"), "rdc : POST appui -> fini")
    p = attend_page(m, lambda p: p.get("resultat"))
    r, c = p.get("resultat", ""), p.get("recopie", "")
    verifie([x in r for x in ("24 s", "22 s", "25 s", "23,4 s", "21,8 s", "MPU6050")], [True] * 6,
            "rdc : résultat : durées mesurées (24, 22), d'avant (25) et du MPU6050 (23,4 ; 21,8)")
    verifie(["drivers.voletRoulants.environnement.VRs.VR2.tempsMontee" in c, "= 24" in c,
             "drivers.voletRoulants.environnement.VRs.VR2.tempsDescente" in c, "= 22" in c], [True] * 4, "rdc : valeurs à recopier dans le persist du dépôt")
    verifie(["flash série" in r, "envoi du FS" in r, "_persist.json" in r], [True] * 3, "rdc : avertissement du flash série et de l'envoi du FS")
    verifie([p.get("debut"), p.get("suivant"), p.get("annuler"), p.get("choixBloque"), p.get("question")], [True, None, False, False, ""],
            "rdc : fini : « Régler les durées » revient, choix libre")
    capture(m, dossier, "reglage_fini_mpu.png")
    sonde_sombre(m)
    sonde_320(m)

    # Carte injoignable (connexion coupee) : message, plus aucun resultat ; puis retour
    CarteReglage.panne = "coupe"
    p = attend_page(m, lambda p: p.get("injoignable"), 8)
    verifie(["injoignable" in p.get("injoignable", ""), p.get("resultat"), p.get("recopie"), p.get("etape"), p.get("message")],
            [True, "", "", "", ""], "injoignable (connexion coupée) : message visible, ni état ni résultat")
    verifie("24 s" in m.cdp.js("document.getElementById('rv').innerText"), False, "injoignable : aucune durée affichée")
    CarteReglage.panne = None
    p = attend_page(m, lambda p: p.get("resultat") and not p.get("injoignable"), 8)
    verifie([bool(p.get("resultat")), p.get("injoignable")], [True, ""], "injoignable : carte revenue, état relu et affiché")


def sonde_lente_et_500(m):
    # Carte lente pendant une montee : la lecture abandonne, message, ni chronometre ni question
    ouvre(m, "rdc", etat("montee", chrono_ms=1500))
    attend_page(m, lambda p: p.get("question"))
    CarteReglage.panne = "lente"
    p = attend_page(m, lambda p: p.get("injoignable"), 9)
    verifie([bool(p.get("injoignable")), p.get("chrono"), p.get("question"), p.get("etape"), p.get("annuler")], [True, "", "", "", True],
            "injoignable (carte lente) : message, ni chronomètre ni question, « Annuler » reste")
    CarteReglage.panne = None
    attend_page(m, lambda p: not p.get("injoignable"), 10)

    # Ordre refuse par la carte (volet qui roule) : la raison est affichee, rien ne change
    ouvre(m, "rdc", REPOS)
    CarteReglage.refus = "Le volet roule : attendez qu'il soit arrêté en bas."
    clic(m, "rv_debut")
    p = attend_page(m, lambda p: p.get("note") and p.get("libre"))     # boutons rendus a la fin de l'envoi
    verifie([CarteReglage.refus in p.get("note", ""), p.get("debut"), p.get("suivant")], [True, True, None], "debut refusé : raison de la carte affichée")
    CarteReglage.refus = None

    # 500 apres « debut » alors que l'ordre a ete pris : la page montre l'etat relu (pret)
    CarteReglage.posts.clear()
    CarteReglage.code_post = 500
    CarteReglage.file = [etat("pret")]
    clic(m, "rv_debut")
    verifie(attend_post(1), ("debut", "2"), "500 : POST debut envoyé")
    p = attend_page(m, lambda p: p.get("suivant"))
    verifie([MESSAGES["pret"][0] in p.get("message", ""), p.get("suivant"), p.get("annuler"), p.get("debut")], [True, "Étape suivante", True, False],
            "500 après debut, état « pret » : la page montre « pret »")
    CarteReglage.code_post = 200
    CarteReglage.file = [etat("annule", message="Réglage annulé : rien n'a été écrit.")]
    clic(m, "rv_annuler")
    verifie(attend_post(2), ("annuler", "2"), "Annuler -> POST action=annuler, id=2")
    p = attend_page(m, lambda p: p.get("debut"))
    verifie([p.get("debut"), p.get("annuler"), "rien n'a été écrit" in p.get("message", ""), p.get("resultat")], [True, False, True, ""],
            "annulé : message de la carte, aucun résultat")


def sonde_un_bouton_et_arrets(m):
    ouvre(m, "rdc", etat("pret", id_=1, boutons=(1,), cle="VR1"))
    p = attend_page(m, lambda p: p.get("appui"))
    verifie([p.get("volet"), p.get("aide"), "bouton du volet" in p.get("appui", ""), "l'un ou l'autre" in p.get("appui", "")],
            ["1", ["moteur"], True, False], "1 bouton : volet 1 choisi, « le bouton du volet »")
    etats = [etat(e, id_=1, boutons=(1,), cle="VR1", chrono_ms=1500 if e in ("montee", "descente") else 0) for e in ("pret", "montee", "haut", "descente")]
    parcours(m, "1 bouton", etats, ["Étape suivante"] * 4, False)
    CarteReglage.etat = etat("pret", id_=1, boutons=(), cle="VR1")
    p = attend_page(m, lambda p: "bouton du volet" not in p.get("appui", "x bouton du volet"))
    verifie(["Étape suivante" in p.get("appui", ""), "bouton du volet" in p.get("appui", "")], [True, False], "aucun bouton : « Étape suivante » seul")

    arrets = [("sens inverse", "sens inverse", "mauvais sens"), ("bloque", "bloqué", "aucun mouvement"), ("arret", "arrêt inattendu", "sans appui")]
    for cause, mot, explication in arrets:
        CarteReglage.etat = etat("annule", id_=1, cle="VR1", cause=cause, mesures={"tempsMontee": 24},
                                 message=f"Le volet s'est arrêté sans appui ({cause}) : rien n'a été écrit.")
        p = attend_page(m, lambda p: mot in p.get("cause", ""))
        verifie([mot in p.get("cause", ""), explication in p.get("cause", ""), p.get("resultat"), p.get("debut")], [True, True, "", True],
                f"arrêt « {cause} » : cause « {mot} » expliquée, aucun résultat")
    for et, mot in (("delai", "120 s"), ("refus", "2 s")):
        CarteReglage.etat = etat(et, id_=1, cle="VR1", message="rien n'a été écrit")
        p = attend_page(m, lambda p: mot in p.get("etape", "") + p.get("cause", ""))
        verifie([mot in p.get("etape", "") + p.get("cause", ""), p.get("resultat")], [True, ""], f"étape {et} : « {mot} » expliqué, aucun résultat")


def sonde_chrono(m, dossier):
    ouvre(m, "garage", etat("pret", id_=1, type_="chrono", cle="VR1"))
    p = attend_page(m, lambda p: p.get("aide") == ["chrono"])
    t = p.get("aideTexte", "")
    verifie([p.get("aide"), "ne commande" in t, "arrêtez" in t.lower() or "arrêter" in t], [["chrono"], True, True],
            "chrono : explications de la porte de garage (la carte ne commande rien, l'arrêt reste à l'utilisateur)")
    capture(m, dossier, "reglage_chrono_pret.png")
    CarteReglage.posts.clear()
    etats = [etat(e, id_=1, type_="chrono", cle="VR1", chrono_ms=1500 if e in ("montee", "descente") else 0) for e in ("pret", "montee", "haut", "descente")]
    parcours(m, "chrono", etats, ["Départ", "Arrivée", "Départ", "Arrivée"], True)
    verifie("vous-même" in lit(m).get("question", ""), True, "chrono : en descente, la question rappelle d'arrêter la porte soi-même")


def contraste(c1, c2):
    def lum(c):
        r = [x / 255 for x in c[:3]]
        r = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in r]
        return 0.2126 * r[0] + 0.7152 * r[1] + 0.0722 * r[2]
    a, b = sorted((lum(c1), lum(c2)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def sonde_sombre(m):
    """Contraste de chaque texte de la page (hors boutons : palette de Tasmota) sur son fond effectif, theme sombre."""
    paires = m.cdp.js("""(() => { const rgb = s => (s.match(/[\\d.]+/g) || []).map(Number);
      const fond = e => { for (; e; e = e.parentElement) { const c = rgb(getComputedStyle(e).backgroundColor); if (c.length === 3 || c[3] > 0) return c; } return [255, 255, 255]; };
      return [...document.querySelectorAll('#rv *')].filter(e => e.offsetParent !== null && !e.closest('button,select')
        && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()))
        .map(e => [e.id || e.tagName, rgb(getComputedStyle(e).color), fond(e)]); })()""") or []
    faibles = [(n, round(contraste(c, f), 1)) for n, c, f in paires if contraste(c, f) < 4.5]
    verifie([len(paires) > 10, faibles], [True, []], f"mode sombre : {len(paires)} textes, contraste >= 4,5 partout")


def sonde_320(m):
    m.cdp.appel("Emulation.setDeviceMetricsOverride", width=320, height=900, deviceScaleFactor=1, mobile=True)
    time.sleep(0.4)
    deborde = m.cdp.js("""(() => { const rv = document.getElementById('rv').getBoundingClientRect(), c = document.getElementById('conteneur').getBoundingClientRect();
      return [rv.right <= c.right + 1, [...document.querySelectorAll('#rv *')].filter(e => e.offsetParent !== null
        && e.getBoundingClientRect().right > rv.right + 1).map(e => e.id || e.tagName)]; })()""")
    verifie(deborde, [True, []], "320 px : rien ne dépasse la colonne de Tasmota")
    m.cdp.appel("Emulation.setDeviceMetricsOverride", width=360, height=900, deviceScaleFactor=1, mobile=True)


def principal():
    options = argparse.ArgumentParser(description="Sonde Chrome de la page de réglage des durées des volets.")
    options.add_argument("--sd", default=str(RACINE / "data/sd"), help="dossier qui porte html/, js/, css/reglageVolets.*")
    options.add_argument("--capture", metavar="DOSSIER", help="dossier des captures (360 px)")
    args = options.parse_args()
    CarteReglage.sd = Path(args.sd)
    print(f"page éprouvée : {CarteReglage.sd}", flush=True)
    if args.capture:
        Path(args.capture).mkdir(parents=True, exist_ok=True)
    m = None
    try:
        m = Montage(CarteReglage, "sonde_reglage_volets_")
        sonde_deux_boutons(m, args.capture)
        sonde_lente_et_500(m)
        sonde_un_bouton_et_arrets(m)
        sonde_chrono(m, args.capture)
        erreurs = [x for x in m.cdp.erreurs() if "favicon.ico" not in x and "Failed to load resource" not in x]
        verifie(erreurs, [], "aucune erreur dans la console (hors ressources refusées par la carte simulée)")
    except FileNotFoundError as erreur:
        print(f"BLOQUE : {erreur}")
        return 3
    except Exception as erreur:
        verifie(repr(erreur), "pas d'exception de la sonde", "sonde : déroulement")
    finally:
        if m:
            m.ferme()
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
