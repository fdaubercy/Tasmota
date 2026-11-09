#!/usr/bin/env python3
"""Banc de autoexec_berry.py et de l'alerte « absente » des commandes Berry (plan autoexec-mqtt-tapp, amelioration A).

Faux depot en dossier temporaire (jamais le vrai) ; le vrai depot sert a un controle : aucune alerte sur ses autoexec.bat, et
tous ses envs se calculent. Temoins : mutants (copie modifiee, banc relance avec AUTOEXEC_MUTANT=<dossier>). Code 0 = vert.

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_autoexec_berry.py
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

if os.environ.get("AUTOEXEC_MUTANT"):
    sys.path.insert(0, os.environ["AUTOEXEC_MUTANT"])

import autoexec_analyse as aa
import autoexec_berry as ab
import autoexec_commandes
import fichiers_berry_etat

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[2]
ENV = "tasmota32s3-lieu-carte"
ECHECS = []
AUTO = ('# "controleD" desactive\nimport demarrage\ndemarrage.charge(["controleA"])\n'
        'demarrage.compile(["controleC"], "serveur.udp")\ndemarrage.leds()\ngestionFileFolder.loadBerryFile("/doubleE", "ON")\n')

SANS_D = AUTO.split(chr(10), 1)[1]


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def faux_depot(tmp, auto):
    fs, carte = Path(tmp) / "data" / "fs", Path(tmp) / "data" / "lieu" / "tasmota32s3-carte"
    fs.mkdir(parents=True)
    carte.mkdir(parents=True)
    for nom, src in (("controleA", "import aideB\ntasmota.add_cmd('ReglageA', f)\n"), ("aideB", 'tasmota.add_cmd("ReglageB", f)\n'),
                     ("controleC", 'tasmota.add_cmd("ReglageC", f)\n'), ("controleD", 'tasmota.add_cmd("ReglageD", f)\n'),
                     ("controleLeds", 'tasmota.add_cmd("ReglageLeds", f)\n'), ("doubleE", 'tasmota.add_cmd("ReglageE", f)\n'),
                     ("controleF", 'tasmota.add_cmd("DIMMER", f)\n')):
        (fs / (nom + ".be")).write_text(src, encoding="utf-8")
    (carte / "autreE.be").write_text('tasmota.add_cmd("ReglageE", f)\n', encoding="utf-8")     # 2e declarant, jamais charge
    if auto is not None:
        (carte / "autoexec.be").write_text(auto, encoding="utf-8")
    return Path(tmp)


def envs():
    import assistant_persist_modification as apm2
    return [c["env"] for c in apm2.cartes(RACINE)]


def banc():
    base = autoexec_commandes.charge(RACINE)
    commandes = dict(base, connues=dict(base["connues"], DIMMER="tasmota/x.ino::k", REGLAGED="data/fs/controleD.be",
                                        REGLAGEA="data/fs/controleA.be"))
    with tempfile.TemporaryDirectory() as tmp:
        r = faux_depot(tmp, AUTO)
        auto_be = r / "data" / "lieu" / "tasmota32s3-carte" / "autoexec.be"
        n = ab.non_chargees(r, ENV)
        verifie("REGLAGEA" in n, False, "module charge par demarrage.charge : pas signale")
        verifie("REGLAGEB" in n, False, "module importe par un module charge (fermeture transitive) : pas signale")
        verifie("REGLAGEC" in n, False, "module cite dans demarrage.compile : compte comme charge (prudence)")
        verifie("REGLAGELEDS" in n, False, "demarrage.leds() charge controleLeds")
        verifie("REGLAGEE" in n, False, "commande a 2 declarants dont un charge (\"/doubleE\") : pas signale")
        verifie("REGLAGED" in n, False, "controleD cite entre guillemets seulement en commentaire : compte comme charge (silence)")
        auto_be.write_text(SANS_D, encoding="utf-8")
        n = ab.non_chargees(r, ENV)
        verifie(n.get("REGLAGED"), ["controleD"], "controleD jamais cite : signale avec son module")
        verifie(sorted(n), ["DIMMER", "REGLAGED"], "seuls D et le DIMMER de controleF sont non charges")
        auto_be.write_text(SANS_D + 'demarrage.charge(["controleD"])\n', encoding="utf-8")
        verifie("REGLAGED" in ab.non_chargees(r, ENV), False, "autoexec.be modifie : le cache est invalide")
        auto_be.write_text(SANS_D, encoding="utf-8")
        n = ab.non_chargees(r, ENV)

        def ana(t, b=n):
            return [(x["ligne"], x["type"], x["niveau"], x["commande"]) for x in aa.analyse(t, {}, commandes, berry_env=b)
                    if x["type"] == "absente"]
        verifie(ana("ReglageD tous info"), [(1, "absente", "orange", "ReglageD")], "analyse : commande Berry non chargee -> absente orange")
        verifie(ana("reglaged 1"), [(1, "absente", "orange", "reglaged")], "analyse : casse libre")
        verifie(ana("Backlog Delay 1; ReglageD 1"), [(1, "absente", "orange", "ReglageD")], "analyse : dans un Backlog")
        verifie(ana("; ReglageD 1"), [], "analyse : commentaire -> rien")
        verifie(ana("ReglageA 1"), [], "analyse : module charge -> rien")
        verifie(ana("Dimmer 50"), [], "analyse : homonyme d'une commande du firmware -> rien (elle existe)")
        verifie(ana("ReglageD 1", None), [], "analyse : berry_env None -> rien")
        verifie(ana("ReglageZ 1"), [], "analyse : commande Berry inconnue du depot -> rien (pas de certitude)")
        verifie([x["message"] for x in aa.analyse("ReglageD 1", {}, commandes, berry_env=n) if x["type"] == "absente"],
                ["ReglageD est une commande Berry du module controleD, que l'autoexec.be de cette carte ne charge pas."], "analyse : message")
        for libelle, contenu in (("absent", None), ("vide", ""), ("de forme ancienne sans module reconnu", "var x = 1\nload(chemin)\n"),
                                 ("avec un module inexistant seulement", 'demarrage.charge(["nexistepas"])\n')):
            with tempfile.TemporaryDirectory() as t2:
                verifie(ab.non_chargees(faux_depot(t2, contenu), ENV), None, f"autoexec.be {libelle} : None (on se tait)")
        verifie(ab.non_chargees(r, "tasmota32s3-base"), None, "env sans dossier de carte : None")
        verifie(ab.non_chargees(r, "nom_sans_tiret"), None, "nom d'env sans tiret : None")
    for bat in sorted((RACINE / "data").rglob("autoexec.bat")):
        env = next((e for e in envs() if RACINE / fichiers_berry_etat.dossier_carte(e) == bat.parent), None)
        verifie(env is not None, True, f"vrai depot : env de {bat.relative_to(RACINE).as_posix()} trouve")
        if env:
            res = [x for x in aa.analyse(bat.read_text(encoding="utf-8"), {}, base, berry_env=ab.non_chargees(RACINE, env))
                   if x["type"] == "absente"]
            verifie(res, [], f"vrai depot : aucune alerte Berry sur {bat.parent.name}")
    for e in envs():
        n = ab.non_chargees(RACINE, e)
        verifie(n is None or isinstance(n, dict), True, f"vrai depot : {e} se calcule sans erreur")


MUTANTS = [
    ("fermeture transitive retiree", 'if n in modules and n != "autoexec" and n not in charges:', "if False:"),
    ("demarrage.leds ignore", "if motif in auto for", "if False for"),
    ("un declarant charge ne suffit pas", "if not mods & charges}", "if not mods <= charges}"),
    ("autoexec non compris -> tout signale", "    if not charges:\n        return None", "    if False:\n        return None"),
    ("prefixe slash non reconnu", "[\"']/?([A-Za-z_]", "[\"']([A-Za-z_]"),
]


def temoins():
    source = (ICI / "autoexec_berry.py").read_text(encoding="utf-8")
    for nom, ancien, nouveau in MUTANTS:
        verifie(ancien in source, True, f"mutant {nom} : motif present")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "autoexec_berry.py").write_text(source.replace(ancien, nouveau, 1), encoding="utf-8")
            p = subprocess.run([sys.executable, str(Path(__file__).resolve())], capture_output=True, text=True, encoding="utf-8",
                               env=dict(os.environ, AUTOEXEC_MUTANT=tmp, PYTHONIOENCODING="utf-8"))
        verifie(p.returncode != 0, True, f"temoin rouge : mutant {nom}")


if __name__ == "__main__":
    banc()
    if not os.environ.get("AUTOEXEC_MUTANT"):
        temoins()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1 if ECHECS else 0)
