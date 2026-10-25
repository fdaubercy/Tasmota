"""Banc de fichiers_berry_renommage (renommer un env : identite reproposee, dossier deplace, spec §10).

Code de sortie 0 = vert. Depot d'essai = COPIE des vrais .ini, .h et dossiers de carte
(test_fichiers_berry_creation.depot_essai) dans un dossier temporaire ; sauvegardes dans un
OUTILS_TASMOTA_DOSSIER temporaire. Le vrai depot n'est jamais ecrit.
"""

import json
import os
import re
import sys
import tempfile
from pathlib import Path

import build_envs
import fichiers_berry_creation as fbc
import fichiers_berry_ini as fbi
import fichiers_berry_renommage as fbr
import test_fichiers_berry_creation as tfc
from fichiers_berry_renommage import Renommage

ECHECS = []
OVERRIDE = "platformio_override.ini"
RIDEAU, DOSSIER_RIDEAU = tfc.RIDEAU, tfc.DOSSIER_RIDEAU
DEFINE_RIDEAU = "FIRMWARE_ESP32S3_RIDEAU_GARAGE_MODBUS"
SANS_BUILD = lambda: []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def octets(racine, *fichiers):
    return {f: (racine / f).read_bytes() for f in fichiers}


def identite_actuelle(racine, define):
    """Valeurs d'identite de la section du .h de `define` (pour revenir au nom d'origine)."""
    h = tfc.texte(racine, fbc.FICHIER_H)
    i = h.index(f"defined({define})")
    bloc = h[i:tfc.fin_section(h, i)]
    return {c: re.search(r'#define\s+' + c + r'\s+"([^"]*)"', bloc).group(1) for c in fbc.CHAMPS_IDENTITE}


def identite_persist(racine, dossier):
    """Valeurs d'identite telles que le _persist.json les porte (texte brut, comme le remplacement cible)."""
    t = tfc.texte(racine, dossier + "/_persist.json")
    spans = fbc.spans_json(t)
    return {champ: t[slice(*spans[tuple(cle.split("."))])] for cle, champ in fbc.CLES_PERSIST.items()}


def renommage(env=RIDEAU, lieu="garage", nom="porte2", define="", **identite):
    ident = fbc.identite_par_defaut(lieu, nom)
    ident.update(identite)
    return Renommage(env=env, lieu=lieu, nom=nom, identite=ident, define=define)


def renomme(racine, r):
    p = fbr.prepare_renommage(racine, r)
    verifie(p["refus"], [], f"prepare {r.env} -> {r.lieu}/{r.nom} : aucun refus")
    return p, fbr.renomme(racine, r, p["empreinte"], SANS_BUILD)


def test_renommage_rideau(racine):
    persist_avant = (racine / DOSSIER_RIDEAU / "_persist.json").read_bytes()
    p, res = renomme(racine, renommage())
    envs = {e.nom for e in build_envs.liste_envs(racine)}
    verifie(("tasmota32s3-garage-porte2" in envs, RIDEAU in envs), (True, False), "page build : nouvel env vu, ancien absent")
    nouveau = racine / "data/garage/tasmota32s3-porte2"
    verifie(((racine / DOSSIER_RIDEAU).exists(), (nouveau / "autoexec.be").is_file(),
             any("sauvegarde" in d.name for d in (racine / "data/garage").iterdir())), (False, True, False),
            "dossier deplace (ni ancien, ni copie -sauvegarde)")
    persist = json.loads((nouveau / "_persist.json").read_text(encoding="utf-8"))
    verifie((persist["serveur"]["mqtt"]["topic"], persist["serveur"]["hostname"]), ("garage/porte2", "PORTE2-GARAGE"),
            "persist : identite nouvelle")
    verifie(len((nouveau / "_persist.json").read_bytes()) > 0 and (nouveau / "_persist.json").read_bytes() != persist_avant,
            True, "persist : reecrit")
    h = tfc.texte(racine, fbc.FICHIER_H)
    verifie((DEFINE_RIDEAU in h, "FIRMWARE_ESP32S3_GARAGE_PORTE2" in h), (False, True), ".h : ancien define parti, nouveau present")
    section = tfc.section_cenv(racine, "tasmota32s3-garage-porte2")
    verifie(any("data/garage/tasmota32s3-porte2" in l for l in section) and not any(DOSSIER_RIDEAU in l for l in section),
            True, "cenv : chemins du dossier reecrits")
    verifie((Path(res["sauvegarde"]) / fbc.FICHIER_H).is_file(), True, "sauvegarde horodatee")


def test_aller_retour(racine):
    avant = octets(racine, fbi.FICHIER_CENV, OVERRIDE, DOSSIER_RIDEAU + "/_persist.json")
    origine = identite_persist(racine, DOSSIER_RIDEAU)
    renomme(racine, renommage())
    renomme(racine, renommage(env="tasmota32s3-garage-porte2", nom="rideau-garage-modbus", define=DEFINE_RIDEAU, **origine))
    verifie(octets(racine, fbi.FICHIER_CENV, OVERRIDE, DOSSIER_RIDEAU + "/_persist.json") == avant, True,
            "renommer puis revenir : cenv, override et persist identiques octet pour octet")


def test_unicite(racine):
    origine = identite_actuelle(racine, DEFINE_RIDEAU)
    p = fbr.prepare_renommage(racine, renommage(WIFI_IP_ADDRESS=origine["WIFI_IP_ADDRESS"],
                                                 MQTT_TOPIC=origine["MQTT_TOPIC"], MQTT_CLIENT_ID=origine["MQTT_CLIENT_ID"]))
    verifie(p["refus"], [], "identite actuelle de l'env gardee : acceptee")
    cuve = identite_actuelle(racine, "FIRMWARE_ESP32S3_CAPTEURS_CUVE_MODBUS")
    p = fbr.prepare_renommage(racine, renommage(MQTT_TOPIC=cuve["MQTT_TOPIC"]))
    verifie(any(cuve["MQTT_TOPIC"] in x for x in p["refus"]), True, "topic d'une AUTRE carte : refuse")


def test_default_envs(racine):
    o = racine / OVERRIDE
    o.write_bytes(re.sub(rb"(?m)^data_dir\s*=.*?(\r?)$", ("data_dir = " + DOSSIER_RIDEAU).encode() + rb"\1", o.read_bytes()))
    avant = fbi.decoupe(tfc.texte(racine, OVERRIDE))
    renomme(racine, renommage())
    apres = fbi.decoupe(tfc.texte(racine, OVERRIDE))
    verifie([l for l in apres if l not in avant], ["data_dir = data/garage/tasmota32s3-porte2",
                                                   "                            tasmota32s3-garage-porte2"],
            "default_envs : ligne active renommee, toujours active ; data_dir suit le dossier")
    renomme(racine, renommage(env="tasmota32s3-garage-serveur-modbus", lieu="garage", nom="maitre-s3"))
    verifie(any(l.strip() == "; tasmota32s3-garage-maitre-s3" for l in fbi.decoupe(tfc.texte(racine, OVERRIDE))), True,
            "default_envs : ligne commentee renommee, toujours commentee")


def test_autre_lieu(racine):
    renomme(racine, renommage(lieu="atelier", nom="porte"))
    t = tfc.texte(racine, fbi.FICHIER_CENV)
    verifie(t.index("; LOCALISATION: ATELIER") < t.index("[env:tasmota32s3-atelier-porte]"), True,
            "autre lieu : section sous un nouveau bandeau")
    verifie((racine / "data/atelier/tasmota32s3-porte/autoexec.be").is_file(), True, "autre lieu : dossier deplace")


def test_refus(racine):
    p = fbr.prepare_renommage(racine, renommage(nom="capteurs-cuve-modbus"))
    verifie(any("existe" in x for x in p["refus"]), True, "nouveau nom deja pris : refus")
    p = fbr.prepare_renommage(racine, renommage(nom="rideau-garage-modbus"))
    verifie(len(p["refus"]) > 0, True, "meme nom : refus")
    try:
        fbr.prepare_renommage(racine, renommage(env="tasmota32s3-base-N16R8"))
        verifie("accepte", "refus", "base : refus")
    except LookupError:
        pass
    r = renommage()
    p = fbr.prepare_renommage(racine, r)
    for builds in (lambda: ["pio run"], lambda: None):
        try:
            fbr.renomme(racine, r, p["empreinte"], builds)
            verifie("renomme", "refus", "build : refus")
        except RuntimeError:
            verifie((racine / DOSSIER_RIDEAU).is_dir(), True, "build : rien de renomme")
    try:
        fbr.renomme(racine, renommage(WIFI_IP_ADDRESS="192.168.0.249"), p["empreinte"], SANS_BUILD)
        verifie("renomme", "refus", "saisie changee depuis le diff : refus")
    except RuntimeError:
        verifie((racine / DOSSIER_RIDEAU).is_dir(), True, "saisie changee : rien de renomme")


def test_atomique(racine):
    import fichiers_berry_sauvegarde as fbs
    avant = octets(racine, fbi.FICHIER_CENV, fbc.FICHIER_H, OVERRIDE, DOSSIER_RIDEAU + "/_persist.json")
    r = renommage()
    p = fbr.prepare_renommage(racine, r)
    origine = fbs.Transaction.ecrit

    def panne(self, rel, contenu):                   # le persist, ecrit en dernier, ne passe pas
        if rel.endswith("_persist.json"):
            raise OSError("panne simulee")
        return origine(self, rel, contenu)
    fbs.Transaction.ecrit = panne
    try:
        fbr.renomme(racine, r, p["empreinte"], SANS_BUILD)
        verifie("renomme", "panne", "atomique : la panne remonte")
    except OSError:
        pass
    finally:
        fbs.Transaction.ecrit = origine
    verifie(octets(racine, fbi.FICHIER_CENV, fbc.FICHIER_H, OVERRIDE, DOSSIER_RIDEAU + "/_persist.json") == avant, True,
            "atomique : fichiers remis, dossier revenu a son nom")


def principal():
    for test in (test_renommage_rideau, test_aller_retour, test_unicite, test_default_envs, test_autre_lieu,
                 test_refus, test_atomique):
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
