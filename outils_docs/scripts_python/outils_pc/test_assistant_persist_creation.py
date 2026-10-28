"""Banc de assistant_persist_creation (creation atomique d'un env genere, et son demarrage prouve).

Code de sortie 0 = vert. La creation se joue pour de vrai dans un depot d'essai (copie des .ini, du .h, des
dossiers de cartes, de data/fs et du modele) dans un dossier temporaire : jamais dans le vrai depot. Aucune valeur de
mot de passe n'est imprimee : les secrets se cherchent par egalite/inclusion et un echec n'affiche que des booleens.
Le dernier test fait demarrer la carte generee sur le faux firmware (banc_demarrage --dossier, berry.exe requis).
A lancer avec le Python du penv (ProjectConfig) :
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" -u outils_docs/scripts_python/outils_pc/test_assistant_persist_creation.py
    ... --garde <dossier>   laisse le depot d'essai (apres creation de la carte piscine) dans ce dossier
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import assistant_persist_creation as apc
import assistant_persist_modele as apm
import assistant_persist_parc as parc
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi
import fichiers_berry_sauvegarde as fbs
from assistant_persist_generation import Reponses
from test_fichiers_berry_creation import RACINE, RIDEAU, depot_essai

ECHECS = []
MAITRE = "tasmota32p4-garage-serveur-modbus"
ENV = "tasmota32s3-garage-piscine"
DOSSIER = "data/garage/tasmota32s3-piscine"
BLOCS = ["udp", "discovery", "rangeExtender", "modbus", "ruban", "ledRGB", "historique"]
BANC_DEMARRAGE = RACINE / "outils_docs/scripts_python/berry/banc_demarrage.py"
SANS_BUILD = lambda: []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def depot(t):
    racine = depot_essai(Path(t) / "depot")
    for rel in (apm.FICHIER_MODELE, "outils_docs/schemas/persist.schema.json"):
        (racine / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(RACINE / rel, racine / rel)
    shutil.copytree(RACINE / "data" / "fs", racine / "data" / "fs")
    return racine


def reponses(**kw):
    base = dict(puce="ESP32S3", base="", lieu="garage", nom="piscine", role="esclave", maitre=MAITRE, id=4, blocs=list(BLOCS),
                metiers=["piscine"], squelettes=True)
    base.update(kw)
    return Reponses(**base)


def octets(racine, rel):
    """Empreinte du fichier (jamais ses octets : le .h porte des mots de passe, un echec les afficherait)."""
    p = Path(racine) / rel
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def secrets_reels():
    s = parc.secrets(RACINE, "SERVEUR-GARAGE-GATEWAY", "SERVEUR-GARAGE-GATEWAY")
    return sorted({x for x in s.values() if x})


def refus_de(racine, r):
    return apc.prepare(racine, r)["refus"]


def leve(fonction, *args):
    try:
        fonction(*args)
    except RuntimeError as exc:
        return str(exc)
    return None


def cree_ok(racine, r):
    p = apc.prepare(racine, r)
    verifie(p["refus"], [], "prepare piscine : aucun refus")
    return p, apc.cree(racine, r, p["empreinte"], SANS_BUILD)


def test_creation(t):
    racine = depot(t)
    os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(t) / "outils")
    r = reponses()
    p, c = cree_ok(racine, r)
    verifie((p["env"], p["dossier"], p["define"]), (ENV, DOSSIER, "FIRMWARE_ESP32S3_GARAGE_PISCINE"), "prepare : env, dossier, define")
    for f in ("_persist.json", "autoexec.be", "graphiques.json", "controlePiscine.be", "piscineFonctions.be"):
        verifie((racine / DOSSIER / f).is_file(), True, f"cree_esclave_s3 : {f} ecrit")
    cenv = (racine / fbi.FICHIER_CENV).read_text(encoding="utf-8")
    verifie(f"[env:{ENV}]" in cenv, True, "cree_esclave_s3 : section du cenv")
    verifie(ENV in fbi.lit_sections(racine).envs_cenv(), True, "cree_esclave_s3 : le cenv relu connait l'env")
    h = (racine / "tasmota/user_config_override.h").read_text(encoding="utf-8", errors="surrogateescape")
    verifie("#elif defined(FIRMWARE_ESP32S3_GARAGE_PISCINE)" in h, True, "cree_esclave_s3 : section .h")
    section = h[h.index("#elif defined(FIRMWARE_ESP32S3_GARAGE_PISCINE)"):]
    section = section[:re.search(r"\n {8}(// -- Options for|#elif\b|#else\b|#endif\b)", section).start()]
    verifie(re.search(r'#define\s+STA_SSID1\s+"SERVEUR-GARAGE-GATEWAY"', section) is not None, True,
            'cree_esclave_s3 : STA_SSID1 = "SERVEUR-GARAGE-GATEWAY"')
    verifie(section.count("#define USE_MODBUS"), 1, "cree_esclave_s3 : USE_MODBUS de son bloc")
    verifie(section.count("#define USE_WS2812 "), 1, "cree_esclave_s3 : USE_WS2812 non repete (bloc leds)")
    pers = json.loads((racine / DOSSIER / "_persist.json").read_text(encoding="utf-8"))
    verifie((pers["serveur"]["rangeExtender"]["id"], pers["serveur"]["hostname"]), (4, "PISCINE-GARAGE"), "persist : id et hostname")
    verifie(c["liens"], {"build": f"http://127.0.0.1:7700/?env={ENV}", "fichiers": f"http://127.0.0.1:7800/?env={ENV}"}, "liens")
    verifie(all(x in c["resume"] for x in (ENV, DOSSIER, "FIRMWARE_ESP32S3_GARAGE_PISCINE", "esclave", "udp")), True, "resume : env, dossier, define, role, blocs")
    # persist_valide_schema
    sys.path.insert(0, str(RACINE / "outils_docs/scripts_python/berry"))
    import genere_schema_persist as gsp
    schema = json.loads((RACINE / "outils_docs/schemas/persist.schema.json").read_text(encoding="utf-8"))
    verifie(list(gsp.valide(pers, schema)), [], "persist_valide_schema : le persist ecrit passe le schema")
    sys.path.pop(0)
    # vu_par_build
    verifie(fbe.dossier_carte(ENV), DOSSIER, "vu_par_build : dossier_carte(env) = dossier ecrit")
    verifie((racine / fbe.dossier_carte(ENV)).is_dir(), True, "vu_par_build : le dossier existe")
    verifie(ENV in [e["nom"] for e in fbe.envs_proposes(racine)], True, "vu_par_build : envs_proposes le liste")
    return racine


def test_empreinte_perimee(t):
    racine = depot(t)
    r = reponses()
    p = apc.prepare(racine, r)
    r.ip = "192.168.0.77"
    msg = leve(apc.cree, racine, r, p["empreinte"], SANS_BUILD)
    verifie(msg is not None, True, "empreinte_perimee : saisie modifiee apres prepare -> RuntimeError")
    verifie((racine / DOSSIER).exists(), False, "empreinte_perimee : rien ecrit")
    # le cenv modifie entre le diff et la creation est aussi detecte
    r = reponses()
    p = apc.prepare(racine, r)
    cenv = racine / fbi.FICHIER_CENV
    cenv.write_bytes(cenv.read_bytes() + b"\n; modifie\n")
    verifie(leve(apc.cree, racine, r, p["empreinte"], SANS_BUILD) is not None, True, "empreinte_perimee : cenv modifie -> RuntimeError")


def test_build_en_cours(t):
    racine = depot(t)
    r = reponses()
    p = apc.prepare(racine, r)
    avant = (octets(racine, fbi.FICHIER_CENV), octets(racine, "tasmota/user_config_override.h"))
    verifie(leve(apc.cree, racine, r, p["empreinte"], lambda: ["x"]) is not None, True, "build_en_cours : liste non vide -> RuntimeError")
    verifie(leve(apc.cree, racine, r, p["empreinte"], lambda: None) is not None, True, "build_en_cours : None (indetectable) -> RuntimeError")
    verifie((racine / DOSSIER).exists(), False, "build_en_cours : dossier non ecrit")
    verifie((octets(racine, fbi.FICHIER_CENV), octets(racine, "tasmota/user_config_override.h")), avant, "build_en_cours : cenv et .h intacts")


def test_refus(t):
    racine = depot(t)
    verifie(any("existe deja" in x for x in refus_de(racine, reponses(lieu="garage", nom="rideau-garage-modbus"))), True,
            "refus_existant : nom de l'env du rideau -> refus")
    verifie(refus_de(racine, reponses(metiers=["Piscine-2"])) != [], True, "refus_metier : Piscine-2 -> refus")
    verifie(any("controleGeneral.be" in x for x in refus_de(racine, reponses(metiers=["general"]))), True,
            "refus_metier : general (controleGeneral.be existe) -> refus")
    verifie(any("maitre" in x for x in refus_de(racine, reponses(maitre="tasmota32p4-inconnu"))), True, "esclave sans maitre connu -> refus")
    verifie(refus_de(racine, reponses(puce="ESP9999")) != [], True, "puce inconnue -> refus lisible (pas d'exception)")
    msg = " ".join(refus_de(racine, reponses(reseau1="RESEAU-INCONNU", role="autonome")))
    verifie("RESEAU-INCONNU" in msg, True, "reseau inconnu : le refus nomme le reseau")
    verifie(refus_de(racine, reponses(metiers=["piscine"], squelettes=False)) != [], True, "metier sans squelettes -> refus")
    verifie(any("au moins un metier" in x for x in refus_de(racine, reponses(metiers=[], squelettes=False))), True,
            "aucun metier -> refus (controleGeneral echouerait au demarrage)")
    verifie(refus_de(racine, reponses(topic="garage/#")) != [], True, "identite : topic avec joker -> refus")
    for ip in ("foo", "999.1.1.1", "::1", ""):
        verifie(any("ip" in x.lower() for x in refus_de(racine, reponses(ip=ip))), True, f"ip invalide {ip!r} -> refus")
    verifie([x for x in refus_de(racine, reponses(ip="0.0.0.0")) if "ip" in x.lower()], [], "ip 0.0.0.0 (DHCP) toleree")
    p = apc.prepare(racine, reponses(id=3))
    verifie(any("id 3" in x for x in p["avertissements"]), True, "id d'esclave deja pris -> avertissement")


def test_atomique(t):
    racine = depot(t)
    os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(t) / "outils")
    r = reponses()
    p = apc.prepare(racine, r)
    avant = (octets(racine, fbi.FICHIER_CENV), octets(racine, "tasmota/user_config_override.h"))
    appels, vraie = [], fbs.Transaction._etape

    def etape(self, libelle, annule):
        appels.append(libelle)
        if len(appels) == 3:
            raise OSError("panne injectee dans la 3e ecriture")
        return vraie(self, libelle, annule)
    fbs.Transaction._etape = etape
    try:
        try:
            apc.cree(racine, r, p["empreinte"], SANS_BUILD)
            verifie(False, True, "atomique : l'exception injectee remonte")
        except OSError:
            verifie(True, True, "atomique : l'exception injectee remonte")
    finally:
        fbs.Transaction._etape = vraie
    verifie(len(appels), 3, "atomique : la 3e etape est bien celle qui echoue")
    verifie((octets(racine, fbi.FICHIER_CENV), octets(racine, "tasmota/user_config_override.h")), avant, "atomique : octets du cenv et du .h identiques")
    verifie((racine / DOSSIER).exists(), False, "atomique : dossier absent")


def test_sans_secret(t):
    racine = depot(t)
    os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(t) / "outils")
    r = reponses()
    p, c = cree_ok(racine, r)
    sortie = json.dumps([p, {k: v for k, v in c.items()}], ensure_ascii=False)
    verifie([s for s in secrets_reels() if s in sortie], [], "diff_sans_secret : aucune valeur reelle dans prepare ni cree")
    verifie("***" in p["diff"] and "***" in p["apercu"]["persist"], True, "diff_sans_secret : '***' a la place des mots de passe")
    ecrit = (racine / DOSSIER / "_persist.json").read_text(encoding="utf-8")
    verifie(all(s in ecrit for s in secrets_reels()[:1]), True, "le persist ECRIT porte bien les vraies valeurs")
    msg = " ".join(refus_de(racine, reponses(reseau1="MAISON", role="autonome")))
    verifie([s for s in secrets_reels() if s in msg], [], "refus : aucun secret")


def test_demarrage(t):
    """La carte generee demarre sur le faux firmware : rubrique erreurs vide (banc_demarrage --dossier)."""
    berry = RACINE / "lib/libesp32/berry/berry.exe"
    if not berry.is_file():
        print("SKIP test_demarrage : berry.exe absent")
        return
    racine = depot(t)
    os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(t) / "outils")
    cree_ok(racine, reponses())
    cmd = [sys.executable, str(BANC_DEMARRAGE), "--dossier", str(racine / DOSSIER), "--env", ENV,
           "--cenv", str(racine / fbi.FICHIER_CENV), "--sources", str(racine / "data/fs")]
    sortie = subprocess.run(cmd, cwd=RACINE, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("\n".join("     " + l for l in sortie.stdout.splitlines()[-14:]))
    verifie(f"OK {ENV}" in sortie.stdout, True, "demarrage : la carte generee est jugee par le banc")
    verifie(sortie.returncode, 0, "demarrage : banc_demarrage --dossier vert (aucune erreur)")


def principal():
    garde = sys.argv[sys.argv.index("--garde") + 1] if "--garde" in sys.argv else None
    for test in (test_creation, test_empreinte_perimee, test_build_en_cours, test_refus, test_atomique, test_sans_secret,
                 test_demarrage):
        with tempfile.TemporaryDirectory() as t:
            test(t)
            if garde and test is test_creation:
                shutil.copytree(Path(t) / "depot", garde, dirs_exist_ok=True)
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
