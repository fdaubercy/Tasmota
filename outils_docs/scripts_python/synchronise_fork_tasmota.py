# -*- coding: utf-8 -*-
r"""
=============================================================================
  synchronise_fork_tasmota.py  -  Synchronisation du fork (merge, a distance)
=============================================================================

UTILISATION
-----------
  python synchronise_fork_tasmota.py [options]

OPTIONS
-------
  --dry-run   Diagnostic seul : dit ou en est le fork, ne modifie RIEN.
  -h | --help Affiche ce message d'aide et quitte.

DESCRIPTION
-----------
  Reproduit, en ligne de commande, les deux boutons que l'on clique a la main :

    1. Le bouton « Sync fork » de GitHub   -> synchronise le fork EN LIGNE
    2. Le bouton « Sync » de VS Code       -> synchronise le depot LOCAL

  Deroule :
    1. Diagnostic (lecture seule)  : combien de commits d'avance / de retard.
    2. Synchro DISTANTE du fork    : API merge-upstream (le bouton « Sync fork »).
    3. Les nouveautes              : resume dans le terminal + trace dans
                                     outils_docs/HISTORIQUE_SYNCHRO_FORK.md.
    4. Synchro LOCALE              : fetch + merge + push (le bouton de VS Code).

STRATEGIE : MERGE, PAS REBASE
-----------------------------
  Ce script fait du **merge**, comme le bouton « Sync fork » de GitHub (dont
  l'historique porte deja la trace : « Merge branch 'arendst:development' »).
  Consequence : aucun commit deja publie n'est reecrit, et un `git push --force`
  n'est JAMAIS necessaire.

  Pour un historique **lineaire** (rebase), utiliser l'autre script :
  `synchronise_upstream_tasmota.py`. Il sait aussi resoudre les conflits en
  interactif, ce que celui-ci ne fait pas.

  Ne PAS melanger les deux strategies au fil du temps : c'est ce qui fait
  diverger un fork.

GARDE-FOUS
----------
  - Arbre de travail sale  -> arret AVANT l'etape 4 (le fork distant, lui, est
                              deja synchronise : rien n'est perdu).
  - Conflit de merge       -> abort + rapport. Aucune resolution automatique.
  - Push                   -> demande confirmation (regle du depot).
  - Jamais de --force, jamais de stash.

PREREQUIS
---------
  - Les remotes « origin » (le fork) et « upstream » (arendst/Tasmota).
  - Le CLI GitHub `gh`, authentifie :  gh auth login
=============================================================================
"""
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# La sortie de ce script peut etre redirigee vers un fichier ; sous Windows,
# Python passerait alors en cp1252 et le moindre caractere hors cp1252 leverait
# UnicodeEncodeError. On force l'utf-8 avec errors="replace" : la sortie ne peut
# plus faire tomber le script.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace", line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8",
                              errors="replace", line_buffering=True)


# ── Localisation du depot ─────────────────────────────────────────────────────

def find_git_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    print("ERREUR : impossible de trouver la racine du depot git.")
    sys.exit(1)


REPO = find_git_root()

# Journal des synchros, versionne (decide le 2026-07-15).
# ATTENTION : ce fichier est ECRIT par ce script a l'etape 3, donc AVANT le
# controle d'arbre sale de l'etape 4. Comme il est suivi par git, il faut
# l'exclure de ce controle (cf. arbre_sale()) — sinon le script se bloquerait
# lui-meme a chaque execution, sur une salissure qu'il vient de causer.
# La CASSE de ce nom doit correspondre exactement a celle du disque : arbre_sale()
# compare la chaine renvoyee par `git status --porcelain` a HISTORIQUE_REL. Windows
# ouvrirait le fichier quelle que soit la casse, mais la comparaison, elle, echouerait
# en silence — et le script se bloquerait sur le journal qu'il vient d'ecrire.
HISTORIQUE = REPO / "outils_docs" / "HISTORIQUE_SYNCHRO_FORK.md"
HISTORIQUE_REL = "outils_docs/HISTORIQUE_SYNCHRO_FORK.md"

EN_TETE_HISTORIQUE = """# Historique des synchronisations du fork

Genere automatiquement par `outils_docs/scripts_python/synchronise_fork_tasmota.py`
a chaque synchronisation reussie du fork avec upstream (arendst/Tasmota).

Append uniquement — ne jamais supprimer d'entree existante.
Les commits marques ● ont un titre qui mentionne Berry / ESP32-S3 / nos sujets.

---
"""


# ── Couleurs ──────────────────────────────────────────────────────────────────

def _enable_ansi() -> bool:
    if os.name != "nt":
        return sys.stdout.isatty()
    try:
        import ctypes
        k = ctypes.windll.kernel32
        # 7 = ENABLE_VIRTUAL_TERMINAL_PROCESSING | sorties standard deja actives
        k.SetConsoleMode(k.GetStdHandle(-11), 7)
        return True
    except Exception:
        return False


ANSI = _enable_ansi()


def _c(code: str) -> str:
    return code if ANSI else ""


VERT = _c("\033[32m")
JAUNE = _c("\033[33m")
ROUGE = _c("\033[31m")
CYAN = _c("\033[36m")
GRIS = _c("\033[90m")
GRAS = _c("\033[1m")
RAZ = _c("\033[0m")


def section(titre: str, etape: int = 0, total: int = 0, largeur: int = 68):
    prefixe = f"[{etape}/{total}] " if total else ""
    print(f"\n{CYAN}{GRAS}{'─' * largeur}{RAZ}")
    print(f"{CYAN}{GRAS}  {prefixe}{titre}{RAZ}")
    print(f"{CYAN}{GRAS}{'─' * largeur}{RAZ}")


# ── Commandes externes ────────────────────────────────────────────────────────

def git_out(*args) -> str:
    """Sortie d'une commande git, chaine vide si echec."""
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip() if r.returncode == 0 else ""


def git_run(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def gh_api(chemin: str, methode: str = "GET", champs: dict | None = None):
    """Appelle l'API GitHub via `gh`. Retourne (ok, donnees_ou_message)."""
    cmd = ["gh", "api", "-X", methode, chemin]
    for k, v in (champs or {}).items():
        cmd += ["-f", f"{k}={v}"]
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    brut = (r.stdout or "") + (r.stderr or "")
    try:
        donnees = json.loads(r.stdout)
    except (json.JSONDecodeError, TypeError):
        donnees = None
    if r.returncode != 0:
        # gh renvoie souvent un JSON d'erreur avec un champ "message"
        msg = donnees.get("message") if isinstance(donnees, dict) else None
        return False, (msg or brut.strip() or f"gh a echoue (code {r.returncode})")
    return True, donnees


# ── Prerequis ─────────────────────────────────────────────────────────────────

def slug_depuis_remote(remote: str) -> str | None:
    """'https://github.com/fdaubercy/Tasmota.git' -> 'fdaubercy/Tasmota'."""
    url = git_out("remote", "get-url", remote)
    if not url:
        return None
    m = re.search(r"github\.com[:/]+([^/]+/[^/]+?)(?:\.git)?$", url)
    return m.group(1) if m else None


def verifier_prerequis() -> tuple[str, str, str]:
    """Retourne (slug_origin, slug_upstream, branche). Sort en erreur sinon."""
    if not shutil.which("gh"):
        print(f"{ROUGE}ERREUR : le CLI GitHub `gh` est introuvable.{RAZ}")
        print("  La synchro DISTANTE du fork passe par l'API GitHub et l'exige.")
        print("  Installation : https://cli.github.com/  puis  gh auth login")
        sys.exit(1)

    r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(f"{ROUGE}ERREUR : `gh` n'est pas authentifie.{RAZ}")
        print("  Lancer :  gh auth login")
        sys.exit(1)

    origin = slug_depuis_remote("origin")
    upstream = slug_depuis_remote("upstream")
    if not origin or not upstream:
        print(f"{ROUGE}ERREUR : remotes 'origin' et/ou 'upstream' introuvables.{RAZ}")
        print("  Attendu :  origin   = ton fork      (ex. fdaubercy/Tasmota)")
        print("             upstream = le vrai depot (ex. arendst/Tasmota)")
        print("  A poser :  git remote add upstream https://github.com/arendst/Tasmota.git")
        sys.exit(1)

    branche = git_out("rev-parse", "--abbrev-ref", "HEAD")
    if not branche or branche == "HEAD":
        print(f"{ROUGE}ERREUR : branche courante indeterminee (HEAD detachee ?).{RAZ}")
        sys.exit(1)

    return origin, upstream, branche


# ── Etape 1 : diagnostic ──────────────────────────────────────────────────────

def diagnostic(origin: str, upstream: str, branche: str):
    """Retourne (ok, en_avance, en_retard, commits_upstream)."""
    prop_upstream = upstream.split("/")[0]
    prop_origin = origin.split("/")[0]

    # base = upstream, head = le fork -> ahead_by / behind_by du point de vue du fork,
    # exactement les chiffres qu'affiche la page GitHub du fork.
    ok, d = gh_api(f"repos/{upstream}/compare/{branche}...{prop_origin}:{branche}")
    if not ok:
        print(f"{ROUGE}ERREUR : comparaison impossible : {d}{RAZ}")
        return False, 0, 0, []

    en_avance = d.get("ahead_by", 0)
    en_retard = d.get("behind_by", 0)

    # Les nouveautes = les commits d'upstream absents du fork : comparaison inverse.
    commits = []
    if en_retard:
        ok2, d2 = gh_api(f"repos/{origin}/compare/{branche}...{prop_upstream}:{branche}")
        if ok2:
            commits = d2.get("commits", [])

    print(f"  fork      : {GRAS}{origin}{RAZ}  (branche {branche})")
    print(f"  upstream  : {GRAS}{upstream}{RAZ}")
    print()
    coul_r = JAUNE if en_retard else VERT
    print(f"  {GRAS}Le fork EN LIGNE{RAZ}  {GRIS}(ce qu'affiche la page GitHub){RAZ}")
    print(f"    {en_avance} commit(s) d'avance   {GRIS}(a toi, absents d'upstream){RAZ}")
    print(f"    {coul_r}{en_retard} commit(s) de retard{RAZ}   {GRIS}(d'upstream, absents du fork){RAZ}")

    # Le local peut etre en avance sur le fork : sans cette ligne, l'ecart entre
    # le chiffre affiche par GitHub et la realite du disque est incomprehensible.
    non_pousses = git_out("rev-list", "--count", f"origin/{branche}..HEAD")
    if non_pousses and non_pousses != "0":
        print(f"\n  {GRAS}Ton depot LOCAL{RAZ}")
        print(f"    {JAUNE}{non_pousses} commit(s) non pousse(s){RAZ} vers ton fork "
              f"{GRIS}(d'ou l'ecart avec le chiffre ci-dessus){RAZ}")
    return True, en_avance, en_retard, commits


# ── Etape 3 : les nouveautes ──────────────────────────────────────────────────

# Ce qui merite d'etre signale dans une liste de commits amont.
# Heuristique volontairement simple : elle ne lit que le TITRE du commit, pas les
# fichiers touches (il faudrait un appel API par commit). Elle rate donc des
# choses — c'est une aide a la lecture, pas un filtre de confiance.
# `haspmota`, `matter`, `lvgl` sont inclus : ce sont des modules Berry a part
# entiere (lv_haspmota, berry_matter, lv_binding_berry sont dans SOLIDIFY_DIRS).
MOTS_SAILLANTS = [
    "berry", "haspmota", "matter", "lvgl", "solidif",
    "esp32-s3", "esp32s3", "modbus", "udp",
    "littlefs", "psram", "memory", "heap", "security", "breaking",
]


def analyser_commits(commits: list) -> list[tuple[str, str, list[str]]]:
    """-> [(sha_court, titre, mots_saillants_touches)], dans l'ordre d'arrivee."""
    analyses = []
    for c in commits:
        titre = (c.get("commit", {}).get("message") or "").split("\n")[0]
        sha = (c.get("sha") or "")[:9]
        bas = titre.lower()
        analyses.append((sha, titre, [m for m in MOTS_SAILLANTS if m in bas]))
    return analyses


def afficher_nouveautes(analyses: list):
    if not analyses:
        print(f"  {GRIS}(aucune){RAZ}")
        return

    nb_saillants = 0
    for sha, titre, touche in analyses:
        if touche:
            nb_saillants += 1
            print(f"  {JAUNE}●{RAZ} {GRIS}{sha}{RAZ} {GRAS}{titre}{RAZ}")
        else:
            print(f"    {GRIS}{sha}{RAZ} {titre}")

    print()
    if nb_saillants:
        print(f"  {JAUNE}{GRAS}{nb_saillants} commit(s) marque(s) ●{RAZ} : leur titre "
              f"mentionne Berry / ESP32-S3 / tes sujets.")
    else:
        print(f"  {GRIS}Aucun titre de commit ne mentionne tes sujets.{RAZ}")
    print(f"  {GRIS}Reperage sur le titre seul : il rate ce qui n'est pas nomme. "
          f"En cas de doute, lire CHANGELOG.md.{RAZ}")


def noter_historique(analyses: list, origin: str, upstream: str,
                     branche: str, type_merge: str):
    """Ajoute une entree au journal des synchros. Append uniquement."""
    if not analyses:
        return

    HISTORIQUE.parent.mkdir(parents=True, exist_ok=True)
    neuf = not HISTORIQUE.exists()

    horodatage = datetime.now().strftime("%Y-%m-%d %H:%M")
    nb_saillants = sum(1 for _, _, t in analyses if t)

    lignes = [
        f"\n## {horodatage} — {len(analyses)} commit(s) recupere(s) d'upstream\n",
        f"\n`{upstream}:{branche}` → `{origin}:{branche}` (merge_type : {type_merge})\n",
    ]
    if nb_saillants:
        lignes.append(f"\n**{nb_saillants} commit(s) ● a lire de pres.**\n")
    lignes.append("\n")
    for sha, titre, touche in analyses:
        marque = "● " if touche else "  "
        # Les titres amont contiennent des backticks : on les neutralise pour ne
        # pas casser le rendu Markdown du journal.
        titre_md = titre.replace("|", "\\|")
        lignes.append(f"- {marque}`{sha}` {titre_md}\n")

    try:
        with io.open(HISTORIQUE, "a", encoding="utf-8") as f:
            if neuf:
                f.write(EN_TETE_HISTORIQUE)
            f.writelines(lignes)
    except OSError as e:
        # Le journal est un confort, pas la mission : on ne fait pas echouer une
        # synchro reussie pour une erreur d'ecriture de fichier.
        print(f"  {JAUNE}[!] journal non ecrit : {e}{RAZ}")
        return

    print(f"\n  {VERT}✔ note dans{RAZ} {HISTORIQUE_REL}")


# ── Etape 4 : synchro locale ──────────────────────────────────────────────────

def arbre_sale() -> list[str]:
    """Fichiers suivis et modifies, hors journal ecrit par ce script lui-meme.

    L'exclusion du journal n'est pas un detail : il est suivi par git et ce script
    vient de le remplir a l'etape 3. Sans cette exclusion, le script refuserait sa
    propre etape 4 a cause d'une salissure qu'il a causee — a chaque execution.
    """
    sortie = git_out("status", "--porcelain")
    sales = []
    for l in sortie.split("\n"):
        if not l.strip() or l.startswith("??"):
            continue
        if l[3:].strip().strip('"') == HISTORIQUE_REL:
            continue
        sales.append(l)
    return sales


def synchro_locale(origin: str, branche: str) -> bool:
    sales = arbre_sale()
    if sales:
        print(f"  {JAUNE}{GRAS}ARRET : {len(sales)} fichier(s) modifie(s) non commite(s).{RAZ}")
        for l in sales[:15]:
            print(f"    {l}")
        if len(sales) > 15:
            print(f"    {GRIS}... et {len(sales) - 15} autre(s){RAZ}")
        print()
        print(f"  {GRAS}Ton fork EN LIGNE est deja synchronise{RAZ} — rien n'est perdu.")
        print("  Seule la mise a jour de ton depot local est reportee.")
        print()
        print("  Pour la faire, au choix :")
        print(f"    - commiter ton travail, puis relancer ce script")
        print(f"    - ou :  git stash  ->  relancer  ->  git stash pop")
        return False

    print("  fetch origin ...")
    if git_run("fetch", "origin").returncode != 0:
        print(f"  {ROUGE}ERREUR : git fetch a echoue.{RAZ}")
        return False

    retard_local = git_out("rev-list", "--count", f"HEAD..origin/{branche}")
    if retard_local and retard_local != "0":
        print(f"  merge origin/{branche} ({retard_local} commit(s)) ...")
        r = git_run("merge", f"origin/{branche}")
        if r.returncode != 0:
            print(f"  {ROUGE}{GRAS}CONFLIT DE MERGE.{RAZ}")
            print(f"  {(r.stdout + r.stderr).strip()[:500]}")
            conflits = git_out("diff", "--name-only", "--diff-filter=U")
            if conflits:
                print(f"\n  Fichiers en conflit :")
                for f in conflits.split("\n"):
                    print(f"    {f}")
            print(f"\n  {GRAS}Le merge est annule{RAZ} (git merge --abort) : ton depot est intact.")
            git_run("merge", "--abort")
            print("  Ce script ne resout pas les conflits. Pour une resolution guidee :")
            print(f"    python {Path(__file__).parent / 'synchronise_upstream_tasmota.py'}")
            print(f"  {GRIS}(attention : celui-la fait du REBASE, pas du merge){RAZ}")
            return False
        print(f"  {VERT}✔ merge reussi{RAZ}")
    else:
        print(f"  {GRIS}deja a jour vis-a-vis d'origin{RAZ}")

    avance_local = git_out("rev-list", "--count", f"origin/{branche}..HEAD")
    if avance_local and avance_local != "0":
        print()
        print(f"  {avance_local} commit(s) local(aux) a pousser vers origin :")
        for l in (git_out("log", "--oneline", f"origin/{branche}..HEAD") or "").split("\n"):
            if l:
                print(f"    {l}")
        print()
        rep = input(f"  {GRAS}Pousser vers origin/{branche} ? [o/N] {RAZ}").strip().lower()
        if rep in ("o", "oui", "y", "yes"):
            r = git_run("push", "origin", branche)
            if r.returncode == 0:
                print(f"  {VERT}✔ pousse{RAZ}")
            else:
                print(f"  {ROUGE}ERREUR : push refuse.{RAZ}")
                print(f"  {(r.stdout + r.stderr).strip()[:400]}")
                return False
        else:
            print(f"  {GRIS}push ignore — tes commits restent locaux.{RAZ}")
    else:
        print(f"  {GRIS}rien a pousser{RAZ}")

    return True


# ── Programme principal ───────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="Synchronise le fork Tasmota (merge) : a distance puis en local.",
        add_help=False,
    )
    p.add_argument("--dry-run", action="store_true",
                   help="Diagnostic seul : ne modifie rien.")
    p.add_argument("-h", "--help", action="store_true")
    a = p.parse_args()

    if a.help:
        print(__doc__)
        sys.exit(0)

    origin, upstream, branche = verifier_prerequis()
    total = 2 if a.dry_run else 4

    section("Diagnostic du fork", 1, total)
    ok, en_avance, en_retard, commits = diagnostic(origin, upstream, branche)
    if not ok:
        sys.exit(1)

    analyses = analyser_commits(commits)

    if a.dry_run:
        section("Nouveautes upstream (non appliquees : --dry-run)", 2, total)
        afficher_nouveautes(analyses)
        # Pas de trace au journal : --dry-run promet de ne RIEN modifier.
        print(f"\n{GRIS}--dry-run : rien n'a ete modifie "
              f"(ni le fork, ni le depot local, ni le journal).{RAZ}")
        sys.exit(0)

    if not en_retard:
        print(f"\n{VERT}{GRAS}Le fork est a jour avec upstream — rien a synchroniser.{RAZ}")
        section("Synchro locale (« Sync » de VS Code)", 2, 2)
        synchro_locale(origin, branche)
        sys.exit(0)

    section("Synchro distante du fork (« Sync fork » de GitHub)", 2, total)
    ok, d = gh_api(f"repos/{origin}/merge-upstream", "POST", {"branch": branche})
    if not ok:
        print(f"  {ROUGE}{GRAS}ECHEC de la synchro distante.{RAZ}")
        print(f"  {d}")
        print()
        print("  Cause probable : les modifications d'upstream entrent en conflit")
        print("  avec les commits de ton fork. GitHub ne resout pas ca tout seul.")
        print("  Resolution guidee (attention : REBASE, pas merge) :")
        print(f"    python {Path(__file__).parent / 'synchronise_upstream_tasmota.py'}")
        sys.exit(1)

    type_merge = d.get("merge_type", "?") if isinstance(d, dict) else "?"
    message = d.get("message", "") if isinstance(d, dict) else ""
    print(f"  {VERT}✔ fork synchronise en ligne{RAZ}  {GRIS}(merge_type: {type_merge}){RAZ}")
    if message:
        print(f"  {GRIS}{message}{RAZ}")

    section(f"Nouveautes recuperees d'upstream ({en_retard})", 3, total)
    afficher_nouveautes(analyses)
    noter_historique(analyses, origin, upstream, branche, type_merge)

    section("Synchro locale (« Sync » de VS Code)", 4, total)
    ok_local = synchro_locale(origin, branche)

    print()
    if ok_local:
        print(f"{VERT}{GRAS}Termine : fork et depot local synchronises.{RAZ}")
    else:
        print(f"{JAUNE}{GRAS}Termine partiellement : le fork EN LIGNE est a jour, "
              f"le local non (voir ci-dessus).{RAZ}")

    # Le journal est suivi par git : il attend un commit, et ce script n'en fait
    # jamais (regle du depot : pas de commit sans demande explicite).
    if analyses and git_out("status", "--porcelain", HISTORIQUE_REL):
        print(f"\n{GRIS}Le journal {HISTORIQUE_REL} a ete complete et attend un commit :{RAZ}")
        print(f"{GRIS}  git add {HISTORIQUE_REL} && git commit -m \"docs: synchro du fork\"{RAZ}")


if __name__ == "__main__":
    main()
