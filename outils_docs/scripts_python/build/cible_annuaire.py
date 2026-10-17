"""Cible PlatformIO « Annuaire des outils » : visible dans pioarduino > Project Tasks > <env> > Custom.

Enregistree comme la cible de la synchro du fork (cible_synchro_fork.py) :
  - ESP32 : importee par pre_utilitaires_platformio.py (extra_scripts des bases ESP32) ;
  - autre env : ce fichier en extra_script direct (pre:outils_docs/scripts_python/build/cible_annuaire.py),
    jamais les deux sur un meme env (cible declaree deux fois).
Lance outils_docs/scripts_python/outils_pc/annuaire_outils.py SANS --sans-navigateur : si l'annuaire tourne
deja (tache VS Code « Outil : annuaire des outils », demarree avec le dossier), il ouvre simplement sa page
et rend la main ; sinon il demarre et ouvre la page. L'env choisi n'a aucune importance.
    HTTP : custom_annuaire_http (optionnel, defaut 7600) -> http://127.0.0.1:7600

La cible quitte avant le reste du pre-script (pas de CFG_HOLDER, pas de platformio_override.ini) et avant
solidify-from-url.py (pas de modules.h).
ATTENTION : c'est un `pio run`. Ne JAMAIS la lancer pendant un build (le changement d'env peut faire
supprimer .pio/build) : lancer alors la tache VS Code « Outil : annuaire des outils » ou le script.
Un annuaire demarre par cette cible s'arrete avec elle (Ctrl+C ou corbeille du terminal), et les outils
qu'il a lances avec lui, sauf la synchro du fork.
En ligne de commande : pio run -e <env> -t annuaire
"""

import os
import subprocess

NOM_CIBLE = "annuaire"


def enregistre(env):
    racine = env.subst("$PROJECT_DIR")
    script = os.path.join(racine, "outils_docs", "scripts_python", "outils_pc", "annuaire_outils.py")

    def lance_annuaire(*args, **kwargs):
        http = str(env.GetProjectOption("custom_annuaire_http", "7600") or "7600")
        commande = [env.subst("$PYTHONEXE"), "-u", script, "--http", http]
        try:
            return subprocess.call(commande, cwd=racine, env=dict(os.environ, PYTHONUTF8="1"))
        except KeyboardInterrupt:
            return 0

    # Cible demandee : lancer TOUT DE SUITE depuis ce script pre, puis quitter (sinon PlatformIO
    # prepare d'abord le build : plusieurs minutes avant le lancement), comme la synchro du fork.
    from SCons.Script import COMMAND_LINE_TARGETS
    if NOM_CIBLE in COMMAND_LINE_TARGETS:
        env.Exit(lance_annuaire())

    env.AddCustomTarget(
        name=NOM_CIBLE,
        dependencies=None,
        actions=[lance_annuaire],
        title="Annuaire des outils (page web)",
        description="Page d'accueil des outils PC : lesquels tournent, ouvrir, lancer, arreter, aide ; "
                    "http://127.0.0.1:7600. Ouvre la page si l'annuaire tourne deja.",
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
