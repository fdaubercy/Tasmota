"""Hook PostToolUse : compile un .be de data/ juste apres son edition par Claude.

Lance outils_docs/scripts_python/berry/verifie_berry.py sur le seul fichier edite (~0,8 s) :
memes globales declarees que le solidifieur du build, code jamais execute.

- fichier hors data/, ou dans un dossier *sauvegarde* : rien ;
- compile : rien (code 0, silencieux) ;
- erreur Berry : code 2, l'erreur (fichier:ligne: erreur: ...) part sur stderr, que Claude lit
  aussitot (l'edition est deja faite : il doit la corriger) ;
- verification impossible (berry.exe absent, temoin rate, delai) : code 2 aussi, avec le motif,
  pour qu'une verification muette ne passe jamais pour un succes ;
- compile mais s'ecarte de la charte des logs (avertissements de verifie_berry.py, audit P7.6) :
  code 0, les avertissements reviennent a Claude en contexte (additionalContext), sans bloquer.

La tache VS Code « --surveille » fait la meme chose pour les editions de l'utilisateur, mais ses
erreurs vont dans l'onglet Problemes, que Claude ne voit pas.
"""
import json
import os
import subprocess
import sys

DEPOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
VERIFIE = os.path.join(DEPOT, "outils_docs", "scripts_python", "berry", "verifie_berry.py")


def fichier_vise(entree):
    outil = entree.get("tool_input") or {}
    chemin = outil.get("file_path") or ""
    if not chemin.lower().endswith(".be"):
        return None
    absolu = os.path.normcase(os.path.abspath(chemin))
    data = os.path.normcase(os.path.join(os.path.abspath(DEPOT), "data")) + os.sep
    if not absolu.startswith(data) or "sauvegarde" in absolu:
        return None
    return chemin


def main():
    try:
        entree = json.load(sys.stdin)
    except ValueError:
        return 0
    chemin = fichier_vise(entree)
    if not chemin or not os.path.isfile(chemin):
        return 0
    try:
        r = subprocess.run([sys.executable, "-I", VERIFIE, chemin], cwd=DEPOT,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=25)
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"Verification Berry impossible pour {chemin} : {e}", file=sys.stderr)
        return 2
    if r.returncode == 0:
        avis = [l for l in r.stdout.splitlines() if ": avertissement: " in l]
        if avis:
            texte = ("Charte des logs (data/fs/logFonctions.be) : ecarts dans le fichier que tu viens d'editer, "
                     "a corriger s'ils viennent de ton edition :\n" + "\n".join(avis))
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": texte}}))
        return 0
    sortie = (r.stdout + r.stderr).strip()
    if r.returncode == 1:
        print(f"Erreur Berry dans le fichier que tu viens d'editer, a corriger :\n{sortie}",
              file=sys.stderr)
    else:
        print(f"Verification Berry invalide (code {r.returncode}) pour {chemin} :\n{sortie}",
              file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
