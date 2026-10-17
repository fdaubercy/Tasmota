"""Cible PlatformIO « Testeur UDP maitre/esclave » : visible dans pioarduino > Project Tasks > <env> > Custom.

Enregistree comme la cible du sniffeur ModBus (cible_sniffeur_modbus.py) :
  - ESP32 : importee par pre_utilitaires_platformio.py (extra_scripts des bases ESP32) ;
  - autre env : ce fichier en extra_script direct (pre:outils_docs/scripts_python/build/cible_testeur_udp.py),
    jamais les deux sur un meme env (cible declaree deux fois).
Lance outils_docs/scripts_python/outils_pc/testeur_udp.py. Les ports ne sont PAS celui de l'env
(monitor_port) : ce sont ceux du maitre ModBus (ESP32-P4) et d'un esclave (ESP32-S3).
    maitre  : custom_testeur_udp_port_maitre (optionnel, defaut vide = ferme, a choisir sur la page)
    esclave : custom_testeur_udp_port_esclave (optionnel, defaut vide = ferme)
    HTTP    : custom_testeur_udp_http (optionnel, defaut 7400) -> http://127.0.0.1:7400
    journal : %TEMP%/testeur_udp.log

ATTENTION : c'est un `pio run`. Ne JAMAIS la lancer pendant un build (le changement d'env peut faire
supprimer .pio/build) : lancer alors la tache VS Code « Outil : testeur UDP maitre/esclave » ou le script.
En ligne de commande : pio run -e <env> -t testeur_udp
Arret : Ctrl+C dans le terminal de la tache (ou la corbeille).
"""

import os
import subprocess
import tempfile

NOM_CIBLE = "testeur_udp"


def enregistre(env):
    racine = env.subst("$PROJECT_DIR")
    script = os.path.join(racine, "outils_docs", "scripts_python", "outils_pc", "testeur_udp.py")

    def lance_testeur(*args, **kwargs):
        port_maitre = str(env.GetProjectOption("custom_testeur_udp_port_maitre", "") or "")
        port_esclave = str(env.GetProjectOption("custom_testeur_udp_port_esclave", "") or "")
        http = str(env.GetProjectOption("custom_testeur_udp_http", "7400") or "7400")
        journal = os.path.join(tempfile.gettempdir(), "testeur_udp.log")
        commande = [env.subst("$PYTHONEXE"), "-u", script, "--http", http, "--journal", journal]
        if port_maitre:
            commande += ["--port-maitre", port_maitre]
        if port_esclave:
            commande += ["--port-esclave", port_esclave]
        print(f"testeur UDP -> http://127.0.0.1:{http}  (journal : {journal})")
        try:
            return subprocess.call(commande, env=dict(os.environ, PYTHONUTF8="1"))
        except KeyboardInterrupt:
            return 0

    # Cible demandee : lancer TOUT DE SUITE depuis ce script pre, puis quitter (sinon PlatformIO
    # prepare d'abord le build : plusieurs minutes avant le lancement), comme le sniffeur ModBus.
    from SCons.Script import COMMAND_LINE_TARGETS
    if NOM_CIBLE in COMMAND_LINE_TARGETS:
        env.Exit(lance_testeur())

    env.AddCustomTarget(
        name=NOM_CIBLE,
        dependencies=None,
        actions=[lance_testeur],
        title="Testeur UDP maitre/esclave (HTTP 127.0.0.1)",
        description="Ouvre les ports serie du maitre ModBus et d'un esclave, lit leurs logs et teste l'UDP "
                    "unicast / multicast dans les deux sens sur http://127.0.0.1:7400.",
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
