"""Cible PlatformIO « Sniffeur MQTT » : visible dans pioarduino > Project Tasks > <env> > Custom.

Enregistree comme la cible du pont serie (cible_pont_serie.py) :
  - ESP32 : importee par pre_utilitaires_platformio.py (extra_scripts des bases ESP32) ;
  - autre env : ce fichier en extra_script direct (pre:outils_docs/scripts_python/cible_sniffeur_mqtt.py),
    jamais les deux sur un meme env (cible declaree deux fois).
Lance outils_docs/scripts_python/sniffeur_mqtt.py. Le broker ne depend pas de l'env choisi : il est lu
dans tasmota/user_config_override.h (MQTT_HOST/PORT/USER/PASS).
    HTTP    : custom_sniffeur_http (optionnel, defaut 7100) -> http://127.0.0.1:7100
    journal : %TEMP%/sniffeur_mqtt.log

En ligne de commande : pio run -e <env> -t sniffeur_mqtt
Arret : Ctrl+C dans le terminal de la tache (ou la corbeille).
"""

import os
import subprocess
import tempfile

NOM_CIBLE = "sniffeur_mqtt"


def enregistre(env):
    racine = env.subst("$PROJECT_DIR")
    script = os.path.join(racine, "outils_docs", "scripts_python", "sniffeur_mqtt.py")

    def lance_sniffeur(*args, **kwargs):
        http = str(env.GetProjectOption("custom_sniffeur_http", "7100") or "7100")
        journal = os.path.join(tempfile.gettempdir(), "sniffeur_mqtt.log")
        commande = [env.subst("$PYTHONEXE"), "-u", script, "--http", http, "--journal", journal]
        print(f"sniffeur MQTT -> http://127.0.0.1:{http}  (journal : {journal})")
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
        title="Sniffeur MQTT (HTTP 127.0.0.1)",
        description="Ecoute le broker MQTT (user_config_override.h), filtre et publie depuis "
                    "http://127.0.0.1:7100.",
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
