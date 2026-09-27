"""Cible PlatformIO « Pont serie » : visible dans pioarduino > Project Tasks > <env> > Custom.

Enregistree par pre_utilitaires_platformio.py (extra_scripts des bases ESP32). Lance
outils_docs/scripts_python/pont_serie.py avec les parametres DE L'ENVIRONNEMENT choisi :
    port    : monitor_port, sinon upload_port (s'il designe un port serie), sinon "auto"
    debit   : monitor_speed (defaut 115200)
    TCP     : custom_pont_tcp (optionnel, defaut 7000) -> http://127.0.0.1:7000 et Serial Monitor (TCP)
    journal : %TEMP%/pont_serie_<env>.log

En ligne de commande : pio run -e <env> -t pont_serie
Arret : Ctrl+C dans le terminal de la tache (ou la corbeille). L'ARRETER AVANT UN FLASH.
"""

import os
import re
import subprocess
import tempfile

NOM_CIBLE = "pont_serie"


def _port_serie(env):
    """monitor_port, sinon upload_port s'il ressemble a un port serie (pas une URL OTA), sinon 'auto'."""
    for option in ("monitor_port", "upload_port"):
        valeur = (env.GetProjectOption(option, "") or "").strip()
        if valeur and re.match(r"^(COM\d+|/dev/\S+|rfc2217://|socket://|loop://)", valeur, re.IGNORECASE):
            return valeur
    return "auto"


def enregistre(env):
    racine = env.subst("$PROJECT_DIR")
    nom_env = env.subst("$PIOENV")
    script = os.path.join(racine, "outils_docs", "scripts_python", "pont_serie.py")

    def lance_pont(*args, **kwargs):
        port = _port_serie(env)
        debit = str(env.GetProjectOption("monitor_speed", "115200") or "115200")
        tcp = str(env.GetProjectOption("custom_pont_tcp", "7000") or "7000")
        journal = os.path.join(tempfile.gettempdir(), f"pont_serie_{nom_env}.log")
        commande = [env.subst("$PYTHONEXE"), script, "--port", port, "--vitesse", debit,
                    "--tcp", tcp, "--journal", journal]
        print(f"[{nom_env}] pont serie : port={port} debit={debit} -> http://127.0.0.1:{tcp}  (journal : {journal})")
        environnement = dict(os.environ, PYTHONUTF8="1")
        try:
            return subprocess.call(commande, env=environnement)
        except KeyboardInterrupt:
            return 0

    env.AddCustomTarget(
        name=NOM_CIBLE,
        dependencies=None,
        actions=[lance_pont],
        title="Pont serie (TCP/HTTP 127.0.0.1)",
        description="Logs colores du port de l'env (monitor_port, monitor_speed) sur http://127.0.0.1:7000 "
                    "et Serial Monitor (TCP). Ctrl+C pour arreter ; l'arreter avant un flash.",
        always_build=True,
    )
