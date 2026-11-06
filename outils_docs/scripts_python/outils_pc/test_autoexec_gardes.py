#!/usr/bin/env python3
"""Banc de autoexec_gardes.py : gardes de compilation d'une carte (plan autoexec-mqtt-tapp, A4).

Defauts injectes (preprocesseur absent, exception), cache (un seul calcul en 100 lectures, empreinte changee = nouveau
calcul, None compris), temps d'une analyse avec cache (< 50 ms, sans sous-processus), puis le vrai depot en LECTURE avec
le vrai preprocesseur (aucun pio run) : ZbSend sur le bureau -> alerte, le vrai autoexec.bat -> aucune `absente`. Sans
preprocesseur sur le poste, ces deux derniers cas sont KO. Aucune valeur du fichier n'est affichee (secrets).
Temoins : mutants du module (AUTOEXEC_MUTANT=<dossier>) doivent rendre le banc ROUGE. Code 0 = vert.

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_autoexec_gardes.py
"""
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

if os.environ.get("AUTOEXEC_MUTANT"):
    sys.path.insert(0, os.environ["AUTOEXEC_MUTANT"])

import autoexec_analyse as aa
import autoexec_commandes
import autoexec_gardes as ag

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[2]
ENV = "tasmota32-bureau-interrupteur-energie"
CARTE = RACINE / "data" / "bureau" / "tasmota32-interrupteur-energie"
ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def faux_depot(tmp, contenu="a"):
    (Path(tmp) / "tasmota").mkdir(exist_ok=True)
    (Path(tmp) / "platformio_tasmota_cenv.ini").write_text("x", encoding="utf-8")
    (Path(tmp) / "tasmota" / "user_config_override.h").write_text(contenu, encoding="utf-8")


def banc():
    appels = []
    vrai_calcule = ag._calcule

    def calcule(racine, env):
        appels.append(env)
        if env == "boom":
            raise RuntimeError("compilateur absent")
        return lambda nom: [[("defined(X)", False)]]

    with tempfile.TemporaryDirectory() as tmp:
        ag._calcule = calcule
        try:
            faux_depot(tmp)
            ag._CACHE.clear()
            verifie([ag.etat(tmp, "e")("N") for _ in range(100)] == [[[("defined(X)", False)]]] * 100 and len(appels), 1,
                    "cache : un seul calcul en 100 lectures")
            faux_depot(tmp, "b")
            ag.etat(tmp, "e")
            verifie(len(appels), 2, "cache : empreinte changee (user_config_override.h) -> nouveau calcul")
            (Path(tmp) / "platformio_tasmota_cenv.ini").write_text("y", encoding="utf-8")
            ag.etat(tmp, "e")
            verifie(len(appels), 3, "cache : empreinte changee (cenv) -> nouveau calcul")
            ag.etat(tmp, "autre")
            verifie(len(appels), 4, "cache : un autre env -> son propre calcul")
            appels.clear()
            verifie([ag.etat(tmp, "boom") for _ in range(20)] == [None] * 20, True, "defaut : exception -> None, jamais d'exception")
            verifie(len(appels), 1, "defaut : le None est aussi mis en cache (pas de sous-processus a chaque frappe)")
        finally:
            ag._calcule = vrai_calcule
    with tempfile.TemporaryDirectory() as tmp:
        faux_depot(tmp)
        ag._CACHE.clear()
        verifie(ag.etat(tmp, "e"), None, "defaut : depot d'essai sans platformio.ini -> None")
    verifie(ag.etat(tmp, "e"), None, "defaut : depot disparu -> None")

    # compilateur absent : le vrai module, les vrais fichiers, un chemin de paquets vide
    anciens = {k: os.environ.get(k) for k in ("USERPROFILE", "HOME")}
    os.environ["USERPROFILE"] = os.environ["HOME"] = str(Path(tempfile.gettempdir()) / "profil_vide_autoexec")   # le fils ne trouve pas ~/.platformio
    ag._CACHE.clear()
    try:
        verifie(ag.etat(RACINE, ENV), None, "defaut : compilateur absent (fils sans ~/.platformio) -> None")
    finally:
        for k, v in anciens.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    # le vrai depot, en lecture
    ag._CACHE.clear()
    g = ag.etat(RACINE, ENV)
    verifie(g is not None, True, "reel : preprocesseur disponible (sinon les 3 cas suivants sont KO)")
    if g is None:
        return
    commandes = autoexec_commandes.charge(RACINE)
    persist = {}
    ana = lambda t: aa.analyse(t, persist, commandes, texte_config="", gardes_env=g)
    verifie([(a["type"], a["niveau"]) for a in ana("ZbSend 1") if a["type"] == "absente"], [("absente", "orange")],
            "reel : ZbSend sur le bureau -> alerte absente")
    verifie("USE_ZIGBEE non defini" in ana("ZbSend 1")[0]["message"], True, "reel : la raison nomme USE_ZIGBEE")
    texte = (CARTE / "autoexec.bat").read_text(encoding="utf-8")
    verifie([a["ligne"] for a in ana(texte) if a["type"] == "absente"], [], "reel : le vrai autoexec.bat du bureau -> aucune absente")
    verifie(ana("Timer1 {}\nRule1 ON System#Boot DO Power1 1 ENDON\nPower 1\nBacklog Delay 1\nWebButton1 X\nTelePeriod 300"
                "\nEnergyRes 3\nI2CScan"), [], "reel : commandes courantes -> aucune alerte")
    for env in (ENV, "tasmota32s3-garage-capteurs-cuve-modbus", "tasmota32p4-garage-serveur-modbus"):
        ge = ag.etat(RACINE, env)
        fausses = [c for n in commandes["gardes"] for ch in (ge(n),) if ch and all(any(v is False for _, v in p) for p in ch)
                   for p in ch for c, v in p if v is False and "USE_" not in c
                   and re.search(r"CONFIG_IDF_TARGET|SOC_|__has_include|ESP_IDF_VERSION", c)]
        verifie(fausses, [], f"reel : {env[-22:]} : aucune alerte portee par la seule condition CONFIG_IDF_TARGET, SOC_, __has_include, ESP_IDF_VERSION")
    debut = time.perf_counter()
    for _ in range(20):
        ag.etat(RACINE, ENV)
        ana(texte)
    ms = (time.perf_counter() - debut) / 20 * 1000
    verifie(ms < 50, True, f"temps : analyse du vrai autoexec avec cache, {ms:.1f} ms (< 50)")
    sous = []
    vrai_run = subprocess.run
    subprocess.run = lambda *a, **k: sous.append(a) or vrai_run(*a, **k)
    try:
        ag.etat(RACINE, ENV)
        ana(texte)
    finally:
        subprocess.run = vrai_run
    verifie(len(sous), 0, "temps : aucun sous-processus une fois le cache pose")


MUTANTS = [
    ("sans cache", "if cle not in _CACHE:", "if True:"),
    ("empreinte sans le .h", 'FICHIERS = ("platformio_tasmota_cenv.ini", "tasmota/user_config_override.h")', 'FICHIERS = ("platformio_tasmota_cenv.ini",)'),
    ("exception non rattrapee", "except Exception as e:", "except KeyboardInterrupt as e:"),
    ("incertain compte faux", "evalue(c, ctx, {})", "bool(evalue(c, ctx, {}))"),
]


def temoins():
    source = (ICI / "autoexec_gardes.py").read_text(encoding="utf-8")
    for nom, ancien, nouveau in MUTANTS:
        verifie(ancien in source, True, f"mutant {nom} : motif present")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "autoexec_gardes.py").write_text(source.replace(ancien, nouveau, 1), encoding="utf-8")
            p = subprocess.run([sys.executable, str(Path(__file__).resolve())], capture_output=True, text=True, encoding="utf-8",
                               env=dict(os.environ, AUTOEXEC_MUTANT=tmp, PYTHONIOENCODING="utf-8", PYTHONPATH=str(ICI)))
        verifie(p.returncode != 0, True, f"temoin rouge : mutant {nom}")


if __name__ == "__main__":
    banc()
    if not os.environ.get("AUTOEXEC_MUTANT"):
        temoins()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1 if ECHECS else 0)
