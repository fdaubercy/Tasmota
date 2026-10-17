"""Questions posees par les scripts de synchro du fork (synchronise_fork_tasmota.py,
synchronise_upstream_tasmota.py), au terminal ou a la page web synchro_fork_web.py.

Au terminal : input(), comme avant. Lances par la page (variable SYNCHRO_FORK_WEB=1), la question
part sur une ligne balisee MARQUE + JSON, que la page transforme en boutons ; la reponse revient par
l'entree standard, puis la ligne question + reponse est recopiee dans la sortie (le terminal l'aurait
affichee en echo).

Entree standard fermee (hors terminal, page arretee) : reponse `eof`, toujours la plus prudente
(ne pas pousser, ne pas synchroniser, annuler le rebase).
"""

import json
import os
import re
import sys

MARQUE = "@@QUESTION@@ "
VARIABLE = "SYNCHRO_FORK_WEB"
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def demander(question, choix, eof="", confirme=None):
    """question : invite du terminal ; choix : [(valeur, libelle), ...] pour les boutons de la page ;
    eof : reponse si l'entree standard est fermee ; confirme : texte a saisir dans la page avant que
    le PREMIER choix s'active (push force : le nom de la branche)."""
    if os.environ.get(VARIABLE) != "1":
        try:
            return input(question)
        except EOFError:
            return eof
    donnees = {"question": _ANSI.sub("", question).strip(), "choix": [list(c) for c in choix],
               "confirme": confirme}
    print(MARQUE + json.dumps(donnees, ensure_ascii=False), flush=True)
    ligne = sys.stdin.readline()
    if not ligne:
        return eof
    reponse = ligne.rstrip("\r\n")
    print(f"{question}{reponse}", flush=True)
    return reponse
