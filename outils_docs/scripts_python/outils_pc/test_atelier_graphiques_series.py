#!/usr/bin/env python3
"""Banc de atelier_graphiques_series.py (plan atelier-graphiques, A4) : faux depot temporaire, `get` simule (aucun
reseau). Verifie aussi que seules les 3 routes de lecture sont demandees.

    <Python de PlatformIO> outils_docs/scripts_python/outils_pc/test_atelier_graphiques_series.py

Code de sortie 0 = vert, 1 = rouge.
"""
import json
import sys
import tempfile
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import atelier_graphiques_series as ag

CUVE, ESCL = "tasmota32s3-garage-cuve", "tasmota32s3-garage-esclave"
CENV = "".join(f"[env:{e}]\nextends = env:tasmota32_base\nextra_scripts = pre_utilitaires_platformio.py\n"
               f"build_flags = -D{f}\n\n" for e, f in ((CUVE, "FIRMWARE_CUVE"), (ESCL, "FIRMWARE_ESCL")))
CENV += "[env:tasmota32_base]\nboard = esp32\n"
H = ('#if defined(FIRMWARE_CUVE)\n#define WIFI_IP_ADDRESS "192.168.0.50"\n#elif defined(FIRMWARE_ESCL)\n'
     '#define WIFI_IP_ADDRESS "0.0.0.0"\n#endif\n')
PERSIST = {"diverses": {"historique": {"activation": "ON", "ajouts": ["DS18B20.Temperature"]}}}
ESCLAVE = {"serveur": {"rangeExtender": {"activation": "ON", "id": 2, "ipMaitre": "192.168.0.9"}}}
GRAPH = {"affichage": {"sensorsCuve.volume": {"libelle": "Volume", "unite": "L"}}}
SNS = {"StatusSNS": {"Time": "x", "DS18B20": {"Temperature": 12.5}, "sensorsCuve": {"volume": 800},
                     "POWER1": "ON"}}
URLS_OK = {"/histo?n=mesures&p=liste", "/cm?cmnd=Status%2010", "/pages?f=sources"}
echecs = []


def verifie(nom, cond):
    print(("ok   " if cond else "ECHEC"), nom)
    if not cond:
        echecs.append(nom)


def faux_get(appels, mort=False, sans_pages=False):
    def get(ip, chemin, delai):
        appels.append((ip, chemin))
        if mort:
            raise OSError("pas de reponse")
        if chemin.startswith("/histo"):
            return json.dumps({"nom": "mesures", "series": ["DS18B20.Temperature"], "mois": []}).encode()
        if chemin.startswith("/cm"):
            return json.dumps(SNS).encode()
        if sans_pages:
            raise OSError("HTTP 404")
        return b'{"historique": true, "flash": []}'
    return get


with tempfile.TemporaryDirectory() as t:
    r = Path(t)
    (r / "platformio_tasmota_cenv.ini").write_text(CENV, encoding="utf-8")
    (r / "tasmota").mkdir()
    (r / "tasmota" / "user_config_override.h").write_text(H, encoding="utf-8")
    for dossier, p in (("tasmota32s3-cuve", PERSIST), ("tasmota32s3-esclave", ESCLAVE)):
        d = r / "data" / "garage" / dossier
        d.mkdir(parents=True)
        (d / "_persist.json").write_text(json.dumps(p), encoding="utf-8")
    (r / "data" / "garage" / "tasmota32s3-cuve" / "graphiques.json").write_text(json.dumps(GRAPH), encoding="utf-8")

    a = []
    s = ag.series(r, CUVE, get=faux_get(a))
    chemins = {x["chemin"]: x for x in s["series"]}
    verifie("carte en ligne : source carte", s["source"] == "carte" and s["historique"] is True)
    verifie("series : historique + feuilles du SENSOR sans Time",
            set(chemins) == {"DS18B20.Temperature", "sensorsCuve.volume", "POWER1"})
    verifie("historique par serie", chemins["DS18B20.Temperature"]["historique"] and not chemins["sensorsCuve.volume"]["historique"])
    verifie("libelle et unite de graphiques.json", chemins["sensorsCuve.volume"]["libelle"] == "Volume"
            and chemins["sensorsCuve.volume"]["unite"] == "L")
    verifie("unite devinee", chemins["DS18B20.Temperature"]["unite"] == "°C")
    verifie("etat pour POWER", chemins["POWER1"]["etat"] and not chemins["sensorsCuve.volume"]["etat"])
    verifie("3 routes de lecture seulement", {c for _, c in a} == URLS_OK and all(i == "192.168.0.50" for i, _ in a))

    s = ag.series(r, CUVE, get=faux_get([], sans_pages=True))
    verifie("/pages absent : pas une erreur", s["source"] == "carte" and s["historique"] is True)

    s = ag.series(r, CUVE, get=faux_get([], mort=True))
    verifie("injoignable : repli depot", s["source"] == "depot" and "carte injoignable" in s["motif"])
    verifie("repli : series du persist et de graphiques.json",
            {x["chemin"] for x in s["series"]} == {"DS18B20.Temperature", "sensorsCuve.volume"})
    v1 = ag.valeurs(r, CUVE, ["DS18B20.Temperature"], "jour", get=faux_get([], mort=True))
    v2 = ag.valeurs(r, CUVE, ["DS18B20.Temperature"], "jour", get=faux_get([], mort=True))
    verifie("valeurs simulees deterministes", v1["source"] == "depot" and v1 == v2
            and isinstance(v1["valeurs"]["DS18B20.Temperature"], float))
    v = ag.valeurs(r, CUVE, ["sensorsCuve.volume", "absente"], "jour", get=faux_get([]))
    verifie("valeurs reelles", v == {"source": "carte", "valeurs": {"sensorsCuve.volume": 800, "absente": None}})

    a = []
    ag.series(r, ESCL, get=faux_get(a))
    verifie("esclave : adresse maitre:port", a and all(i == "192.168.0.9:8081" for i, _ in a))
    verifie("esclave : aucune ecriture", {c for _, c in a} <= URLS_OK)

sys.exit(1 if echecs else 0)
