"""Banc de assistant_persist_modele (JSON modele du persist, couverture du parc).

Code de sortie 0 = vert. Lecture seule des vrais persists du depot (data/*/*/_persist.json hors *sauvegarde*) et
du vrai modele outils_docs/schemas/modele_persist.json ; les cas d'erreur (modele casse, persist illisible) sont
montes dans un dossier temporaire, jamais dans le depot. Aucun mot de passe n'est affiche : les secrets du parc
ne sont compares qu'au texte du modele, et seul le CHEMIN fautif est imprime.
A lancer depuis la racine : "$USERPROFILE/.platformio/penv/Scripts/python.exe" -u
outils_docs/scripts_python/outils_pc/test_assistant_persist_modele.py
"""

import copy
import json
import os
import sys
import tempfile
from pathlib import Path

import assistant_persist_modele as apm

ECHECS = []
RACINE = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))
CHEMINS_SECRETS = ("serveur.wifi.reseau1.mdpWifi", "serveur.wifi.reseau2.mdpWifi", "serveur.mqtt.mdp",
                   "serveur.rangeExtender.AP.mdp", "serveur.serveurFTP.mdp")


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def _valeur(donnees, chemin):
    for cle in chemin.split("."):
        if not isinstance(donnees, dict) or cle not in donnees:
            return None
        donnees = donnees[cle]
    return donnees


# ---- Le vrai modele face au vrai parc (lecture seule) ----------------------------------------------------
def test_couverture_parc(modele):
    e = apm.ecarts(RACINE, modele)
    verifie(e["nouvelles"], {}, "couverture_parc : tout chemin du parc est dans le modele")
    verifie(e["illisibles"], [], "couverture_parc : les 8 persists du depot sont lisibles")
    verifie(len([p for p in apm.persists_du_depot(RACINE) if p[1] is not None]), 8, "couverture_parc : 8 persists lus")


def test_aucun_secret(modele):
    """Les valeurs REELLES des 5 chemins secrets (lues dans le parc) n'apparaissent nulle part dans le modele.
    Seul le chemin est imprime en cas d'echec, jamais la valeur."""
    texte = (RACINE / apm.FICHIER_MODELE).read_text(encoding="utf-8")
    fuites, nb = [], 0
    for rel, donnees, _ in apm.persists_du_depot(RACINE):
        for chemin in CHEMINS_SECRETS:
            v = _valeur(donnees, chemin) if donnees else None
            if isinstance(v, str) and v:
                nb += 1
                if v in texte or json.dumps(v, ensure_ascii=False)[1:-1] in texte:
                    fuites.append(f"{rel}:{chemin}")
    verifie(nb >= 8, True, "aucun_secret : des valeurs reelles ont bien ete lues dans le parc (temoin du test)")
    verifie(sorted(set(fuites)), [], "aucun_secret : aucune valeur reelle dans le texte du modele")


def test_secrets_marques(modele):
    for chemin in CHEMINS_SECRETS:
        v = _valeur(modele["socle"], chemin)
        roles = [r.get(chemin) for r in modele["roles"].values() if chemin in r]
        valeurs = [x for x in [v] + roles if x is not None]
        verifie(bool(valeurs) and all(isinstance(x, str) and x.startswith("@secret:") for x in valeurs), True,
                f"secrets_marques : {chemin} vaut @secret:* dans le socle ou les roles")
    for puce, p in modele["puces"].items():
        texte_h = "\n".join(p["h"])
        verifie([m for m in ("{{@wifi1}}", "{{@wifi2}}", "{{@ap}}") if m not in texte_h], [],
                f"secrets_marques : gabarit .h {puce} : mots de passe en marqueurs")


def test_ordre_racine(modele):
    verifie(list(modele["socle"]), ["diverses", "serveur", "template", "modules", "drivers"], "ordre_racine")
    verifie(sorted(modele), sorted(["version", "socle", "roles", "puces", "blocs", "socle_autoexec", "metier",
                                    "cenv", "a_completer"]), "ordre_racine : cles de premier niveau du modele")
    verifie(modele["version"], 1, "ordre_racine : version 1")


def test_chemins_reduits(modele):
    ch = apm.chemins_modele(modele)
    verifie(("drivers", "ModBus", "environnement", "TasmotaSlaveModBus", "TasmotaSlaveModBus#", "id") in ch, True,
            "chemins_reduits : TasmotaSlaveModBusN -> TasmotaSlaveModBus#")
    verifie(any(c[:2] == ("modules", "*") for c in ch), True, "chemins_reduits : modules.* present")
    verifie(("modules", "activation") in ch, True, "chemins_reduits : modules.activation garde tel quel")


def test_rien_a_completer(modele):
    verifie(modele["a_completer"], [], "rien_a_completer")


def test_puces(modele):
    attendu = {"ESP32": (36, False, "tasmota32"), "ESP32S3": (38, True, "tasmota32s3"),
               "ESP32P4": (55, True, "tasmota32p4")}
    verifie({k: (p["gpio"], p["historique"], p["prefixe_env"]) for k, p in modele["puces"].items()}, attendu,
            "puces : gpio, historique, prefixe_env")
    verifie(all(any("{{define}}" in l for l in p["h"]) for p in modele["puces"].values()), True,
            "puces : chaque gabarit .h porte {{define}}")


def test_temoin_couverture(modele):
    """Temoin (regle 7) : sans drivers.voletRoulants, la couverture DOIT echouer et nommer les 7 cartes qui l'ont."""
    m = copy.deepcopy(modele)
    del m["socle"]["drivers"]["voletRoulants"]
    for b in m["blocs"]:
        for cote in ("actif", "inactif"):
            for c in [c for c in b[cote] if c.startswith("drivers.voletRoulants")]:
                del b[cote][c]
    nouv = apm.ecarts(RACINE, m)["nouvelles"]
    vr = {c: v for c, v in nouv.items() if c.startswith("drivers.voletRoulants")}
    verifie(bool(vr) and len(vr) == len(nouv), True, "temoin_couverture : seuls les chemins des volets manquent")
    verifie(sorted({len(v) for v in vr.values()}) == [7] if vr else False, True,
            "temoin_couverture : chaque chemin manquant nomme les 7 cartes")


def test_temoin_cle_metier_nouvelle(modele):
    """Temoin (Ruling 1 precise) : le VRAI persist de la cuve, recopie dans un depot d'essai avec une cle
    modules.cuve.seuilX de plus, doit faire sortir cette cle (et elle seule) dans « nouvelles »."""
    with tempfile.TemporaryDirectory() as t:
        cuve = json.loads((RACINE / "data/garage/tasmota32s3-capteurs-cuve-modbus/_persist.json").read_text(encoding="utf-8"))
        _ecrit(Path(t) / "data/garage/tasmota32s3-capteurs-cuve-modbus/_persist.json", json.dumps(cuve, ensure_ascii=False))
        verifie(apm.ecarts(t, modele)["nouvelles"], {}, "temoin_cle_metier : la cuve telle quelle est couverte")
        cuve["modules"]["cuve"]["seuilX"] = 12
        _ecrit(Path(t) / "data/garage/tasmota32s3-capteurs-cuve-modbus/_persist.json", json.dumps(cuve, ensure_ascii=False))
        verifie(apm.ecarts(t, modele)["nouvelles"], {"modules.*.seuilX": ["tasmota32s3-capteurs-cuve-modbus"]},
                "temoin_cle_metier : modules.cuve.seuilX sort dans nouvelles")


def test_defines_par_bloc(modele):
    """Ruling 6 : les defines qui dependent d'un bloc sont dans blocs[].h, plus dans les gabarits des puces."""
    import re
    blocs = {b["id"]: b for b in modele["blocs"]}
    verifie(all(isinstance(b.get("h"), list) for b in modele["blocs"]), True, "defines_par_bloc : chaque bloc a un champ h")
    verifie(any(re.match(r"\s*#define\s+USE_MODBUS\b", l) for l in blocs["modbus"]["h"]), True,
            "defines_par_bloc : le bloc modbus porte #define USE_MODBUS")
    actif = re.compile(r"\s*#\s*define\s+USE_MODBUS\b")          # une ligne en commentaire (// #define) ne compte pas
    verifie([p for p, x in modele["puces"].items() if any(actif.match(l) for l in x["h"])], [],
            "defines_par_bloc : aucun gabarit de puce (dont S3) ne definit USE_MODBUS hors commentaire")
    attendus = {"i2c": "USE_I2C", "ads1115": "USE_ADS1115", "ds3231": "USE_RTC_CHIPS", "lorawan": "USE_LORAWAN_BRIDGE",
                "voletRoulants": "USE_SHUTTER", "ruban": "USE_WS2812", "ledRGB": "TASMOTALED_HARDWARE_SPI",
                "i2s": "USE_I2S_ALL", "sd": "USE_SDCARD"}
    verifie([i for i, d in attendus.items() if not any(re.match(r"\s*#define\s+" + d + r"\b", l) for l in blocs[i]["h"])],
            [], "defines_par_bloc : i2c, ads1115, ds3231, lorawan, volets, ruban, ledRGB, i2s, sd portent leur define")
    tous = re.compile(r"\s*#\s*(define|undef)\s+(" + "|".join(list(attendus.values()) + ["USE_MODBUS", "USE_SPI"]) + r")\b")
    verifie({p: [l.strip() for l in x["h"] if tous.match(l)] for p, x in modele["puces"].items()},
            {p: [] for p in modele["puces"]}, "defines_par_bloc : gabarits des puces sans aucun define de bloc")


# ---- Fonctions pures --------------------------------------------------------------------------------------
def test_chemins_unitaires():
    d = {"modules": {"activation": "ON",
                     "cuve": {"name": "x", "logs": {"nbLogsFiles": 15}, "dimensions": {"hauteur": 1},
                              "environnement": {"boutons": {"bouton1": {"pin": 7}}, "relais": {}}}},
         "drivers": {"leds": {"environnement": {"leds": {"led1": {"pin": 1}, "ledRGB": {"pin": 48}}}},
                     "I2C": {"environnement": {"ADS1115": {"voies": {"A0": {"x": 1}}}}},
                     "VR": {"environnement": {"VRs": {"VR1": {"relais1": 2, "boutons": {"bouton2": {"id": 1}}}}}}},
         "serveur": {"wifi": {"reseau1": {"nom": "a"}}, "vide": {}, "liste": [1, 2]}}
    attendu = {("modules", "activation"), ("modules", "*", "name"), ("modules", "*", "logs"),
               ("modules", "*", "dimensions"), ("modules", "*", "environnement", "boutons"),
               ("modules", "*", "environnement", "relais"),
               ("drivers", "leds", "environnement", "leds", "led#", "pin"),
               ("drivers", "leds", "environnement", "leds", "ledRGB", "pin"),
               ("drivers", "I2C", "environnement", "ADS1115", "voies", "A0", "x"),
               ("drivers", "VR", "environnement", "VRs", "VR#", "relais1"),
               ("drivers", "VR", "environnement", "VRs", "VR#", "boutons", "bouton#", "id"),
               ("serveur", "wifi", "reseau1", "nom"), ("serveur", "vide"), ("serveur", "liste")}
    verifie(apm.chemins(d), attendu, "chemins : reductions xxxN -> xxx# (environnement) et modules.* (1er niveau)")
    verifie(apm.chemins({"pin": 3}, ("drivers", "SD", "environnement", "pinsSDs", "pinsSD4")),
            {("drivers", "SD", "environnement", "pinsSDs", "pinsSD#", "pin")}, "chemins : le prefixe est reduit aussi")
    verifie(apm.chemins("OFF", ("serveur", "udp", "activation")), {("serveur", "udp", "activation")},
            "chemins : valeur simple sous un prefixe")


def test_chemins_modele_unitaires():
    m = {"socle": {"serveur": {"udp": {"activation": "ON"}}}, "roles": {"esclave": {"serveur.IP.IPGateway": "x"}},
         "puces": {"ESP32": {"ajouts": {"diverses.historique": None}},
                   "ESP32P4": {"ajouts": {"drivers.H": {"environnement": {"pinsHs": {"pinsH1": {"pin": 1}}}}}}},
         "blocs": [{"actif": {"drivers.T.activation": "ON"}, "inactif": {"drivers.T.activation": "OFF"}}],
         "metier": {"gabarit": {"name": "{{nom_lisible}}", "environnement": {"boutons": {}}}}}
    verifie(apm.chemins_modele(m), {("serveur", "udp", "activation"), ("serveur", "IP", "IPGateway"),
                                    ("drivers", "H", "environnement", "pinsHs", "pinsH#", "pin"),
                                    ("drivers", "T", "activation"), ("modules", "*", "name"),
                                    ("modules", "*", "environnement", "boutons")},
            "chemins_modele : socle + roles + ajouts (null ignore) + blocs + metier")


def _ecrit(chemin, texte):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(texte, encoding="utf-8", newline="\n")


def test_modele_illisible():
    with tempfile.TemporaryDirectory() as t:
        racine = Path(t)
        try:
            apm.charge_modele(racine)
            verifie("pas d'erreur", "ValueError", "modele absent : ValueError")
        except ValueError as exc:
            verifie(str(exc).startswith("modele_persist.json"), True, "modele absent : ValueError nommant le fichier")
        _ecrit(racine / apm.FICHIER_MODELE, '{\n\t"version": 1,\n\t"socle": {\n\t\t"a": ,\n\t}\n}\n')
        try:
            apm.charge_modele(racine)
            verifie("pas d'erreur", "ValueError", "modele casse : ValueError")
        except ValueError as exc:
            verifie(str(exc).startswith("modele_persist.json ligne 4 :"), True, "modele casse : erreur et sa ligne")
        _ecrit(racine / apm.FICHIER_MODELE, '{"version": 1, "socle": {}}')
        try:
            apm.charge_modele(racine)
            verifie("pas d'erreur", "ValueError", "modele incomplet : ValueError")
        except ValueError as exc:
            verifie("roles" in str(exc), True, "modele incomplet : cle manquante nommee")


def test_parc_essai():
    """Persists hors sauvegarde, illisible signale sans planter, cle propre a UNE carte ignoree (decision 1)."""
    with tempfile.TemporaryDirectory() as t:
        racine = Path(t)
        # dimensions : listee dans metier.cles_propres -> ignoree ; propre : d'une seule carte mais NON listee ->
        # nouvelle quand meme ; commune : sur 2 cartes -> nouvelle
        a = {"serveur": {"udp": {"activation": "ON"}}, "modules": {"activation": "ON", "cuve": {"name": "c",
             "dimensions": {"h": 1}, "commune": 0}}}
        b = {"serveur": {"udp": {"activation": "ON"}, "neuve": 1}, "modules": {"activation": "ON",
             "rideau": {"name": "r", "commune": 1, "propre": 1}, "garage": {"name": "g", "commune": 2, "propre": 2}}}
        _ecrit(racine / "data/garage/carte-a/_persist.json", json.dumps(a))
        _ecrit(racine / "data/garage/carte-b/_persist.json", json.dumps(b))
        _ecrit(racine / "data/garage/carte-c-sauvegarde/_persist.json", json.dumps({"ignoree": 1}))
        _ecrit(racine / "data/cave/carte-d/_persist.json", '{"serveur": ')
        lus = apm.persists_du_depot(racine)
        verifie([r for r, _, _ in lus], ["data/cave/carte-d/_persist.json", "data/garage/carte-a/_persist.json",
                                         "data/garage/carte-b/_persist.json"], "persists_du_depot : hors *sauvegarde*, tries")
        verifie([(d is None, bool(e)) for _, d, e in lus], [(True, True), (False, False), (False, False)],
                "persists_du_depot : illisible -> (None, erreur)")
        modele = {"socle": {"serveur": {"udp": {"activation": "OFF"}}, "modules": {"activation": "ON"}},
                  "roles": {}, "puces": {}, "blocs": [],
                  "metier": {"gabarit": {"name": "n"}, "cles_propres": ["dimensions"]}}
        e = apm.ecarts(racine, modele)
        verifie(e["illisibles"], ["data/cave/carte-d/_persist.json"], "ecarts : persist illisible signale")
        verifie(e["nouvelles"], {"serveur.neuve": ["carte-b"], "modules.*.commune": ["carte-a", "carte-b"],
                                 "modules.*.propre": ["carte-b"]},
                "ecarts : nouvelles (seule dimensions, listee dans cles_propres, est ignoree)")
        del modele["metier"]["cles_propres"]
        verifie("modules.*.dimensions" in apm.ecarts(racine, modele)["nouvelles"], True,
                "ecarts : sans cles_propres, dimensions est une cle nouvelle")
        verifie(e["divergentes"], {"serveur.udp.activation": {"modele": "OFF", "parc": "ON"}},
                "ecarts : defaut divergent de la valeur commune du parc")
        modele["socle"]["serveur"]["fantome"] = 1
        verifie(apm.ecarts(racine, modele)["disparues"], ["serveur.fantome"], "ecarts : cle du modele absente du parc")


def principal():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    test_chemins_unitaires()
    test_chemins_modele_unitaires()
    test_modele_illisible()
    test_parc_essai()
    try:
        modele = apm.charge_modele(RACINE)
    except Exception as exc:
        verifie(repr(exc), "modele lisible", "charge_modele(depot)")
        modele = None
    if modele is not None:
        for test in (test_couverture_parc, test_aucun_secret, test_secrets_marques, test_ordre_racine,
                     test_chemins_reduits, test_rien_a_completer, test_puces, test_temoin_couverture,
                     test_temoin_cle_metier_nouvelle, test_defines_par_bloc):
            try:
                test(modele)
            except Exception as exc:
                verifie(repr(exc), "pas d'exception", test.__name__)
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
