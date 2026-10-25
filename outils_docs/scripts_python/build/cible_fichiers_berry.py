"""Cible PlatformIO « Fichiers Berry par env » : visible dans pioarduino > Project Tasks > <env> > Custom.

Copie adaptee de cible_build_web.py, meme fonctionnement : importee par pre_utilitaires_platformio.py
(extra_scripts des bases ESP32), l'env choisi n'a aucune importance.
    HTTP : custom_fichiers_berry_http (optionnel, defaut 7800) -> http://127.0.0.1:7800

La page n'est PAS lancee comme enfant de la cible : une cible est un `pio run` ; vivante, elle serait
comptee comme un build par garde_build (CIBLES_OUTILS la reconnait, mais seulement apres 30 s) et la
page refuserait d'ecrire le cenv pendant ce temps. Donc :
  - la page repond deja -> la cible ouvre seulement le navigateur ;
  - sinon -> la page est demarree DETACHEE (hors job, sans fenetre), sa console dans
    %LOCALAPPDATA%\outils_tasmota\consoles\fichiers_berry.log, elle ouvre elle-meme le navigateur ;
    la cible attend qu'elle reponde puis rend la main.
La cible quitte avant le reste du pre-script (pas de CFG_HOLDER, pas de platformio_override.ini) et avant
solidify-from-url.py (pas de modules.h).
ATTENTION : c'est un `pio run`. Ne JAMAIS la lancer pendant un build : lancer alors la tache VS Code
« Outil : fichiers Berry par env » ou le script. En ligne de commande : pio run -e <env> -t fichiers_berry
Banc : test_cible_fichiers_berry.py (sans PlatformIO, fausse page).
"""

import os
import subprocess
import time
import urllib.request
import webbrowser
from pathlib import Path

NOM_CIBLE = "fichiers_berry"
PORT_DEFAUT = "7800"

# Memes drapeaux que annuaire_lanceur.DRAPEAUX_HORS_JOB (pas DETACHED_PROCESS : les enfants console de la
# page, pio et esptool, ouvriraient des fenetres visibles).
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000
DRAPEAUX = CREATE_BREAKAWAY_FROM_JOB | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW if os.name == "nt" else 0

DERNIER = None          # dernier processus demarre (pour les bancs)


def repond(port, delai=1.0):
    """True si la page Fichiers Berry par env repond sur 127.0.0.1:<port>."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/execution", timeout=delai) as r:
            return r.status == 200
    except OSError:
        return False


def dossier_donnees():
    """Meme regle que outils_pc/acces_web.dossier_donnees (dossier voisin : pas d'import croise)."""
    force = os.environ.get("OUTILS_TASMOTA_DOSSIER")
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(force) if force else Path(base) / "outils_tasmota"


def _demarre(commande, racine, sortie):
    def popen(drapeaux):
        return subprocess.Popen(commande, cwd=str(racine), env=dict(os.environ, PYTHONUTF8="1"),
                                stdin=subprocess.DEVNULL, stdout=sortie, stderr=subprocess.STDOUT,
                                creationflags=drapeaux)
    try:
        return popen(DRAPEAUX)
    except OSError:
        if not DRAPEAUX & CREATE_BREAKAWAY_FROM_JOB:
            raise
        return popen(DRAPEAUX & ~CREATE_BREAKAWAY_FROM_JOB)     # job qui refuse le breakaway


def lance_page(python, racine, port, donnees, script, ouvre=webbrowser.open, demarre=_demarre, attente=20):
    """Ouvre la page si elle tourne, sinon la demarre detachee ; 0 si elle repond a la fin, sinon 1."""
    global DERNIER
    url = f"http://127.0.0.1:{port}/"
    if repond(port):
        print(f"Fichiers Berry par env tourne deja : ouverture de {url}")
        ouvre(url)
        return 0
    consoles = Path(donnees) / "consoles"
    consoles.mkdir(parents=True, exist_ok=True)
    journal = consoles / "fichiers_berry.log"
    with open(journal, "wb") as sortie:                 # une console par lancement : tronquee
        sortie.write(f"[cible fichiers_berry] lance {time.strftime('%Y-%m-%d %H:%M:%S')}\n".encode("utf-8"))
        sortie.flush()
        DERNIER = demarre([str(python), "-u", str(script), "--http", str(port)], racine, sortie)
    fin = time.monotonic() + attente
    while time.monotonic() < fin:
        if repond(port, 0.5):
            print(f"Fichiers Berry par env demarre : {url} (console : {journal})")
            return 0
        if DERNIER.poll() is not None:
            break
        time.sleep(0.3)
    print(f"Fichiers Berry par env n'a pas demarre : voir {journal}")
    try:
        print(journal.read_text(encoding="utf-8", errors="replace")[-2000:])
    except OSError:
        pass
    return 1


def enregistre(env):
    racine = env.subst("$PROJECT_DIR")
    script = os.path.join(racine, "outils_docs", "scripts_python", "outils_pc", "fichiers_berry_web.py")

    def lance(*args, **kwargs):
        port = str(env.GetProjectOption("custom_fichiers_berry_http", PORT_DEFAUT) or PORT_DEFAUT)
        try:
            return lance_page(env.subst("$PYTHONEXE"), racine, port, dossier_donnees(), script)
        except KeyboardInterrupt:
            return 0

    # Cible demandee : lancer TOUT DE SUITE depuis ce script pre, puis quitter (sinon PlatformIO
    # prepare d'abord le build : plusieurs minutes avant le lancement), comme l'annuaire.
    from SCons.Script import COMMAND_LINE_TARGETS
    if NOM_CIBLE in COMMAND_LINE_TARGETS:
        env.Exit(lance())

    env.AddCustomTarget(
        name=NOM_CIBLE,
        dependencies=None,
        actions=[lance],
        title="Fichiers Berry par env (page web)",
        description="Fichiers Berry de chaque env (sur le FS, exclu, solidifie) et creation d'un env a partir "
                    "d'une carte modele ; http://127.0.0.1:7800. Ouvre la page si elle tourne deja.",
        always_build=True,
    )


# Execute comme extra_script (SConscript) : 'Import' est fourni par SCons -> enregistre la cible.
# Importe comme module par pre_utilitaires_platformio.py : 'Import' n'existe pas -> rien ici.
try:
    Import("env")  # type: ignore[name-defined]  # noqa: F821
except NameError:
    pass
else:
    enregistre(env)  # type: ignore[name-defined]  # noqa: F821
