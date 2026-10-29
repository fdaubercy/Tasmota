"""Banc de assistant_persist_modification, groupe « charge » (A4) : recenser les cartes, relire leurs reponses.

Code de sortie 0 = vert. Depot d'essai dans un dossier temporaire, jamais le vrai depot. Aucun mot de passe imprime.
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" -u outils_docs/scripts_python/outils_pc/test_assistant_persist_modification.py
"""

import json
import os
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

import assistant_persist_creation as apc
import assistant_persist_modification as apmod
import fichiers_berry_etat as fbe
from test_assistant_persist_creation import ENV, MAITRE, SANS_BUILD, depot, reponses, secrets_reels

ECHECS = []
TEMOIN = "TEMOIN-SECRET-4242"


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def leve(exc, fonction, *args):
    try:
        fonction(*args)
    except exc as e:
        return str(e)
    return None


def test_charge(t):
    racine = depot(t)
    os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(t) / "outils")
    # cartes_du_parc
    cartes = apmod.cartes(racine)
    envs = [c["env"] for c in cartes]
    attendu = [e["nom"] for e in fbe.envs_proposes(racine) if e["famille"] == "cartes"
               and (racine / fbe.dossier_carte(e["nom"]) / "_persist.json").is_file()]
    verifie(envs, attendu, "cartes_du_parc : les cartes du depot d'essai")
    verifie(MAITRE in envs and len(envs) > 1, True, "cartes_du_parc : le maitre y est")
    verifie([e for e in envs if fbe.est_base(e)], [], "cartes_du_parc : aucune base")
    verifie(set(cartes[0]), {"env", "dossier", "puce"}, "cartes_du_parc : champs")
    verifie(next(c["dossier"] for c in cartes if c["env"] == MAITRE), fbe.dossier_carte(MAITRE), "cartes_du_parc : dossier")
    # charge_carte_creee
    r = reponses()
    apc.cree(racine, r, apc.prepare(racine, r)["empreinte"], SANS_BUILD)
    c = apmod.charge_env(racine, ENV)
    rep = c["reponses"]
    for champ in ("puce", "lieu", "nom", "role", "maitre", "id", "ip", "metiers"):
        verifie(rep[champ], asdict(r)[champ], f"charge_carte_creee : {champ}")
    verifie(sorted(rep["blocs"]), sorted(b for b in r.blocs if b != "rangeExtender"), "charge_carte_creee : blocs (rangeExtender : maitre seulement)")
    verifie(rep["base"] != "" and "define" in rep and rep["define"].startswith("FIRMWARE_"), True,
            "charge_carte_creee : base et define relus")
    verifie((c["env"], c["reglages_propres"], c["avertissements"]), (ENV, 0, []), "charge_carte_creee : aucun reglage propre")
    # carte du parc, avec une cle propre : comptee
    persist = racine / fbe.dossier_carte(MAITRE) / "_persist.json"
    j = json.loads(persist.read_text(encoding="utf-8"))
    j["cle_propre_a_la_carte"] = 1
    persist.write_text(json.dumps(j, indent="\t"), encoding="utf-8")
    verifie(apmod.charge_env(racine, MAITRE)["reglages_propres"] >= 1, True, "reglages_propres : cle propre comptee")
    # charge_inconnu
    verifie(leve(LookupError, apmod.charge_env, racine, "tasmota32s3-nulle-part") is not None, True, "charge_inconnu : LookupError")
    base = next(e["nom"] for e in fbe.envs_proposes(racine) if e["famille"] == "bases")
    verifie(leve(LookupError, apmod.charge_env, racine, base) is not None, True, "charge_inconnu : une base -> LookupError")
    # charge_persist_casse
    persist.write_text('{"serveur": {"wifi": "' + TEMOIN + '"', encoding="utf-8")
    msg = leve(ValueError, apmod.charge_env, racine, MAITRE)
    verifie((msg is not None, TEMOIN in (msg or "")), (True, False), "charge_persist_casse : ValueError sans valeur")
    persist.write_text(json.dumps({"serveur": {"wifi": TEMOIN}}), encoding="utf-8")
    msg = leve(ValueError, apmod.charge_env, racine, MAITRE)
    verifie((msg is not None, TEMOIN in (msg or "")), (True, False), "charge_persist_incomplet : ValueError sans valeur")
    # aucun_secret
    racine2 = depot(Path(t) / "b")
    sortie = json.dumps(apmod.charge_env(racine2, MAITRE), ensure_ascii=False) + json.dumps(c, ensure_ascii=False)
    verifie([s for s in secrets_reels() if s in sortie], [], "aucun_secret : charge_env du maitre")


def principal():
    with tempfile.TemporaryDirectory() as t:
        test_charge(t)
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
