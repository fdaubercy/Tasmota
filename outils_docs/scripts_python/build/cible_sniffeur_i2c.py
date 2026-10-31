"""Cible PlatformIO « Sniffeur I2C » : visible dans pioarduino > Project Tasks > <env> > Custom.

Enregistree comme la cible du sniffeur ModBus (cible_sniffeur_modbus.py) :
  - ESP32 : importee par pre_utilitaires_platformio.py (extra_scripts des bases ESP32) ;
  - autre env : ce fichier en extra_script direct (pre:outils_docs/scripts_python/build/cible_sniffeur_i2c.py),
    jamais les deux sur un meme env (cible declaree deux fois).
Lance outils_docs/scripts_python/outils_pc/sniffeur_i2c.py. Le port n'est PAS celui de l'env (monitor_port
designe la carte) : c'est celui de l'ESP32-S3 DEDIE au sniffeur (firmware outils_docs/firmware_sniffeur_i2c).
    port    : custom_sniffeur_i2c_port (optionnel, defaut auto = le seul port USB qui repond comme un sniffeur ;
              sinon demarre port ferme, a choisir sur la page)
    HTTP    : custom_sniffeur_i2c_http (optionnel, defaut 7350) -> http://127.0.0.1:7350 ; le sniffeur affiche aussi
              le lien reseau (avec jeton) et ouvre le navigateur (acces_web.py)
    journal : %LOCALAPPDATA%\\outils_tasmota\\sniffeur_i2c\\ (toujours actif, 30 jours)

En ligne de commande : pio run -e <env> -t sniffeur_i2c
Arret : Ctrl+C dans le terminal de la tache (ou la corbeille).
"""

import os
import subprocess

NOM_CIBLE = "sniffeur_i2c"


def enregistre(env):
    racine = env.subst("$PROJECT_DIR")
    script = os.path.join(racine, "outils_docs", "scripts_python", "outils_pc", "sniffeur_i2c.py")

    def lance_sniffeur(*args, **kwargs):
        port = str(env.GetProjectOption("custom_sniffeur_i2c_port", "auto") or "auto")
        http = str(env.GetProjectOption("custom_sniffeur_i2c_http", "7350") or "7350")
        commande = [env.subst("$PYTHONEXE"), "-u", script, "--port", port, "--http", http]
        try:
            return subprocess.call(commande, env=dict(os.environ, PYTHONUTF8="1"))
        except KeyboardInterrupt:
            return 0

    # Cible demandee : lancer TOUT DE SUITE depuis ce script pre, puis quitter (sinon PlatformIO
    # prepare d'abord le build : plusieurs minutes avant le lancement), comme le pont serie.
    from SCons.Script import COMMAND_LINE_TARGETS
    if NOM_CIBLE in COMMAND_LINE_TARGETS:
        env.Exit(lance_sniffeur())

    env.AddCustomTarget(
        name=NOM_CIBLE,
        dependencies=None,
        actions=[lance_sniffeur],
        title="Sniffeur I2C (HTTP 127.0.0.1)",
        description="Ecoute un bus I2C par l'ESP32-S3 dedie, decode chaque transaction jusqu'au registre et "
                    "l'affiche sur http://127.0.0.1:7350 (lecture/ecriture d'un registre par la carte ou au banc).",
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
