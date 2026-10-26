r"""Verifie les renvois au code des documents durables du depot (audit Berry P10.7, constats B12, B14, B19).

UTILISATION
-----------
  python verifie_references_docs.py              les documents durables (liste DURABLES ci-dessous)
  python verifie_references_docs.py f1.md ...    seulement ces documents
  python verifie_references_docs.py --externes   cherche aussi les fichiers hors depot (~/.platformio : paquets, PlatformIO)

  Code de sortie : 0 = tout renvoi est juste, 1 = au moins un defaut.
  Format : CLAUDE.md:42: ligne: modbusFonctions.be:1791 -> citer la fonction (fichier::fonction)

LA REGLE
--------
Un document durable renvoie au code par CHEMIN ou par `fichier::fonction`, jamais par numero de ligne :
un numero se decale a chaque modification du fichier, un nom reste juste tant que la fonction existe.
Les documents datés (audits, diagnostics, specs, ANALYSE_*) sont des traces : ils gardent leurs numeros.

CE QUI EST VERIFIE (hors blocs ``` de code)
-------------------------------------------
  ligne     `fichier.ext:N` ou `` `:N` `` : numero de ligne -> defaut
  chemin    `a/b/c.ext` entre accents graves : doit exister (racine du depot, ou fin d'un chemin suivi par git)
  fonction  `fichier::nom` : le fichier doit exister et DEFINIR nom (def, fonction C, cle .nom =, section,
            variable) ; pour un .ini/.json/.csv/.md, il suffit que nom y figure
Fichier hors depot (sources du framework, de lwIP...) : signale "hors depot, non verifie", sans defaut,
sauf avec --externes (recherche dans ~/.platformio/packages, lente : ~250 000 fichiers).
"""
import os
import re
import subprocess
import sys
from pathlib import Path

DURABLES = ["CLAUDE.md", "outils_docs/README.md", "outils_docs/SOLIDIFICATION_BERRY.md",
            "outils_docs/PROTOCOLE_MODBUS.md", "outils_docs/CARTE_MODULES_BERRY.md"]
DURABLES_MOTIFS = [".claude/skills/**/*.md", ".claude/agents/*.md", ".claude/commands/*.md"]
EXT = r"(?:be|py|ino|h|c|cpp|ini|json|csv|md|js|html|css|sh|ps1|mjs|txt)"
RE_LIGNE = re.compile(r"([\w./\\-]+\." + EXT + r"):(\d+(?:-\d+)?)\b")
RE_LIGNE_COURTE = re.compile(r"`:(\d+(?:-\d+)?)`")
RE_CODE = re.compile(r"`([^`\n]+)`")
RE_FONCTION = re.compile(r"^([\w./\\-]+\." + EXT + r")::([\w.\[\]:-]+)$")
RE_CHEMIN = re.compile(r"^[\w.-]+(?:/[\w.-]+)+\." + EXT + r"$")
# Un chemin cite qui commence par l'un de ces dossiers est un chemin du depot : absent = defaut
DOSSIERS_DEPOT = {"data", "outils_docs", "tasmota", "lib", "pio-tools", ".claude", ".vscode", "tasks", "docs",
                  "partitions", "boards"}
CODE_SOURCE = {".be", ".py", ".c", ".cpp", ".h", ".ino", ".js", ".mjs", ".sh", ".ps1"}
# Fichiers ecrits par un build puis retires (tasmota.ino.cpp de pioino, _temp_be_*.c de la solidification) :
# presents ou non selon le moment, jamais un defaut (classes « hors depot, non verifie »)
RE_GENERE = re.compile(r"\.ino\.cpp$|(^|/)_temp_be_[\w]*\.c$")


def racine_depot() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    sys.exit("ERREUR : racine du depot introuvable.")


class Index:
    """Fichiers suivis par git (et presents), recherches par chemin complet ou par fin de chemin."""

    def __init__(self, racine: Path, externes: bool):
        self.racine = racine
        sortie = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=str(racine),
                                capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
        self.chemins = [c for c in sortie.splitlines() if c]
        self.par_nom = {}
        for c in self.chemins:
            self.par_nom.setdefault(c.rsplit("/", 1)[-1], []).append(c)
        self.externes = None
        if externes:
            self.externes = {}
            # paquets (frameworks, toolchains, lwIP...) et PlatformIO lui-meme (platformio/run/helpers.py...)
            pio = Path.home() / ".platformio"
            for base in (pio / "packages", pio / "penv" / "Lib" / "site-packages" / "platformio"):
                for dossier, _, fichiers in os.walk(base):
                    for f in fichiers:
                        self.externes.setdefault(f, []).append(os.path.join(dossier, f))

    def trouve(self, cite: str):
        """Liste des fichiers (absolus) qui correspondent ; None si hors depot et non cherche."""
        cite = cite.replace("\\", "/")
        if cite.startswith("./"):
            cite = cite[2:]
        if cite.startswith("P/"):                       # abreviation des skills : P = outils_docs/scripts_python
            cite = "outils_docs/scripts_python/" + cite[2:]
        if (self.racine / cite).is_file():
            return [self.racine / cite]
        nom = cite.rsplit("/", 1)[-1]
        candidats = [self.racine / c for c in self.par_nom.get(nom, []) if c == cite or c.endswith("/" + cite)]
        if candidats:
            return candidats
        if RE_GENERE.search(cite):                      # genere par un build : absent hors build
            return None
        if cite.split("/", 1)[0] in DOSSIERS_DEPOT:     # chemin du depot qui n'existe pas : defaut
            return []
        if self.externes is not None:
            return [Path(c) for c in self.externes.get(nom, []) if c.replace("\\", "/").endswith(cite)]
        return None


def definit(fichier: Path, nom: str) -> bool:
    """Le fichier definit-il nom ? (code source : definition ; autres : simple presence)"""
    try:
        texte = fichier.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    court = nom.split(".")[-1]
    if fichier.suffix not in CODE_SOURCE:
        return nom in texte
    n = re.escape(court)
    motifs = [
        rf"\bdef\s+(?:\w+_)?{n}\s*\(",                 # Berry / Python : def nom( ou def module_nom(
        rf"\bclass\s+{n}\b",                            # classe
        rf"\.{n}\s*=",                                  # module.nom = ...
        rf"^\s*(?:var\s+)?{n}\s*=",                     # variable / constante
        rf"^[\w \t\*&:<>,]*\b{n}\s*\([^;]*$",           # fonction C/C++ (definition, pas un appel suivi de ;)
        rf"#\s*define\s+{n}\b",                         # macro
        rf"\bfunction\s+{n}\b|\b{n}\s*\(\)\s*\{{",      # JS / shell
    ]
    return any(re.search(m, texte, re.M) for m in motifs)


def blocs_hors_code(texte: str):
    """(numero de ligne, ligne) hors des blocs ``` ."""
    dans_code = False
    for i, ligne in enumerate(texte.splitlines(), 1):
        if ligne.lstrip().startswith("```"):
            dans_code = not dans_code
            continue
        if not dans_code:
            yield i, ligne


def verifie_document(doc: Path, racine: Path, index: Index):
    """(defauts, hors_depot) : listes de lignes 'doc:ligne: genre: message'."""
    rel = str(doc.relative_to(racine) if doc.is_relative_to(racine) else doc).replace("\\", "/")
    defauts, hors = [], []
    texte = doc.read_text(encoding="utf-8", errors="replace")
    for num, ligne in blocs_hors_code(texte):
        for m in RE_LIGNE.finditer(ligne):
            defauts.append(f"{rel}:{num}: ligne: {m.group(0)} -> citer la fonction (fichier::fonction)")
        for m in RE_LIGNE_COURTE.finditer(ligne):
            defauts.append(f"{rel}:{num}: ligne: {m.group(0)} -> citer la fonction (fichier::fonction)")
        for m in RE_CODE.finditer(ligne):
            cite = m.group(1).strip()
            f = RE_FONCTION.match(cite)
            if f:
                trouves = index.trouve(f.group(1))
                if trouves is None:
                    hors.append(f"{rel}:{num}: hors depot, non verifie: {cite}")
                elif not trouves:
                    defauts.append(f"{rel}:{num}: chemin: {f.group(1)} introuvable")
                elif not any(definit(t, f.group(2)) for t in trouves):
                    defauts.append(f"{rel}:{num}: fonction: {f.group(2)} non definie dans {f.group(1)}")
            elif RE_CHEMIN.match(cite) and not any(c in cite for c in "*<>{}$%~"):
                trouves = index.trouve(cite)
                if trouves is None:
                    hors.append(f"{rel}:{num}: hors depot, non verifie: {cite}")
                elif not trouves:
                    defauts.append(f"{rel}:{num}: chemin: {cite} introuvable")
    return defauts, hors


def documents(racine: Path, args):
    if args:
        return [(racine / a) if not Path(a).is_absolute() else Path(a) for a in args]
    docs = [racine / d for d in DURABLES]
    for motif in DURABLES_MOTIFS:
        docs += sorted(racine.glob(motif))
    return [d for d in docs if d.is_file()]


def main() -> int:
    sys.stdout.reconfigure(errors="replace")
    args = sys.argv[1:]
    if args in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    externes = "--externes" in args
    args = [a for a in args if a != "--externes"]
    racine = racine_depot()
    index = Index(racine, externes)
    tous_defauts, tous_hors = [], []
    docs = documents(racine, args)
    for doc in docs:
        d, h = verifie_document(doc, racine, index)
        tous_defauts += d
        tous_hors += h
    for l in tous_defauts + tous_hors:
        print(l)
    print(f"{len(docs)} document(s), {len(tous_defauts)} defaut(s), {len(tous_hors)} renvoi(s) hors depot non verifie(s).")
    return 1 if tous_defauts else 0


if __name__ == "__main__":
    sys.exit(main())
