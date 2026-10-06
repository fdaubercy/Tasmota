"""Cible PlatformIO « Sniffeur ModBus » : visible dans pioarduino > Project Tasks > <env> > Custom.

Enregistree comme la cible du serveur syslog (cible_syslog_tasmota.py) :
  - ESP32 : importee par pre_utilitaires_platformio.py (extra_scripts des bases ESP32) ;
  - autre env : ce fichier en extra_script direct (pre:outils_docs/scripts_python/cible_sniffeur_modbus.py),
    jamais les deux sur un meme env (cible declaree deux fois).
Lance outils_docs/scripts_python/sniffeur_modbus.py. Le port n'est PAS celui de l'env (monitor_port
designe la carte ESP32) : c'est celui du convertisseur USB-RS485, branche sur le bus.
    port    : custom_sniffeur_modbus_port (optionnel, defaut auto = le seul CH343 present ; sinon
              demarre port ferme, a choisir sur la page)
    debit   : custom_sniffeur_modbus_debit (optionnel, defaut 19200, debit du bus du garage)
    HTTP    : custom_sniffeur_modbus_http (optionnel, defaut 7300) -> http://127.0.0.1:7300
    journal : %TEMP%/sniffeur_modbus.log

En ligne de commande : pio run -e <env> -t sniffeur_modbus
Arret : Ctrl+C dans le terminal de la tache (ou la corbeille).
"""

import os
import subprocess
import tempfile

NOM_CIBLE = "sniffeur_modbus"


def enregistre(env):
    racine = env.subst("$PROJECT_DIR")
    script = os.path.join(racine, "outils_docs", "scripts_python", "sniffeur_modbus.py")

    def lance_sniffeur(*args, **kwargs):
        port = str(env.GetProjectOption("custom_sniffeur_modbus_port", "auto") or "auto")
        debit = str(env.GetProjectOption("custom_sniffeur_modbus_debit", "19200") or "19200")
        http = str(env.GetProjectOption("custom_sniffeur_modbus_http", "7300") or "7300")
        journal = os.path.join(tempfile.gettempdir(), "sniffeur_modbus.log")
        commande = [env.subst("$PYTHONEXE"), "-u", script, "--port", port, "--debit", debit,
                    "--http", http, "--journal", journal]
        print(f"sniffeur ModBus -> http://127.0.0.1:{http}  (journal : {journal})")
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
        title="Sniffeur ModBus (HTTP 127.0.0.1)",
        description="Ecoute le bus RS485 par le convertisseur USB-RS485, decode les trames ModBus et "
                    "les affiche sur http://127.0.0.1:7300 (envoi et emulation de la carte relais).",
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
