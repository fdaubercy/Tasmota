"""Cible PlatformIO « Synchro du fork » : visible dans pioarduino > Project Tasks > <env> > Custom.

Enregistree comme la cible du testeur UDP (cible_testeur_udp.py) :
  - ESP32 : importee par pre_utilitaires_platformio.py (extra_scripts des bases ESP32) ;
  - autre env : ce fichier en extra_script direct (pre:outils_docs/scripts_python/build/cible_synchro_fork.py),
    jamais les deux sur un meme env (cible declaree deux fois).
Lance outils_docs/scripts_python/maintenance/synchro_fork_web.py : page de la synchro du fork (merge et
rebase), lien affiche dans la console et ouvert dans le navigateur. L'env choisi n'a aucune importance.
    HTTP : custom_synchro_fork_http (optionnel, defaut 7500) -> http://127.0.0.1:7500

La cible quitte avant le reste du pre-script (pas de CFG_HOLDER, pas de platformio_override.ini) et avant
solidify-from-url.py (pas de modules.h) : elle ne salit pas l'arbre de travail que la synchro exige propre.
ATTENTION : c'est un `pio run`. Ne JAMAIS la lancer pendant un build (le changement d'env peut faire
supprimer .pio/build) : lancer alors la tache VS Code « Outil : synchro du fork » ou le script.
En ligne de commande : pio run -e <env> -t synchro_fork
Arret : Ctrl+C dans le terminal de la tache (ou la corbeille).
"""

import os
import subprocess

NOM_CIBLE = "synchro_fork"


def enregistre(env):
    racine = env.subst("$PROJECT_DIR")
    script = os.path.join(racine, "outils_docs", "scripts_python", "maintenance", "synchro_fork_web.py")

    def lance_synchro(*args, **kwargs):
        http = str(env.GetProjectOption("custom_synchro_fork_http", "7500") or "7500")
        commande = [env.subst("$PYTHONEXE"), "-u", script, "--http", http]
        try:
            return subprocess.call(commande, cwd=racine, env=dict(os.environ, PYTHONUTF8="1"))
        except KeyboardInterrupt:
            return 0

    # Cible demandee : lancer TOUT DE SUITE depuis ce script pre, puis quitter (sinon PlatformIO
    # prepare d'abord le build : plusieurs minutes avant le lancement), comme le testeur UDP.
    from SCons.Script import COMMAND_LINE_TARGETS
    if NOM_CIBLE in COMMAND_LINE_TARGETS:
        env.Exit(lance_synchro())

    env.AddCustomTarget(
        name=NOM_CIBLE,
        dependencies=None,
        actions=[lance_synchro],
        title="Synchro du fork (page web)",
        description="Page de la synchro du fork Tasmota avec l'amont (merge ou rebase) : etat, nouveautes, "
                    "conflits, push, journal ; http://127.0.0.1:7500, et depuis le reseau par le lien a jeton.",
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
