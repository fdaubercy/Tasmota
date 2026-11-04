#!/usr/bin/env python3
"""Banc de autoexec_fichier.py : lecture masquee, remise des secrets, diff et ecriture d'un autoexec.bat (plan
autoexec-bat, A3).

Lit le vrai autoexec.bat du differentiel (data/bureau/tasmota32-interrupteur-energie) ; toute ecriture se fait sur une
COPIE temporaire des seuls fichiers utiles du depot, sauvegardes de Transaction comprises (OUTILS_TASMOTA_DOSSIER).
Aucune valeur secrete n'est affichee : les libelles ne citent que des valeurs inventees. Temoins : des mutants du
module (copie modifiee en dossier temporaire, banc relance avec AUTOEXEC_MUTANT=<dossier>) doivent rendre le banc
ROUGE. Code 0 = vert.

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_autoexec_fichier.py
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if os.environ.get("AUTOEXEC_MUTANT"):
    sys.path.insert(0, os.environ["AUTOEXEC_MUTANT"])

import autoexec_analyse as aa
import autoexec_fichier as af

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[2]
ENV = "tasmota32-bureau-interrupteur-energie"
CARTE = "data/bureau/tasmota32-interrupteur-energie"
NEUVE = "tasmota32-bureau-essai"                     # carte sans autoexec.bat (dossier cree dans la copie)
UTILES = [f"{CARTE}/autoexec.bat", f"{CARTE}/_persist.json", "data/fs/configGlobal.be",
          "outils_docs/schemas/commandes_tasmota.json", "outils_docs/schemas/banque_autoexec.json"]
ECHECS = []
AUCUN_BUILD = lambda: []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def secret_absent(texte, secrets, libelle):
    """Jamais la valeur dans le message : seulement le nombre de secrets retrouves."""
    verifie(sum(s in texte for s in secrets), 0, libelle)


def leve(fonction, exception, libelle):
    try:
        fonction()
    except exception as erreur:
        verifie(True, True, f"{libelle} ({erreur})")
        return
    verifie("aucune exception", exception.__name__, libelle)


def copie_depot(tmp):
    for rel in UTILES:
        (Path(tmp) / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(RACINE / rel, Path(tmp) / rel)
    (Path(tmp) / "data/bureau/tasmota32-essai").mkdir(parents=True)
    return Path(tmp)


def secrets_reels():
    """Valeurs secretes du vrai fichier, lues par autoexec_analyse.lignes (lecture independante du module teste)."""
    texte = (RACINE / CARTE / "autoexec.bat").read_text(encoding="utf-8")
    return [v for l in aa.lignes(texte) for nom, v in l["commandes"] if aa.SECRETS.search(nom) and v]


def ecrit_tel_quel(racine, env):
    """Relit, puis ecrit le texte de la page sans changement (rouges lus = ceux du diff)."""
    l = af.lit(racine, env)
    return af.ecrit(racine, env, l["texte"], l["empreinte"], af.diff(racine, env, l["texte"])["rouges"], AUCUN_BUILD)


def vrai_fichier(racine, secrets):
    octets = (RACINE / CARTE / "autoexec.bat").read_bytes()
    verifie(len(secrets) >= 2, True, "vrai fichier : au moins 2 secrets (en commentaire) a masquer")
    l = af.lit(racine, ENV)
    secret_absent(l["texte"], secrets, "vrai fichier : aucun secret dans lit()['texte']")
    verifie((l["existe"], l["chemin"]), (True, f"{CARTE}/autoexec.bat"), "vrai fichier : existe, chemin relatif")
    verifie((len(l["empreinte"]), l["empreinte"] == af.lit(racine, ENV)["empreinte"], l["empreinte"] == hashlib.sha256(octets).hexdigest()),
            (64, True, False), "empreinte : HMAC stable dans le processus, pas le sha256 brut")
    verifie("\r" in l["texte"], False, "vrai fichier (CRLF) : texte de la page en \\n")
    verifie(l["texte"].count("***"), len(secrets), "vrai fichier : un *** par secret")
    origine = octets.decode("utf-8").replace("\r\n", "\n")
    verifie([a == b for a, b in zip(l["texte"].splitlines(), origine.splitlines()) if "***" not in a].count(False), 0,
            "vrai fichier : lignes sans secret intactes")
    verifie(af.demasque(l["texte"], origine) == origine, True, "vrai fichier : demasque(lit) = texte d'origine")
    d = af.diff(racine, ENV, l["texte"])
    verifie((d["diff"], d["empreinte"], d["rouges"]), ("", l["empreinte"], 2), "vrai fichier sans changement : diff vide, 2 rouges")
    page = l["texte"].replace("SSId1 ", "SSId1 AutreReseau", 1).replace("WebLog 3", "WebLog 2", 1)
    d = af.diff(racine, ENV, page)
    secret_absent(d["diff"], secrets, "vrai fichier modifie : aucun secret dans le diff")
    verifie(("AutreReseau" in d["diff"], "***" in d["diff"], "WebLog 2;" in d["diff"]), (True, True, True),
            "vrai fichier modifie : diff des lignes changees, secrets en ***")
    verifie(ecrit_tel_quel(racine, ENV), {"ecrit": True, "chemin": f"{CARTE}/autoexec.bat"}, "vrai fichier : ecriture acceptee")
    verifie((racine / CARTE / "autoexec.bat").read_bytes() == octets, True, "vrai fichier : aller-retour = octets identiques (CRLF)")
    sauv = [p for p in (Path(os.environ["OUTILS_TASMOTA_DOSSIER"]) / "fichiers_berry" / "sauvegardes").iterdir()
            if p.name.endswith("-autoexec")]
    verifie((len(sauv), (sauv[0] / CARTE / "autoexec.bat").read_bytes() == octets if sauv else None), (1, True),
            "Transaction(\"autoexec\") : copie d'origine sauvegardee")


def aller_retour(racine):
    p = racine / CARTE / "autoexec.bat"
    cas = {"LF avec fin": b"SetOption1 1\nPassword1 abc\n", "LF sans fin": b"SetOption1 1\nPassword1 abc",
           "CRLF avec fin": b"SetOption1 1\r\nPassword1 abc\r\n", "CRLF sans fin": b"SetOption1 1\r\nPassword1 abc",
           "BOM": b"\xef\xbb\xbfSetOption1 1\r\n;Password1 abc\r\n", "lignes vides et espaces": b"\n  ;  x\n\n\tWebLog 1  \n\n"}
    for nom, octets in cas.items():
        p.write_bytes(octets)
        ecrit_tel_quel(racine, ENV)
        verifie(p.read_bytes(), octets, f"aller-retour {nom} : octets identiques")
    p.write_bytes(b"SetOption1 1\r\nWebLog 1")
    l = af.lit(racine, ENV)
    af.ecrit(racine, ENV, l["texte"].replace("WebLog 1", "WebLog 2") + "\n", l["empreinte"], 0, AUCUN_BUILD)
    verifie(p.read_bytes(), b"SetOption1 1\r\nWebLog 2", "fichier sans fin de ligne finale : gardee absente")
    p.write_bytes(b"SetOption1 1\r\nWebLog 1\r\n")
    l = af.lit(racine, ENV)
    af.ecrit(racine, ENV, l["texte"].rstrip("\n").replace("WebLog 1", "WebLog 2") + "\nSerialLog 0", l["empreinte"], 0, AUCUN_BUILD)
    verifie(p.read_bytes(), b"SetOption1 1\r\nWebLog 2\r\nSerialLog 0\r\n", "fichier CRLF : ligne ajoutee en CRLF, fin finale gardee")


def masquage():
    verifie(af.masque("Backlog SSId1 A; Password1 secretA\n"), "Backlog SSId1 A; Password1 ***\n", "Backlog : seule la valeur du secret masquee")
    verifie(af.masque(";Backlog MqttUser u;  MqttPassword  secretM  ;Topic t\r\n"),
            ";Backlog MqttUser u;  MqttPassword  ***  ;Topic t\r\n", "commentaire : secret masque, espaces gardes")
    verifie(af.masque("  ;; WebPassword secretW"), "  ;; WebPassword ***", "commentaire ;; : secret masque")
    verifie(af.masque("Password1=secretE\nPassword2 = secretF\n"), "Password1=***\nPassword2 = ***\n",
            "Password1=x (lu ainsi par le firmware) : masque")
    verifie(af.masque("cmnd/carte/MqttPassword secretG"), "cmnd/carte/MqttPassword ***", "prefixe cmnd/x/ : masque")
    verifie(af.masque("Password1\nSSId1 secretNon\nWebLog 1"), "Password1\nSSId1 secretNon\nWebLog 1",
            "sans valeur, ou commande sans secret : rien de masque")
    verifie(af.masque("MqttPassword un mot; de passe\n"), "MqttPassword ***\n", "hors Backlog : toute la fin de ligne est la valeur")
    for disque, attendu, libelle in [
            ("Rule1 ON System#Boot DO MqttPassword secretR ENDON\n", "Rule1 ON System#Boot DO MqttPassword ***\n", "corps de Rule"),
            ("Backlog Rule1 ON x DO WebPassword secretS ENDON; Rule1 1\n", "Backlog Rule1 ON x DO WebPassword ***; Rule1 1\n",
             "corps de Rule dans un Backlog"),
            ('Br persist.password = "secretB"\n', "Br persist.password = ***\n", "Br"),
            (";Rule1 ON x DO Password1:secretC\n", ";Rule1 ON x DO Password1***\n", "corps de Rule en commentaire"),
            ('Br persist.x = {"password":"ZZZ"}\n', 'Br persist.x = {"password***\n', "JSON colle au mot a secret"),
            ("Br f(apikey:xyz) + 1\n", "Br f(apikey***\n", "valeur collee apres :"),
            ("Br x.token=xyz\n", "Br x.token=***\n", "token=xyz colle")]:
        verifie(af.masque(disque), attendu, f"{libelle} : masque apres le mot a secret")
        verifie(af.demasque(af.masque(disque), disque), disque, f"{libelle} : remis")


def remise():
    disque = "Backlog SSId1 A; Password1 secretA\n"
    page = af.masque(disque).replace("SSId1 A", "SSId1 B")
    verifie(af.demasque(page, disque), "Backlog SSId1 B; Password1 secretA\n", "vigilance 1 : SSId1 change, Password1 d'origine remis")
    disque = "MqttPassword m1\nPassword1 p1\n"
    verifie(af.demasque("Password1 ***\n", disque), "Password1 p1\n", "remise par commande : ligne d'un autre secret retiree")
    verifie(af.demasque("Password1 ***\nMqttPassword ***\n", disque), "Password1 p1\nMqttPassword m1\n",
            "remise par commande : lignes interverties")
    disque = "Password1 a1\n;Password1 a2\n"
    verifie(af.demasque("WebLog 1\nPassword1 ***\n;Password1 ***\n", disque), "WebLog 1\nPassword1 a1\n;Password1 a2\n",
            "meme commande : ordre d'apparition")
    verifie(af.demasque("password1 ***\n;PASSWORD1 ***\n", disque), "password1 a1\n;PASSWORD1 a2\n", "nom sans tenir compte de la casse")
    verifie(af.demasque("Password1 neuf\n;Password1 ***\n", disque), "Password1 neuf\n;Password1 a2\n",
            "k-ieme apparition : 1re valeur retapee, la 2e garde a2")
    leve(lambda: af.demasque("Password1 ***\n", disque), ValueError, "apparition de Password1 retiree, *** restant : refus")
    leve(lambda: af.demasque("Password1 ***\n;Password1 ***\nPassword1 ***\n", disque), ValueError,
         "apparition de Password1 ajoutee, *** restant : refus")
    verifie(af.demasque("Password1 neuf\n", disque), "Password1 neuf\n", "apparition retiree sans *** : accepte")
    leve(lambda: af.demasque("Password1 ***\n", "Password1\n"), ValueError, "*** la ou le disque n'avait pas de valeur : refus")
    disque = "Rule1 ON x DO MqttPassword s1 ENDON\n"
    leve(lambda: af.demasque(af.masque(disque).replace("ON x", "ON token"), disque), ValueError,
         "mot a secret ajoute devant un *** : refus (*** ne serait pas remis)")
    verifie(af.demasque("; note *** gardee\n", "; note *** gardee\n"), "; note *** gardee\n", "*** deja dans le fichier : garde")
    disque = "; note *** gardee\nRule1 ON x DO MqttPassword m1 ENDON\n"
    leve(lambda: af.demasque("Rule1 ON token DO MqttPassword ***\n", disque), ValueError,
         "*** litteral ailleurs sur le disque, *** non remis : refus (critere par ligne)")
    verifie(af.demasque("Password1 neuf\nMqttPassword ***\n", "Password1 a\nMqttPassword m\n"), "Password1 neuf\nMqttPassword m\n",
            "valeur saisie en clair : gardee telle quelle")
    leve(lambda: af.demasque("Password1 ***\nPassword2 ***\n", "Password1 a\n"), ValueError, "*** sans valeur d'origine : refus")
    leve(lambda: af.demasque("Password1 ***\nPassword1 ***\n", "Password1 a\n"), ValueError, "plus de *** que de valeurs d'origine : refus")


def refus(racine):
    p = racine / CARTE / "autoexec.bat"
    p.write_bytes(b"Password1 secretH\nWebLog 1\n")
    l = af.lit(racine, ENV)
    page = l["texte"].replace("WebLog 1", "WebLog 2")
    rouges = af.diff(racine, ENV, page)["rouges"]
    verifie(rouges, 2, "Password1 en clair : 2 rouges (secret, redemarrage)")
    p.write_bytes(b"Password1 secretH\nWebLog 3\n")
    leve(lambda: af.ecrit(racine, ENV, page, l["empreinte"], rouges, AUCUN_BUILD), RuntimeError, "vigilance 4 : empreinte perimee, refus")
    verifie(p.read_bytes(), b"Password1 secretH\nWebLog 3\n", "empreinte perimee : rien d'ecrit")
    l = af.lit(racine, ENV)
    leve(lambda: af.ecrit(racine, ENV, page, l["empreinte"], rouges - 1, AUCUN_BUILD), ValueError, "rouges_lus < rouges : refus")
    leve(lambda: af.ecrit(racine, ENV, page, l["empreinte"], rouges, lambda: ["pio run -e x"]), RuntimeError, "build en cours : refus")
    leve(lambda: af.ecrit(racine, ENV, page, l["empreinte"], rouges, lambda: None), RuntimeError, "build indetectable : refus")
    leve(lambda: af.ecrit(racine, ENV, page + "Password2 ***\n", l["empreinte"], 9, AUCUN_BUILD), ValueError, "*** sans origine : refus")
    verifie(p.read_bytes(), b"Password1 secretH\nWebLog 3\n", "refus : rien d'ecrit")
    af.ecrit(racine, ENV, page, l["empreinte"], rouges, AUCUN_BUILD)
    verifie(p.read_bytes(), b"Password1 secretH\nWebLog 2\n", "rouges lus : ecrit, secret remis")
    l = af.lit(racine, ENV)
    verifie(af.diff(racine, ENV, l["texte"] + "Backlog Hostname x\n")["rouges"], 3, "Hostname (boucle de redemarrage) : un rouge de plus")
    p.write_bytes(b";MqttPassword secretK\n")
    l = af.lit(racine, ENV)
    verifie(af.diff(racine, ENV, l["texte"])["rouges"], 1, "secret en commentaire : 1 rouge")
    leve(lambda: af.ecrit(racine, ENV, l["texte"], l["empreinte"], True, AUCUN_BUILD), ValueError, "rouges_lus=True : refus")


def carte_neuve(racine):
    l = af.lit(racine, NEUVE)
    verifie((l["existe"], l["texte"], l["empreinte"], l["chemin"]), (False, "", "", "data/bureau/tasmota32-essai/autoexec.bat"),
            "carte sans autoexec.bat : existe False, texte et empreinte vides")
    leve(lambda: af.ecrit(racine, NEUVE, "WebLog 1\n", "abc", 0, AUCUN_BUILD), RuntimeError, "carte neuve, empreinte fausse : refus")
    verifie(af.ecrit(racine, NEUVE, "WebLog 1\nSetOption1 1\n", "", 0, AUCUN_BUILD)["ecrit"], True, "carte neuve : ecriture")
    verifie((racine / "data/bureau/tasmota32-essai/autoexec.bat").read_bytes(), b"WebLog 1\nSetOption1 1\n",
            "carte neuve : fichier cree, UTF-8 sans BOM, LF")
    leve(lambda: af.lit(racine, "tasmota32-base-essai"), ValueError, "base : pas d'autoexec.bat")
    leve(lambda: af.ecrit(racine, "tasmota32-absent-x", "WebLog 1\n", "", 0, AUCUN_BUILD), ValueError, "dossier de carte absent : refus")


def banc():
    secrets = secrets_reels()
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(tmp) / "donnees")
        racine = copie_depot(Path(tmp) / "depot")
        vrai_fichier(racine, secrets)
        aller_retour(racine)
        masquage()
        remise()
        refus(racine)
        carte_neuve(racine)
        (racine / "outils_docs/schemas/banque_autoexec.json").unlink()
        verifie(af.diff(racine, ENV, af.lit(racine, ENV)["texte"])["rouges"] >= 0, True, "banque absente : diff possible")
    verifie((RACINE / CARTE / "autoexec.bat").read_bytes().count(b"\r\n") > 0, True, "vrai depot : fichier non touche (toujours CRLF)")


MUTANTS = [
    ("remise par position", "nom.lower()", '""'),
    ("remise par k-ieme ***", "            k = rangs[cle] = rangs.get(cle, -1) + 1\n            if ligne[d:f] != MASQUE:\n                continue",
     "            if ligne[d:f] != MASQUE:\n                continue\n            k = rangs[cle] = rangs.get(cle, -1) + 1"),
    ("masquage des corps retire", "for mot in mots:", "for mot in list(mots)[:1]:"),
    ("*** restant non refuse", "if MASQUE in l and l not in connues:", "if False:"),
    ("*** restant compte sur tout le fichier", "if MASQUE in l and l not in connues:",
     "if texte.count(MASQUE) > texte_disque.count(MASQUE):"),
    ("valeur collee au mot a secret non masquee", "mot.start() + autoexec_analyse.SECRETS.search(mot.group()).end()", "mot.end()"),
    ("empreinte sha256 brute", "hmac.new(_CLE, octets, hashlib.sha256)", "hashlib.sha256(octets)"),
    ("rouges_lus booleen accepte", "isinstance(rouges_lus, bool) or ", ""),
    ("masquage des commentaires retire", 'if ligne[i:i + 1] == ";":', 'if ligne[i:i + 1] == ";":\n        return []\n    if False:'),
    ("empreinte ignoree", "if _empreinte(octets) != empreinte:", "if False:"),
    ("rouges lus ignores", "or rouges_lus < rouges:", "or False:"),
    ("build en cours ignore", "    if builds:", "    if False:"),
    ("build indetectable ignore", "if builds is None:", "if False:"),
    ("fins de ligne CRLF perdues", 'texte = texte.replace("\\n", "\\r\\n")', "pass"),
    ("BOM perdu", "(BOM if octets and octets.startswith(BOM) else b\"\")", 'b""'),
    ("fin de ligne finale non gardee", "elif not fin and texte.endswith", "elif False and texte.endswith"),
    ("Password1=x non masque", 'ligne[v] == "="', "False"),
    ("banque absente refusee", "    except ValueError:\n        noms = []", "    except KeyError:\n        noms = []"),
]


def temoins():
    source = (ICI / "autoexec_fichier.py").read_text(encoding="utf-8")
    for nom, ancien, nouveau in MUTANTS:
        verifie(ancien in source, True, f"mutant {nom} : motif present")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "autoexec_fichier.py").write_text(source.replace(ancien, nouveau), encoding="utf-8")
            p = subprocess.run([sys.executable, str(Path(__file__).resolve())], capture_output=True, text=True, encoding="utf-8",
                               env=dict(os.environ, AUTOEXEC_MUTANT=tmp, PYTHONIOENCODING="utf-8"))
        verifie(p.returncode != 0, True, f"temoin rouge : mutant {nom}")


if __name__ == "__main__":
    banc()
    if not os.environ.get("AUTOEXEC_MUTANT"):
        temoins()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1 if ECHECS else 0)
