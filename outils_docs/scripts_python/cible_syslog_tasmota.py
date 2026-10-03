"""Cible PlatformIO « Serveur syslog » : visible dans pioarduino > Project Tasks > <env> > Custom.

Enregistree comme la cible du sniffeur MQTT (cible_sniffeur_mqtt.py) :
  - ESP32 : importee par pre_utilitaires_platformio.py (extra_scripts des bases ESP32) ;
  - autre env : ce fichier en extra_script direct (pre:outils_docs/scripts_python/cible_syslog_tasmota.py),
    jamais les deux sur un meme env (cible declaree deux fois).
Lance outils_docs/scripts_python/syslog_tasmota.py. L'ecoute ne depend pas de l'env choisi : les modules
envoient a SYS_LOG_HOST:SYS_LOG_PORT (tasmota/user_config_override.h), qui doit designer ce poste.
    UDP     : SYS_LOG_PORT de user_config_override.h (514)
    HTTP    : custom_syslog_http (optionnel, defaut 7200) -> http://127.0.0.1:7200
    journal : %TEMP%/syslog_tasmota.log (bascule en .1 au-dela de 20 Mo)

En ligne de commande : pio run -e <env> -t syslog_tasmota
Arret : Ctrl+C dans le terminal de la tache (ou la corbeille).
"""

import os
import subprocess
import tempfile

NOM_CIBLE = "syslog_tasmota"


def enregistre(env):
    racine = env.subst("$PROJECT_DIR")
    script = os.path.join(racine, "outils_docs", "scripts_python", "syslog_tasmota.py")

    def lance_syslog(*args, **kwargs):
        http = str(env.GetProjectOption("custom_syslog_http", "7200") or "7200")
        journal = os.path.join(tempfile.gettempdir(), "syslog_tasmota.log")
        commande = [env.subst("$PYTHONEXE"), "-u", script, "--http", http, "--journal", journal]
        print(f"serveur syslog -> http://127.0.0.1:{http}  (journal : {journal})")
        try:
            return subprocess.call(commande, env=dict(os.environ, PYTHONUTF8="1"))
        except KeyboardInterrupt:
            return 0

    # Cible demandee : lancer TOUT DE SUITE depuis ce script pre, puis quitter (sinon PlatformIO
    # prepare d'abord le build : plusieurs minutes avant le lancement), comme le pont serie.
    from SCons.Script import COMMAND_LINE_TARGETS
    if NOM_CIBLE in COMMAND_LINE_TARGETS:
        env.Exit(lance_syslog())

    env.AddCustomTarget(
        name=NOM_CIBLE,
        dependencies=None,
        actions=[lance_syslog],
        title="Serveur syslog (HTTP 127.0.0.1)",
        description="Recoit en UDP 514 les logs syslog des modules Tasmota et les affiche sur "
                    "http://127.0.0.1:7200.",
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
