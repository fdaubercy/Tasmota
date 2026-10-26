"""Controle de la solidification Berry d'un `pio run`, des la fin du pre-build (page Build et televersement).

pio-tools/solidify-from-url.py (fichier de l'amont, non modifie) inscrit dans lib/libesp32/berry_custom/src/
modules.h tout module dont le source contient `module("X")`, mais le solidificateur Berry
(solidify_all_python.be, parse_file) n'ecrit dans solidify/solidified_<fichier>.h que les objets nommes par une
directive `#@ solidify:X`. Sans elle, le .h ne contient que son en-tete : la compilation va au bout et l'edition
des liens echoue sur `undefined reference to be_native_module_X`, une heure plus tard (cas reel du 2026-10-26 :
data/fs/demarrage.be). Ce module dit, en lisant les fichiers ecrits par le pre-build, quels modules ou classes
inscrits dans modules.h n'ont aucune definition solidifiee. Lecture seule ; aucun appel a pio.
"""

import re
from pathlib import Path

SOURCES = Path("lib") / "libesp32" / "berry_custom" / "src"
_INSCRIT = re.compile(r"be_extern_native_(module|class)\(\s*([A-Za-z_]\w*)\s*\)")
# Ce qu'ecrit solidify.dump : `be_define_const_native_module(X)` pour un module, `be_local_class(X,` pour une classe
_DEFINI = {"module": "be_define_const_native_module({})", "class": "be_local_class({},"}
GENRES = {"module": "module", "class": "classe"}


def _cause(sources, nom, genre):
    """Le source embarque qui declare `nom`, et s'il lui manque la directive `#@ solidify:<nom>`."""
    declaration = f'module("{nom}")' if genre == "module" else f"class {nom}"
    for be in sorted((sources / "embedded").glob("*.be")):
        texte = be.read_text(encoding="utf-8", errors="replace")
        if declaration not in texte.replace("'", '"'):
            continue
        if not re.search(rf"#@\s*solidify:{re.escape(nom)}\b", texte):
            return f"directive « #@ solidify:{nom} » absente de {be.name}"
        return f"{be.name} porte la directive mais rien n'a été solidifié (voir la sortie du pré-build)"
    return "aucune définition solidifiée (voir la sortie du pré-build)"


def vides(racine):
    """[{nom, genre, cause}] des modules et classes de modules.h sans definition dans solidify/*.h ; [] si rien."""
    sources = Path(racine) / SOURCES
    modules_h = sources / "modules.h"
    if not modules_h.is_file():
        return []
    inscrits = _INSCRIT.findall(modules_h.read_text(encoding="utf-8", errors="replace"))
    if not inscrits:
        return []
    solidifie = "".join(h.read_text(encoding="utf-8", errors="replace")
                        for h in sorted((sources / "solidify").glob("*.h")))
    return [{"nom": nom, "genre": GENRES[genre], "cause": _cause(sources, nom, genre)}
            for genre, nom in inscrits if _DEFINI[genre].format(nom) not in solidifie]


def motif(liste):
    """Motif d'echec de l'env : « solidification vide : X (cause) ; Y (cause) »."""
    return "solidification vide : " + " ; ".join(f"{v['nom']} ({v['cause']})" for v in liste)
