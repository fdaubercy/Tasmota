"""Banc de atelier_visuels_description : cas partages (cas_visuel.json) et sources() sur une COPIE du persist de la cuve.

Lancer : "$USERPROFILE/.platformio/penv/Scripts/python.exe" test_atelier_visuels_description.py   (code 0 = vert)
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atelier_visuels_description as av

RACINE = Path(__file__).resolve().parents[3]
CUVE = "tasmota32s3-garage-capteurs-cuve-modbus"
DOSSIER = "data/garage/tasmota32s3-capteurs-cuve-modbus"
ECHECS = []


def verifie(cond, msg):
    if not cond:
        ECHECS.append(msg)
        print("ROUGE :", msg)


def cas_partages():
    cas = json.loads((RACINE / "outils_docs/schemas/cas_visuel.json").read_text(encoding="utf-8"))
    for c in cas:
        err = av.valide(c["desc"], c["octets"], c["puce"])
        verifie(bool(err) == bool(c["erreurs"]), f"{c['nom']} : erreurs {err}")
        for attendu in c["erreurs"]:
            verifie(any(attendu in e for e in err), f"{c['nom']} : {attendu!r} absent de {err}")
        if not c["erreurs"]:
            verifie(err == [], f"{c['nom']} : {err}")
    ex = json.loads((RACINE / "outils_docs/schemas/exemple_visuel.json").read_text(encoding="utf-8"))
    verifie(av.valide(ex, None, "ESP32") == [], "exemple_visuel.json invalide")
    verifie(len(cas) >= 22, "moins de 22 cas")


def seuils():
    verifie(av.SEUIL_AVERT == 40 * 1024 and av.SEUILS_REFUS == {"esp32": 61440, "autre": 204800}, "constantes")
    verifie(av.avertissement(41 * 1024) and not av.avertissement(40 * 1024) and not av.avertissement(None), "avertissement")


def sources_cuve():
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / DOSSIER
        dest.mkdir(parents=True)
        d = json.loads((RACINE / DOSSIER / "_persist.json").read_text(encoding="utf-8-sig"))
        d["modules"]["cuve"]["environnement"]["relais"]["relai1"]["motdepasse"] = "SECRET-A-NE-PAS-VOIR"
        d["modules"]["cuve"]["environnement"]["relais"]["relai1"]["nom"] = "Ruban"
        d["drivers"]["ModBus"]["periodeReleve"] = 10
        d["drivers"]["ModBus"]["environnement"]["TasmotaSlaveModBus"]["TasmotaSlaveModBus1"] = \
            {"activation": "ON", "name": "Esclave test", "id": 7, "token": "XYZ"}
        (dest / "_persist.json").write_text(json.dumps(d), encoding="utf-8")
        (dest / "discovery.json").write_text(json.dumps(
            {"AABBCCDDEEFF": {"esclave1": {"nom": "Rideau"}, "lwt": "Online"}, "112233445566": {"role": "x"}}), encoding="utf-8")
        s = av.sources(tmp, CUVE)
        verifie({"n": 1, "nom": "Ruban"} in s["relais"], f"relais {s['relais']}")
        verifie({"id": 7, "nom": "Esclave test"} in s["esclaves"], f"esclaves {s['esclaves']}")
        verifie(s["esclaves_reseau"] == [{"mac": "AABBCCDDEEFF", "nom": "Rideau"}] and "udp" not in s and "rgx" not in s, f"esclaves_reseau {s}")
        verifie(s["periodeReleve"] == 10 and s["telePeriod"] == 300, f"periodes {s['periodeReleve']} {s['telePeriod']}")
        verifie({"chemin": ["Button1"], "nom": "Bouton ruban"} in s["mesures"], f"mesures {s['mesures']}")
        verifie("SECRET-A-NE-PAS-VOIR" not in json.dumps(s) and "XYZ" not in json.dumps(s), "secret dans les sources")
        verifie(av.defauts_seuils(s) == {"modbus_serie": 30, "modbus_esclave": 30}, f"defauts {av.defauts_seuils(s)}")
        verifie(av.defauts_seuils({"periodeReleve": None, "telePeriod": None}) == {"modbus_serie": 30, "modbus_esclave": 30},
                "defauts sans periode")
        verifie(av.sources(tmp, "tasmota32-inconnu-x")["relais"] == [], "env inconnu")
        verifie(av.sources(tmp, "base")["relais"] == [], "env sans tiret")


if __name__ == "__main__":
    cas_partages()
    seuils()
    sources_cuve()
    print("VERT" if not ECHECS else f"{len(ECHECS)} echec(s)")
    sys.exit(1 if ECHECS else 0)
