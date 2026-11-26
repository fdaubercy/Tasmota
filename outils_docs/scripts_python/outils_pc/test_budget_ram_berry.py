"""Banc de budget_ram_berry (budget de RAM Berry par puce, plan binomes-berry A21). Code de sortie 0 = vert.

Lit les vrais modele_persist.json, cenv et persists du depot (jamais ecrits, aucune valeur affichee : seuls des Ko et
des noms de fichiers sortent). Les cas « au-dessus » passent par un budget abaisse EN MEMOIRE (copie du modele).
Temoins : cout neutralise, table `budget` retiree, nom du fichier ignore par la mesure : le controle doit echouer.
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()

import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import assistant_persist_creation as apc
import assistant_persist_modele as apm
import assistant_persist_modification as apm2
import assistant_persist_web as apw
import budget_ram_berry as bud
import test_assistant_persist_creation as tapc
import test_fichiers_berry_web as tfw

ECHECS = []
RACINE = tapc.RACINE
ESP32_EN_SERVICE = ["tasmota32-jardin-projecteur-led", "tasmota32-jardin-projecteur-barbecue",
                    "tasmota32-bureau-interrupteur-energie", "tasmota32-garage-portail-jardin-modbus",
                    "tasmota32-cave-serveur-rly"]
PORTAIL, LED = "tasmota32-garage-portail-jardin-modbus", "tasmota32-jardin-projecteur-led"
CAVE, CAVE_PERSIST = "tasmota32-cave-serveur-rly", "data/cave/tasmota32-serveur-rly/_persist.json"


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def depot_synthetique(t):
    """data/fs/controleX.be (bloc de taille : controleX 30 Ko de .bec, xFonctions 3 Ko), data/fs/libre.be sans bloc (4096 o)."""
    racine = Path(t)
    (racine / "data" / "fs").mkdir(parents=True)
    bloc = bud._mesure().bloc_driver([("controleX.be", 40960, 30720, None, 0), ("xFonctions.be", 5120, 3072, 2048, 0)])
    (racine / "data/fs/controleX.be").write_text(bloc + "\nvar x = 1\n", encoding="utf-8")
    (racine / "data/fs/libre.be").write_bytes(b"#" * 4096)
    return racine


def modele_budget(ko):
    return {"puces": {"ESP32": {"budget": {"ram_berry_ko": ko, "source": "essai", "a_confirmer": False}}}}


def signale(racine, modele, fichiers, persist):
    """Le controle : un env au-dessus du budget de l'ESP32 porte un message qui cite son cout et le budget."""
    b = bud.bilan(modele, "ESP32", bud.cout(racine, fichiers, persist))
    return b["depasse"] and str(b["budget"]) in b["message"] and str(b["cout"]["ko"]) in b["message"]


def test_calcul(t):
    racine = depot_synthetique(t)
    c = bud.cout(racine, ["data/fs/controleX.be"], {})
    verifie((c["bec_ko"], c["estimes"]), (30.0, []), "cout : .bec de la ligne DU fichier, pas du binome entier")
    c = bud.cout(racine, ["data/fs/libre.be"], {"a": "x" * 1000})
    verifie((c["bec_ko"], c["estimes"]), (2.0, ["libre.be"]), "cout : .be sans bloc de taille = moitie du .be, marque estime")
    verifie(c["persist_ko"], round(bud.FACTEUR_PERSIST * len('{"a":"' + "x" * 1000 + '"}') / 1024, 1), "cout : facteur x persist compact")
    verifie(signale(racine, modele_budget(20), ["data/fs/controleX.be"], {}), True, "au-dessus du budget (30 > 20) : signale")
    verifie(signale(racine, modele_budget(20), ["data/fs/libre.be"], {}), False, "en dessous du budget (2 < 20) : pas signale")
    b = bud.bilan(modele_budget(20), "ESP32", bud.cout(racine, ["data/fs/libre.be"], {}))
    verifie((b["depasse"], b["message"], b["budget"]), (False, "", 20), "en dessous : message vide, budget rendu")
    verifie(bud.bilan(modele_budget(20), "ESP32S3", bud.cout(racine, ["data/fs/controleX.be"], {}))["depasse"], False,
            "puce sans table budget : jamais signale")
    verifie(bud.budget({"puces": {"ESP32": {"budget": {"ram_berry_ko": "20"}}}}, "ESP32"), None, "budget non numerique : ignore")


def test_temoins(t):
    racine = depot_synthetique(t)
    neutre, vrai = bud.cout, bud.cout
    bud.cout = lambda *a: dict(neutre(*a), ko=0.0)
    try:
        verifie(signale(racine, modele_budget(20), ["data/fs/controleX.be"], {}), False, "TEMOIN : cout neutralise, le controle echoue")
    finally:
        bud.cout = vrai
    verifie(signale(racine, {"puces": {"ESP32": {}}}, ["data/fs/controleX.be"], {}), False,
            "TEMOIN : table budget retiree, le controle echoue")
    lit = bud._mesure().lit_taille
    bud._mesure().lit_taille = lambda p: None                  # plus de bloc de taille : 30 Ko deviennent .be / 2
    try:
        verifie(bud.cout(racine, ["data/fs/controleX.be"], {})["bec_ko"] == 30.0, False, "TEMOIN : mesure ignoree, le .bec change")
    finally:
        bud._mesure().lit_taille = lit


def test_manifeste():
    modele = apm.charge_modele(RACINE)
    for puce in ("ESP32", "ESP32S3", "ESP32P4"):
        b = bud.budget(modele, puce)
        verifie(bool(b) and isinstance(b.get("source"), str) and len(b["source"]) > 20 and isinstance(b.get("a_confirmer"), bool),
                True, f"manifeste : {puce} porte budget {{ram_berry_ko, source, a_confirmer}}")
    psram = modele["puces"]["ESP32"]["budget"].get("avec_psram", {})
    verifie((type(psram.get("ram_berry_ko")), psram.get("a_confirmer")), (int, True), "manifeste : ESP32 avec PSRAM note, a confirmer")
    verifie("ESP8266" in modele["puces"], False, "manifeste : pas de puce ESP8266 (pas de Berry, note dans budget_ram_berry)")


def test_parc_reel():
    """Les 5 ESP32 en service tiennent (tasmota.gc() 24 a 40 Ko, stables) ; un module solidifie ne compte pas."""
    modele = apm.charge_modele(RACINE)
    for env in ESP32_EN_SERVICE:
        b = bud.pour_carte(RACINE, env)
        print(f"     {env} : {b and b['cout']['ko']} Ko (code {b and b['cout']['bec_ko']}, persist {b and b['cout']['persist_ko']})"
              f" / budget {b and b['budget']}")
        verifie((b is not None and b["budget"] == modele["puces"]["ESP32"]["budget"]["ram_berry_ko"], b and b["depasse"]),
                (True, False), f"parc reel : {env} sous le budget de l'ESP32")
    b = bud.pour_carte(RACINE, PORTAIL)
    verifie("data/fs/discoveryFonctions.be" in bud.charges(RACINE, modele, apm2.reponses_de_l_env(RACINE, LED), LED, True), False,
            "parc reel : discoveryFonctions (bloc actif, solidifie par le socle) non compte sur le projecteur LED")
    verifie(bud.pour_carte(RACINE, "tasmota32-base"), None, "base : pas de bilan")
    # page 7800 : discoveryFonctions (21 Ko de .bec) sorti de custom_berry_solidify du projecteur LED (geste de la page) :
    # compte avec les listes du cenv seules, alors que la liste generee le dit encore solidifie
    vrai = bud._listes_env
    bud._listes_env = lambda racine, env: tuple(s - {"data/fs/discoveryFonctions.be"} for s in vrai(racine, env))
    try:
        b = bud.pour_carte(RACINE, LED)
        verifie((b["depasse"], b["cout"]["bec_ko"] > 15), (True, True),
                "page 7800 : discoveryFonctions desolidifie sur le projecteur LED, compte et signale")
    finally:
        bud._listes_env = vrai
    # la cave portait le persist d'avant le palier 1 (3501e194f) a gc() 50 899 o, le plafond retenu : signalee
    ancien = json.loads(subprocess.run(["git", "-C", str(RACINE), "show", f"3501e194f:{CAVE_PERSIST}"], capture_output=True,
                                       check=True).stdout.decode("utf-8"))
    rc = apm2.reponses_de_l_env(RACINE, CAVE)
    b = bud.bilan(modele, "ESP32", bud.cout(RACINE, bud.charges(RACINE, modele, rc, CAVE), ancien))
    print(f"     cave avant allegement : {b['cout']['ko']} Ko / budget {b['budget']}")
    verifie(b["depasse"], True, "parc reel : cave avant allegement (au plafond de 50 Ko mesure) signalee")
    bas = copy.deepcopy(modele)
    bas["puces"]["ESP32"]["budget"]["ram_berry_ko"] = 1
    r = apm2.reponses_de_l_env(RACINE, PORTAIL)
    persist = {"a": "x" * 2000}                                # ~3,9 Ko : sous 26, au-dessus de 1
    verifie(bud.avertissement(RACINE, modele, r, persist, PORTAIL), "", "assistant : portail sous le vrai budget, aucun avertissement")
    verifie("au-delà du budget de 1 Ko" in bud.avertissement(RACINE, bas, r, persist, PORTAIL), True,
            "assistant : budget abaisse a 1 Ko, avertissement")


def avec_budget(ko, fonction):
    """fonction() avec la table budget de l'ESP32 remplacee en memoire (charge_modele de l'assistant)."""
    vrai = apm.charge_modele
    def charge(racine):
        m = vrai(racine)
        m["puces"]["ESP32"]["budget"]["ram_berry_ko"] = ko
        return m
    apm.charge_modele = charge
    try:
        return fonction()
    finally:
        apm.charge_modele = vrai


def test_assistant(t):
    racine = tapc.depot(t)
    r = tapc.reponses(puce="ESP32", nom="essai-budget", blocs=[])
    marque = lambda avs: [a for a in avs if a.startswith("RAM Berry")]
    verifie(marque(apw.apercu(racine, r)["avertissements"]), [], "apercu : ESP32 leger, aucun avertissement de RAM")
    verifie(len(marque(avec_budget(1, lambda: apw.apercu(racine, r))["avertissements"])), 1, "apercu : au-dessus du budget, avertissement")
    p = avec_budget(1, lambda: apc.prepare(racine, r))
    verifie((p["refus"], len(marque(p["avertissements"]))), ([], 1), "creation (prepare) : au-dessus du budget, avertissement")
    verifie(marque(apc.prepare(racine, r)["avertissements"]), [], "creation (prepare) : sous le budget, rien")
    rp = apm2.reponses_de_l_env(racine, PORTAIL)
    m = avec_budget(1, lambda: apm2.prepare_modification(racine, PORTAIL, rp))
    verifie(len(marque(m["avertissements"])), 1, "modification (prepare) : au-dessus du budget, avertissement")
    verifie(marque(apm2.prepare_modification(racine, PORTAIL, rp)["avertissements"]), [], "modification (prepare) : sous le budget, rien")


def test_route(t):
    b = tfw.Banc(t)
    try:
        (b.racine / apm.FICHIER_MODELE).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(RACINE / apm.FICHIER_MODELE, b.racine / apm.FICHIER_MODELE)       # dans la copie seulement
        statut, etat = b.requete("GET", f"/etat?env={PORTAIL}")
        verifie((statut, bool(etat.get("budget")), etat.get("budget", {}).get("depasse")), (200, True, False),
                "GET /etat : budget de la carte, sous le budget")
        verifie(sorted(etat["budget"]), ["a_confirmer", "budget", "cout", "depasse", "message"], "GET /etat : budget sans autre champ")
        statut, etat = avec_budget(1, lambda: b.requete("GET", f"/etat?env={PORTAIL}"))
        verifie((statut, etat["budget"]["depasse"], "au-delà du budget" in etat["budget"]["message"]), (200, True, True),
                "GET /etat : budget abaisse, depasse et message")
        statut, etat = b.requete("GET", "/etat?env=tasmota32-base")
        verifie((statut, etat.get("budget", "absent")), (200, None), "GET /etat d'une base : budget null")
    finally:
        b.ferme()


def principal():
    for test in (test_manifeste, test_parc_reel):
        try:
            test()
        except Exception as exc:
            verifie(repr(exc), "pas d'exception", test.__name__)
    for test in (test_calcul, test_temoins, test_assistant, test_route):
        with tempfile.TemporaryDirectory() as t:
            try:
                test(t)
            except Exception as exc:
                verifie(repr(exc), "pas d'exception", test.__name__)
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
