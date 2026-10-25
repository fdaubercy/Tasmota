"""Banc de fichiers_berry_suppression (supprimer un env : cenv, .h, default_envs, dossier en -sauvegarde).

Code de sortie 0 = vert. Depot d'essai = COPIE des vrais .ini, du vrai user_config_override.h et des vrais
dossiers de carte (test_fichiers_berry_creation.depot_essai), dans un dossier temporaire ; sauvegardes dans un
OUTILS_TASMOTA_DOSSIER temporaire. Le vrai depot n'est jamais ecrit.
"""

import os
import re
import sys
import tempfile
from pathlib import Path

import fichiers_berry_creation as fbc
import fichiers_berry_ini as fbi
import fichiers_berry_suppression as fbx
import test_fichiers_berry_creation as tfc

ECHECS = []
OVERRIDE = "platformio_override.ini"
RIDEAU, DOSSIER_RIDEAU = tfc.RIDEAU, tfc.DOSSIER_RIDEAU
CUVE = "tasmota32s3-garage-capteurs-cuve-modbus"
CAVE32, CAVE_S3 = "tasmota32-cave-serveur-rly", "tasmota32s3-cave-serveur-rly"
SANS_BUILD = lambda: []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def octets(racine, *fichiers):
    return {f: (racine / f).read_bytes() for f in fichiers}


def supprime(racine, env):
    p = fbx.prepare_suppression(racine, env)
    verifie(p["refus"], [], f"prepare {env} : aucun refus")
    return p, fbx.supprime(racine, env, p["empreinte"], SANS_BUILD)


def test_aller_retour(racine):
    avant = octets(racine, fbi.FICHIER_CENV, fbc.FICHIER_H, OVERRIDE)
    tfc.cree(racine, tfc.creation())
    p, r = supprime(racine, "tasmota32s3-garage-porte-test")
    verifie(octets(racine, fbi.FICHIER_CENV, fbc.FICHIER_H, OVERRIDE) == avant, True,
            "creation puis suppression : cenv, .h et override identiques octet pour octet")
    verifie(((racine / "data/garage/tasmota32s3-porte-test").exists(),
             (racine / "data/garage/tasmota32s3-porte-test-sauvegarde/autoexec.be").is_file()), (False, True),
            "dossier renomme en -sauvegarde")
    verifie(r["dossier_sauvegarde"], "data/garage/tasmota32s3-porte-test-sauvegarde", "resultat : dossier renomme")
    verifie((Path(r["sauvegarde"]) / fbc.FICHIER_H).is_file(), True, "sauvegarde horodatee du .h")
    verifie("[env:tasmota32s3-garage-porte-test]" in p["diff"], True, "diff : section retiree visible")


def test_section_partagee_puis_tete(racine):
    _, r = supprime(racine, CAVE32)
    h = tfc.texte(racine, fbc.FICHIER_H)
    verifie(fbi.decoupe(h).count("        #if defined(FIRMWARE_ESP32S3_CAVE_SERVEUR_RLY)"), 1,
            "section partagee : seul defined(FIRMWARE_ESP32_CAVE_SERVEUR_RLY) part de la condition")
    verifie("FIRMWARE_ESP32_CAVE_SERVEUR_RLY" in h, False, "section partagee : ancien define absent du .h")
    verifie(any("condition interne" in a and "FIRMWARE_ESP32S3_CAVE_SERVEUR_RLY" in a for a in r["avertissements"]), True,
            "section partagee : conditions internes de la section signalees (a revoir a la main)")
    supprime(racine, CAVE_S3)
    h = tfc.texte(racine, fbc.FICHIER_H)
    verifie(re.search(r"FIRMWARE_ESP32S3?_CAVE_SERVEUR_RLY", h) is None, True, "section de tete retiree")
    verifie(h.count("        #if defined(FIRMWARE_TELEINFO_CONSO)"), 1, "section suivante passee de #elif a #if")
    verifie(h.count("        #elif defined(FIRMWARE_TELEINFO_CONSO)"), 0, "plus de #elif pour la nouvelle tete")


def test_default_envs(racine):
    avant = fbi.decoupe(tfc.texte(racine, OVERRIDE))
    _, r = supprime(racine, RIDEAU)                     # ligne active de default_envs
    apres = fbi.decoupe(tfc.texte(racine, OVERRIDE))
    verifie([l for l in avant if l not in apres], ["                            " + RIDEAU],
            "default_envs : seule la ligne active de l'env part")
    commentee = next(l for l in apres if l.strip() == "; tasmota32s3-garage-serveur-modbus")
    supprime(racine, "tasmota32s3-garage-serveur-modbus")
    apres2 = fbi.decoupe(tfc.texte(racine, OVERRIDE))
    verifie([l for l in apres if l not in apres2], [commentee], "default_envs : ligne commentee retiree, aucune autre")
    verifie(any(l.strip() == "; tasmota32p4-garage-serveur-modbus" or l.strip() == "tasmota32p4-garage-serveur-modbus"
                for l in apres2), True, "default_envs : l'env P4 au nom voisin reste")
    o = racine / OVERRIDE                                # data_dir change a chaque build : pose ici sur la cuve
    o.write_bytes(re.sub(rb"(?m)^data_dir\s*=.*?(\r?)$", b"data_dir = data/garage/tasmota32s3-capteurs-cuve-modbus\\1",
                         o.read_bytes()))
    _, r = supprime(racine, CUVE)                        # data_dir = son dossier
    verifie(any("data_dir" in a for a in r["avertissements"]), True, "data_dir sur le dossier supprime : signale")


def test_sauvegarde_prise(racine):
    (racine / (DOSSIER_RIDEAU + "-sauvegarde")).mkdir()
    _, r = supprime(racine, RIDEAU)
    verifie(r["dossier_sauvegarde"], DOSSIER_RIDEAU + "-sauvegarde-2", "-sauvegarde deja pris -> -sauvegarde-2")
    verifie((racine / (DOSSIER_RIDEAU + "-sauvegarde-2/autoexec.be")).is_file(), True, "-sauvegarde-2 rempli")


def test_refus(racine):
    p = fbx.prepare_suppression(racine, "tasmota32s3-base-N16R8")
    verifie(any(RIDEAU in x for x in p["refus"]), True, "base heritee et referencee : refus qui nomme ses envs")
    try:
        fbx.prepare_suppression(racine, "tasmota32s3-safeboot")
        verifie("accepte", "refus", "env de l'amont : refus")
    except LookupError:
        pass
    p = fbx.prepare_suppression(racine, RIDEAU)
    avant = octets(racine, fbi.FICHIER_CENV, fbc.FICHIER_H, OVERRIDE)
    for builds, libelle in ((lambda: ["pio run"], "build en cours"), (lambda: None, "detection impossible")):
        try:
            fbx.supprime(racine, RIDEAU, p["empreinte"], builds)
            verifie("supprime", "refus", f"refus : {libelle}")
        except RuntimeError:
            verifie((racine / DOSSIER_RIDEAU).is_dir(), True, f"refus ({libelle}) : rien de supprime")
    try:
        fbx.supprime(racine, CUVE, p["empreinte"], SANS_BUILD)     # empreinte d'un autre env
        verifie("supprime", "refus", "refus : empreinte d'une autre demande")
    except RuntimeError:
        verifie(octets(racine, fbi.FICHIER_CENV, fbc.FICHIER_H, OVERRIDE) == avant, True, "refus empreinte : rien d'ecrit")


def test_atomique(racine):
    import fichiers_berry_sauvegarde as fbs
    avant = octets(racine, fbi.FICHIER_CENV, fbc.FICHIER_H, OVERRIDE)
    p = fbx.prepare_suppression(racine, RIDEAU)
    origine, vus = fbs.Transaction.ecrit, []

    def panne(self, rel, contenu):                    # la 2e ecriture echoue
        vus.append(rel)
        if len(vus) == 2:
            raise OSError("panne simulee")
        return origine(self, rel, contenu)
    fbs.Transaction.ecrit = panne
    try:
        fbx.supprime(racine, RIDEAU, p["empreinte"], SANS_BUILD)
        verifie("supprime", "panne", "atomique : la panne remonte")
    except OSError:
        pass
    finally:
        fbs.Transaction.ecrit = origine
    verifie(octets(racine, fbi.FICHIER_CENV, fbc.FICHIER_H, OVERRIDE) == avant, True, "atomique : fichiers remis")
    verifie(((racine / DOSSIER_RIDEAU).is_dir(), (racine / (DOSSIER_RIDEAU + "-sauvegarde")).exists()), (True, False),
            "atomique : dossier non renomme")


def test_citations(racine):
    script = racine / "outils_docs/scripts_python/berry/banc_essai.py"
    script.parent.mkdir(parents=True)
    script.write_text(f'CARTES = {{"{RIDEAU}": "{DOSSIER_RIDEAU}"}}\n', encoding="utf-8")
    p = fbx.prepare_suppression(racine, RIDEAU)
    verifie(any("banc_essai.py" in a for a in p["avertissements"]), True, "citation dans un script : signalee")
    supprime(racine, RIDEAU)
    verifie(RIDEAU in script.read_text(encoding="utf-8"), True, "citation dans un script : non modifiee")


def principal():
    for test in (test_aller_retour, test_section_partagee_puis_tete, test_default_envs, test_sauvegarde_prise,
                 test_refus, test_atomique, test_citations):
        with tempfile.TemporaryDirectory() as t:
            os.environ["OUTILS_TASMOTA_DOSSIER"] = os.path.join(t, "outils")
            try:
                test(tfc.depot_essai(t))
            except Exception as exc:
                verifie(repr(exc), "pas d'exception", test.__name__)
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
