"""Banc de assistant_persist_elements (editeur des entrees/sorties du bloc metier, A7).

Code de sortie 0 = vert. Lecture seule des vrais persists du parc (jamais imprimes : un echec n'affiche que des
chemins, des noms de groupe et des broches) ; la generation et la creation se jouent dans un depot d'essai.
  - rejeu_environnement : l'environnement du bloc metier PRINCIPAL de chaque carte du parc (la cuve d'abord),
    relu par reponses_depuis_persist puis regenere par persist, est celui du vrai persist ;
  - couverture_cles : chaque cle d'element du parc est decrite par metier.elements (gabarit ou optionnelles) ;
  - broches : plage de la puce lue dans data/fs/configGlobal.be, doublons, broches des drivers ;
  - le parc entier passe verifie_elements sans refus (pas de faux refus) ;
  - USE_DS18x20 est pose dans la section du .h des qu'un thermometre existe.
A lancer avec le Python du penv :
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" -u outils_docs/scripts_python/outils_pc/test_assistant_persist_elements.py
"""

import copy
import sys
import tempfile
from pathlib import Path

import assistant_persist_creation as apc
import assistant_persist_elements as ape
import assistant_persist_generation as gen
import assistant_persist_modele as apm
import assistant_persist_parc as parc
import test_assistant_persist_creation as tac
from assistant_persist_generation import Reponses
from test_fichiers_berry_creation import RACINE

ECHECS = []
CONFIG = RACINE / "data/fs/configGlobal.be"
CUVE = "data/garage/tasmota32s3-capteurs-cuve-modbus"


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def _env(dossier):
    _, lieu, carte = dossier.split("/")
    prefixe, _, nom = carte.partition("-")
    return f"{prefixe}-{lieu}-{nom}"


def cartes():
    """[(dossier, donnees)] des persists lisibles du parc ayant un bloc metier."""
    res = []
    for rel, donnees, _ in apm.persists_du_depot(RACINE):
        if isinstance(donnees, dict) and [k for k in donnees.get("modules", {}) if k != "activation"]:
            res.append((rel.rsplit("/", 1)[0], donnees))
    return res


def rejoue(modele, dossier, donnees):
    r = gen.reponses_depuis_persist(modele, donnees, _env(dossier), RACINE)
    v = gen.variables(RACINE, r)
    return r, gen.persist(modele, r, v, parc.secrets(RACINE, v["reseau1"], v["reseau2"]))


def relai(pin, nom="Relais", **kw):
    e = copy.deepcopy(ape.gabarits_elements(MODELE)["relais"])
    e.update(pin=pin, nom=nom, **kw)
    return e


def test_gabarits(modele):
    g = ape.gabarits_elements(modele)
    verifie(tuple(g), ape.GROUPES_ELEMENTS, "gabarits : un par groupe, dans l'ordre de GROUPES_ELEMENTS")
    socle = {"activation", "nom", "id", "pin", "type", "virtuel", "relaisLie"}
    # un relais du parc n'a jamais de relaisLie (rapport A7 : ecart au brief, qui le met au socle)
    verifie([x for x in g if not (socle - ({"relaisLie"} if x == "relais" else set())) <= set(g[x])], [],
            "gabarits : le socle activation, nom, id, pin, type, virtuel, relaisLie (sauf relais : sans relaisLie dans le parc)")
    verifie(sorted({"afficheWeb", "value", "etat", "timer", "publishMQTT", "timestamp", "idModBus"} - set(g["relais"])), [],
            "gabarits : le relais porte afficheWeb, value, etat, timer, publishMQTT, timestamp, idModBus")
    opt = modele["metier"]["elements"]["relais"]["optionnelles"]
    verifie(sorted({"channel", "nbLeds"} - set(opt)), [], "gabarits : channel et nbLeds (LED) sont des cles optionnelles du relais")
    verifie({x: ape.singulier(modele, x) for x in g},
            {"boutons": "bouton", "interrupteurs": "interrupteur", "relais": "relai", "capteurs": "capteur",
             "compteurs": "compteur", "thermometres": "thermometre", "analogiques": "analogique"},
            "singuliers lus dans le parc (relais -> relai)")
    g["relais"]["nom"] = "touche"
    verifie(ape.gabarits_elements(modele)["relais"]["nom"] != "touche", True, "gabarits : une copie (le modele n'est pas modifie)")


def test_broches():
    ordre = {"ESP32": 36, "ESP32S3": 38, "ESP32P4": 55}
    for puce, n in ordre.items():
        verifie(len(ape.broches_valides(puce)), n, f"broches_valides({puce}) : {n} GPIO de configGlobal.be")
    s3 = ape.broches_valides("ESP32S3")
    verifie((s3[:3], s3[-1], 22 in s3, 33 in s3), ([0, 1, 2], 48, False, True), "S3 : 0-21 et 33-48 (pas de 22 a 32)")
    verifie(ape.broches_valides("ESP32")[:6], [0, 1, 2, 3, 4, 5], "ESP32 : ordre de configGlobal.be (0..5 d'abord)")
    verifie(ape.broches_valides("ESP32")[24:28], [6, 7, 8, 11], "ESP32 : 6, 7, 8, 11 apres 27, comme ordreGPIO")
    verifie(ape.broches_valides("ESP32P4")[-1], 54, "P4 : jusqu'a GPIO54")
    try:
        ape.broches_valides("ESP8266")
        verifie(False, True, "puce inconnue : ValueError")
    except ValueError:
        verifie(True, True, "puce inconnue : ValueError")


def test_rejeu_environnement(modele):
    for dossier, donnees in cartes():
        r, obj = rejoue(modele, dossier, donnees)
        principal = r.metiers[0]
        vrai = donnees["modules"][principal]["environnement"]
        obtenu = obj["modules"][principal]["environnement"]
        ecarts = [g for g in sorted(set(vrai) | set(obtenu)) if vrai.get(g) != obtenu.get(g)]
        verifie(ecarts, [], f"rejeu_environnement : {dossier.rsplit('/', 1)[-1]} ({principal}) : environnement identique")
        if dossier == CUVE:
            verifie(obtenu == vrai, True, "rejeu_environnement : l'environnement de la cuve rejoue = le vrai")


def test_couverture(modele):
    inconnues = {}
    for dossier, donnees in cartes():
        for metier, bloc in donnees["modules"].items():
            if metier == "activation" or not isinstance(bloc, dict):
                continue
            for groupe, contenu in bloc.get("environnement", {}).items():
                for el in contenu.values():
                    if not isinstance(el, dict):
                        continue
                    connues = set(modele["metier"]["elements"][groupe]["gabarit"]) | set(modele["metier"]["elements"][groupe]["optionnelles"])
                    for c in el:
                        if c not in connues:
                            inconnues.setdefault(f"{groupe}.{c}", []).append(dossier.rsplit("/", 1)[-1])
    verifie(inconnues, {}, "couverture : toute cle d'element du parc est dans metier.elements (gabarit ou optionnelles)")
    verifie(ape.releve_modele(RACINE, modele) == modele["metier"]["elements"], True,
            "couverture : metier.elements = ce que le parc donne (releve_modele)")


def test_verifie_elements():
    drivers = {"ModBus RX": 4, "ModBus TX": 5}
    verifie(ape.verifie_elements("ESP32S3", {"relais": [relai(6), relai(7, "R2")]}, drivers), [], "verifie : rien a refuser")
    r = ape.verifie_elements("ESP32S3", {"relais": [relai(6), relai(6, "R2")]}, drivers)
    verifie((len(r), "6" in (r[0] if r else "")), (1, True), "broche_double : refus, la broche est nommee")
    r = ape.verifie_elements("ESP32", {"relais": [relai(40)]}, {})
    verifie((len(r), "40" in (r[0] if r else "")), (1, True), "broche_hors_plage_esp32 : GPIO40 refuse sur ESP32")
    verifie(ape.verifie_elements("ESP32S3", {"relais": [relai(40)]}, {}), [], "S3 : GPIO40 accepte")
    verifie(len(ape.verifie_elements("ESP32S3", {"relais": [relai(25)]}, {})), 1, "S3 : GPIO25 refuse (trou 22-32)")
    verifie(len(ape.verifie_elements("ESP32S3", {"relais": [relai(-5)]}, {})), 1, "broche < -1 refusee")
    r = ape.verifie_elements("ESP32S3", {"relais": [relai(4)]}, drivers)
    verifie((len(r), "ModBus RX" in (r[0] if r else "")), (1, True), "broche_driver : un relais sur la broche RX ModBus est refuse")
    verifie(ape.verifie_elements("ESP32S3", {"relais": [relai(4)]}, {}), [], "temoin : sans les broches des drivers, rien")
    verifie(ape.verifie_elements("ESP32S3", {"relais": [relai(-1), relai(-1, "R2")]}, drivers), [], "-1 (sans broche) n'est jamais un doublon")
    verifie(ape.verifie_elements("ESP32S3", {"relais": [relai(4, activation="OFF")]}, drivers), [],
            "un element OFF sur une broche prise est tolere (cuve : compteur1 OFF sur la broche RX)")
    verifie(ape.verifie_elements("ESP32", {"relais": [relai(40, activation="OFF")]}, {}), [],
            "un element OFF hors plage est tolere (differentiel ESP32 : compteur1 OFF sur GPIO40)")
    verifie(len(ape.verifie_elements("ESP32S3", {"relais": [relai(6), relai(7, "Relais")]}, {})), 1, "nom en double dans un groupe : refus")
    verifie(ape.verifie_elements("ESP32S3", {"relais": [relai(6)], "boutons": [dict(relai(7), nom="Relais")]}, {}), [],
            "le meme nom dans deux groupes differents est permis")
    r = ape.verifie_elements("ESP32S3", {"relais": [relai(6)], "boutons": [relai(6, "B")]}, {})
    verifie(len(r), 1, "broche en double entre deux groupes : refus")
    verifie(len(ape.verifie_elements("ESP32S3", {"voitures": []}, {})), 1, "groupe inconnu : refus")
    verifie(len(ape.verifie_elements("ESP32S3", {"relais": [dict(relai(6), pin="6")]}, {})), 1, "broche non entiere : refus")
    verifie("".join(ape.verifie_elements("ESP32S3", {"relais": [relai(4)]}, {4: "ModBus RX"})).count("ModBus RX"), 1,
            "broches des drivers : dict broche -> nom accepte aussi")


def test_parc_sans_refus(modele):
    for dossier, donnees in cartes():
        r, _ = rejoue(modele, dossier, donnees)
        pins = ape.broches_drivers(donnees)
        refus = ape.verifie_elements(r.puce, r.elements, pins)
        verifie(refus, [], f"parc_sans_refus : {dossier.rsplit('/', 1)[-1]} : aucun faux refus")


def test_broches_drivers(modele):
    donnees = next(d for dossier, d in cartes() if dossier == CUVE)
    pins = ape.broches_drivers(donnees)
    verifie(sorted(pins.values()), sorted([4, 5, 9, 8, 38, 39, 48]), "broches_drivers : cuve = ModBus RX/TX, I2C, LED (ledLink, led1, ledRGB)")
    verifie(sorted(k for k in pins if "ModBus" in k), ["ModBus RX", "ModBus TX"], "broches_drivers : libelles ModBus")
    copie = copy.deepcopy(donnees)
    copie["drivers"]["ModBus"]["activation"] = "OFF"
    verifie(sorted(ape.broches_drivers(copie).values()), sorted([9, 8, 38, 39, 48]), "broches_drivers : un driver OFF ne compte pas")
    copie = copy.deepcopy(donnees)
    copie["drivers"]["leds"]["environnement"]["leds"]["led1"]["activation"] = "OFF"
    verifie(39 in ape.broches_drivers(copie).values(), False, "broches_drivers : une LED OFF ne compte pas")


def reponses(**kw):
    base = dict(puce="ESP32S3", base="", lieu="garage", nom="piscine", role="esclave", maitre=tac.MAITRE, id=4,
                blocs=["udp", "discovery", "modbus", "i2c", "ruban"], metiers=["piscine"], squelettes=True)
    base.update(kw)
    return Reponses(**base)


def genere(modele, r):
    v = gen.variables(RACINE, r)
    return v, gen.persist(modele, r, v, None)


def test_robustesse(modele):
    donnees = next(d for dossier, d in cartes() if dossier == CUVE)
    for abime in ("texte", ["x"], None):
        copie = copy.deepcopy(donnees)
        copie["drivers"]["ModBus"]["environnement"] = abime
        copie["drivers"]["I2C"]["environnement"]["pinsI2Cs"] = abime
        copie["drivers"]["leds"] = abime
        try:
            pins = ape.broches_drivers(copie)
        except Exception as exc:                      # AttributeError attendu avant correctif
            pins = repr(exc)
        verifie(pins, {}, f"broches_drivers : environnement/pins/pilote valant {abime!r} -> aucun plantage, aucune broche")
    verifie(ape.broches_drivers({"drivers": "x"}), {}, "broches_drivers : drivers pas un objet")
    r = ape.verifie_elements("ESP32S3", {"relais": [relai(6, nom=""), relai(7, nom=5), relai(8, "A", activation="OFF")]}, {})
    verifie(len(r), 2, "nom vide ou non chaine d'un element actif : refuse (un element OFF est ignore)")
    verifie(ape.verifie_elements("ESP32S3", {"relais": [relai(8, nom="", activation="OFF")]}, {}), [], "nom vide d'un element OFF : tolere")
    # configGlobal.be sans la branche de la puce : refus lisibles, pas de plantage
    with tempfile.TemporaryDirectory() as t:
        faux = Path(t) / "data/fs"
        faux.mkdir(parents=True)
        texte = CONFIG.read_text(encoding="utf-8", errors="replace").replace('== "ESP32S3")', '== "ESP32S3x")')
        (faux / "configGlobal.be").write_text(texte, encoding="utf-8")
        try:
            ape.broches_valides("ESP32S3", t)
            verifie(False, True, "broches_valides sans branche S3 : ValueError")
        except ValueError as exc:
            verifie(("configGlobal.be" in str(exc), "ESP32S3" in str(exc)), (True, True), "broches_valides : l'erreur nomme le fichier et la puce")
        r = ape.verifie_elements("ESP32S3", {"relais": [relai(6), relai(-1, "Sans broche"), relai(7, "Eteint", activation="OFF")]}, {}, t)
        verifie((len(r), "ESP32S3" in r[0] and "configGlobal.be" in r[0]), (1, True),
                "puce illisible : seul l'element actif avec broche est refuse, avec le message")
    r = ape.verifie_elements("ESP32S3", {"relais": [relai(6)]}, {}, "/dossier/inexistant")
    verifie(len(r), 1, "configGlobal.be absent : refus, pas de plantage")


def test_persist(modele):
    r = reponses()
    v, obj = genere(modele, r)
    ref = gen.persist(modele, r, v, None)
    verifie(obj["modules"]["piscine"]["environnement"], modele["metier"]["gabarit"]["environnement"],
            "sans elements : l'environnement reste celui du gabarit (comportement inchange)")
    r = reponses(elements={"relais": [relai(6, "Pompe", id=1), relai(7, "Filtre", id=2)]})
    v, obj = genere(modele, r)
    env = obj["modules"]["piscine"]["environnement"]
    verifie(list(env["relais"]), ["relai1", "relai2"], "persist : 2 relais -> relai1, relai2")
    verifie((env["relais"]["relai2"]["pin"], env["relais"]["relai2"]["nom"]), (7, "Filtre"), "persist : contenu de relai2")
    verifie(env["boutons"], {}, "persist : les groupes non fournis restent ceux du gabarit")
    verifie(obj != ref, True, "persist : l'apercu change avec 2 relais")
    r = reponses(elements={"relais": [relai(6)], "analogiques": [], "thermometres": []})
    env = gen.persist(modele, r, v, None)["modules"]["piscine"]["environnement"]
    verifie((env["analogiques"], env["thermometres"]), ({"activation": "OFF", "name": "Capteurs analogiques", "valeurMin": 0,
                                                         "valeurMax": 0}, {"affichageWebSensor": "OFF"}),
            "persist : un groupe vide garde ses reglages de groupe (analogiques OFF faute d'element actif)")
    ana = copy.deepcopy(ape.gabarits_elements(modele)["analogiques"])
    env = gen.persist(modele, reponses(elements={"analogiques": [ana]}), v, None)["modules"]["piscine"]["environnement"]
    verifie(env["analogiques"]["activation"], "ON" if ana["activation"] == "ON" else "OFF",
            "persist : analogiques.activation suit l'activation des elements")
    # seul le metier principal recoit les elements
    r = reponses(metiers=["piscine", "annexe"], elements={"relais": [relai(6)]})
    obj = genere(modele, r)[1]
    verifie(obj["modules"]["annexe"]["environnement"], modele["metier"]["gabarit"]["environnement"], "persist : le 2e metier garde le gabarit")
    # ordre des cles de l'environnement
    verifie(list(obj["modules"]["piscine"]["environnement"]), list(modele["metier"]["gabarit"]["environnement"]),
            "persist : ordre des groupes du gabarit")


def test_coherence(modele):
    def refus(r):
        v, obj = genere(modele, r)
        return gen.coherence(modele, r, obj, gen.autoexec(modele, r), gen.listes_cenv(modele, r), RACINE)
    verifie(refus(reponses(elements={"relais": [relai(6), relai(7, "R2")]})), [], "coherence : 2 relais valides, aucun refus")
    r = refus(reponses(elements={"relais": [relai(6), relai(6, "R2")]}))
    verifie((len(r), "6" in (r[0] if r else "")), (1, True), "coherence : broche en double refusee")
    r = refus(reponses(elements={"relais": [relai(40, "Loin")]}, puce="ESP32"))
    verifie(len(r) >= 1 and any("40" in x for x in r), True, "coherence : broche hors plage refusee")
    v, obj = genere(modele, reponses())
    broche_rx = ape.broches_drivers(obj)
    rx = next((p for k, p in broche_rx.items() if "ModBus RX" in k), None)
    verifie(rx is not None, True, "persist genere : le driver ModBus actif donne sa broche RX")
    r = refus(reponses(elements={"relais": [relai(rx)]}))
    verifie(any("ModBus RX" in x for x in r), True, "coherence : un relais sur la broche RX ModBus est refuse (persist genere)")


def test_ds18x20(modele):
    with tempfile.TemporaryDirectory() as t:
        racine = tac.depot(t)

        def plus(r):
            res = apc.prepare(racine, r)
            return res["refus"], [l for l in res["diff"].splitlines() if l.startswith("+") and "USE_DS18x20" in l]
        termo = copy.deepcopy(ape.gabarits_elements(modele)["thermometres"])
        refus, define = plus(reponses())
        verifie((refus, define), ([], []), "ds18x20 : S3 sans thermometre, pas de define")
        refus, define = plus(reponses(elements={"thermometres": [dict(termo, activation="ON", pin=18)]}))
        verifie((refus, len(define)), ([], 1), "ds18x20 : S3 avec un thermometre, USE_DS18x20 pose une fois")
        refus, define = plus(reponses(puce="ESP32P4", elements={"thermometres": [dict(termo, activation="ON", pin=18)]}))
        verifie((refus, len(define)), ([], 1), "ds18x20 : P4 (le gabarit de puce le pose deja) pas de doublon")
        refus, define = plus(reponses(elements={"thermometres": []}))
        verifie((refus, define), ([], []), "ds18x20 : groupe vide, pas de define")


def principal():
    global MODELE
    modele = MODELE = apm.charge_modele(RACINE)
    for test, args in ((test_gabarits, (modele,)), (test_broches, ()), (test_rejeu_environnement, (modele,)),
                       (test_couverture, (modele,)), (test_verifie_elements, ()), (test_parc_sans_refus, (modele,)),
                       (test_broches_drivers, (modele,)), (test_robustesse, (modele,)), (test_persist, (modele,)), (test_coherence, (modele,)),
                       (test_ds18x20, (modele,))):
        print(f"-- {test.__name__}")
        test(*args)
    print()
    if ECHECS:
        print(f"{len(ECHECS)} ECHEC(S) :")
        for e in ECHECS:
            print("  -", e)
        return 1
    print("VERT")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
