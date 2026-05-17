# -*- coding: utf-8 -*-
r"""
=============================================================================
  synchronise_upstream_tasmota.py  -  Synchronisation du fork avec upstream
=============================================================================

UTILISATION
-----------
  python synchronise_upstream_tasmota.py [options]

OPTIONS
-------
  --dry-run   Montre les conflits potentiels sans modifier les fichiers.
  -h | --help Affiche ce message d'aide et quitte.

DESCRIPTION
-----------
  1. Fait git fetch upstream pour mettre a jour les references distantes.
  2. Lance git rebase upstream/development sur votre branche locale.
  3. Pour chaque conflit detecte :
       Fichier binaire  -> votre version conservee automatiquement.
       Fichier texte    -> affiche les deux versions et demande :
           [M] Garder le mien
           [U] Prendre upstream
           [E] Editer dans VS Code (attend la fermeture du fichier)
           [Q] Annuler le rebase (git rebase --abort)
  4. Propose de pousser vers origin apres un rebase reussi.

PREREQUIS
---------
  Le remote "upstream" doit etre configure :
    git remote add upstream https://github.com/arendst/Tasmota.git
=============================================================================
"""
import subprocess, sys, os, time, argparse
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
from pathlib import Path
from datetime import datetime

# ── Localisation du repo ──────────────────────────────────────────────────────

def find_git_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / '.git').exists():
            return p
        p = p.parent
    raise RuntimeError("Dossier .git introuvable — placez le script dans le repo Tasmota")

REPO = find_git_root()

# ── Couleurs ANSI ─────────────────────────────────────────────────────────────

def _enable_ansi() -> bool:
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleMode(
                ctypes.windll.kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    return sys.stdout.isatty()

_COLOR = _enable_ansi()

def _c(code: str) -> str:
    return code if _COLOR else ""

RST = _c("\033[0m");  BLD = _c("\033[1m");  DIM = _c("\033[2m")
GRN = _c("\033[92m"); YLW = _c("\033[93m"); RED = _c("\033[91m")
CYN = _c("\033[96m"); MGT = _c("\033[95m"); WHT = _c("\033[97m")

# ── Entetes de section ────────────────────────────────────────────────────────

def section(title: str, step: int = 0, total: int = 0, width: int = 68):
    step_str = f"  ETAPE {step}/{total}  " if step else "  "
    text     = f"{step_str}{title}"
    pad      = max(0, width - len(text) - 4)
    print(f"\n{MGT}{BLD}{'='*width}{RST}")
    print(f"{MGT}{BLD}  {text}{' '*pad}{RST}")
    print(f"{MGT}{BLD}{'='*width}{RST}")

# ── Git utilitaires ───────────────────────────────────────────────────────────

def git_cmd(*args, cwd: Path = REPO) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-c", "core.quotePath=false", *args],
        capture_output=True, text=True,
        encoding="utf-8", errors="replace", cwd=cwd,
    )

def git_out(*args, cwd: Path = REPO) -> str:
    return git_cmd(*args, cwd=cwd).stdout.strip()

def git_interactive(*args, cwd: Path = REPO) -> int:
    """Lance une commande git en mode interactif (sortie visible). Retourne le code de retour."""
    r = subprocess.run(
        ["git", "-c", "core.quotePath=false", *args],
        cwd=cwd,
    )
    return r.returncode

# ── Detection des fichiers binaires ──────────────────────────────────────────

_BINARY_EXT = {
    '.bin', '.elf', '.hex', '.a', '.o', '.lib', '.so', '.dll', '.exe',
    '.ico', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg',
    '.zip', '.tar', '.gz', '.7z', '.rar', '.pdf', '.mp3', '.mp4',
    '.xlsm', '.xlsx', '.xls', '.doc', '.docx',
}

def is_binary(path: Path) -> bool:
    if path.suffix.lower() in _BINARY_EXT:
        return True
    try:
        return b'\x00' in path.read_bytes()[:8192]
    except Exception:
        return True

# ── Verification upstream ─────────────────────────────────────────────────────

def check_upstream_remote() -> bool:
    r = subprocess.run(["git", "remote", "get-url", "upstream"],
                       capture_output=True, text=True, cwd=REPO)
    return r.returncode == 0

# ── Fetch upstream ────────────────────────────────────────────────────────────

def fetch_upstream() -> bool:
    print(f"  {DIM}git fetch upstream...{RST}", end="", flush=True)
    r = git_cmd("fetch", "upstream")
    if r.returncode == 0:
        print(f"\r  {GRN}✓{RST}  git fetch upstream  {DIM}(OK){RST}              ")
        return True
    print(f"\r  {RED}✗{RST}  git fetch upstream  {DIM}(ECHEC){RST}")
    print(f"  {RED}{r.stderr.strip()}{RST}")
    return False

# ── Affichage du conflit ──────────────────────────────────────────────────────

def count_conflict_lines(file_path: Path) -> tuple[int, int]:
    """Compte les lignes ours/theirs. Retourne (upstream_lines, mine_lines)."""
    try:
        lines = file_path.read_text(encoding='utf-8', errors='replace').splitlines()
    except Exception:
        return 0, 0
    upstream = mine = 0
    state = None
    for line in lines:
        if line.startswith('<<<<<<<'):
            state = 'upstream'   # pendant rebase: <<<< = upstream (ours)
        elif line.startswith('======='):
            state = 'mine'       # pendant rebase: ==== > >>>> = vos commits (theirs)
        elif line.startswith('>>>>>>>'):
            state = None
        elif state == 'upstream':
            upstream += 1
        elif state == 'mine':
            mine += 1
    return upstream, mine

def show_conflict(file_path: Path, max_lines: int = 50):
    """Affiche les blocs de conflit du fichier avec couleurs."""
    try:
        lines = file_path.read_text(encoding='utf-8', errors='replace').splitlines()
    except Exception:
        print(f"  {RED}Impossible de lire le fichier.{RST}")
        return

    shown = 0
    state = None
    for line in lines:
        if shown >= max_lines:
            print(f"  {DIM}... (tronque a {max_lines} lignes){RST}")
            break
        if line.startswith('<<<<<<<'):
            state = 'upstream'
            print(f"  {RED}{BLD}{line}{RST}")
        elif line.startswith('======='):
            state = 'mine'
            print(f"  {YLW}{BLD}{line}{RST}")
        elif line.startswith('>>>>>>>'):
            state = None
            print(f"  {GRN}{BLD}{line}{RST}")
        elif state == 'upstream':
            print(f"  {RED}  {line}{RST}")
        elif state == 'mine':
            print(f"  {GRN}  {line}{RST}")
        else:
            continue  # ignorer les lignes hors blocs de conflit
        shown += 1

# ── Ouverture VS Code ─────────────────────────────────────────────────────────

def open_vscode(file_path: Path):
    """Ouvre le fichier dans VS Code et attend la fermeture de l'onglet."""
    try:
        subprocess.run(["code", "--wait", str(file_path)], cwd=REPO)
    except FileNotFoundError:
        print(f"  {YLW}[WARN]{RST} VS Code ('code') introuvable dans le PATH.")
        print(f"  Editez manuellement : {CYN}{file_path}{RST}")
        input(f"  Appuyez sur {BLD}Entree{RST} une fois le fichier sauvegarde... ")

# ── Resolution interactive d'un conflit ──────────────────────────────────────

def resolve_conflict(rel: str, idx: int, total: int) -> str:
    """
    Affiche le conflit et demande a l'utilisateur quoi faire.
    Retourne 'mine', 'upstream', 'edit' ou 'abort'.

    Rappel git rebase :
      --theirs = VOS commits (rejoues sur upstream)
      --ours   = upstream/development (la base)
    """
    file_path = REPO / rel

    print(f"\n  {MGT}{BLD}CONFLIT  {WHT}{rel}  {DIM}({idx}/{total}){RST}")
    print(f"  {'─'*64}")

    if is_binary(file_path) or not file_path.exists():
        print(f"  {YLW}Fichier binaire — votre version conservee automatiquement.{RST}")
        r = git_cmd("checkout", "--theirs", "--", rel)
        if r.returncode == 0:
            git_cmd("add", "--", rel)
            print(f"  {GRN}✓{RST}  {DIM}votre version conservee (--theirs){RST}")
        else:
            print(f"  {RED}Erreur : {r.stderr.strip()}{RST}")
        return 'mine'

    upstream_lines, mine_lines = count_conflict_lines(file_path)
    print(f"  {RED}< upstream  {RST}: {upstream_lines} ligne(s) modifiee(s)")
    print(f"  {GRN}> le votre  {RST}: {mine_lines} ligne(s) modifiee(s)")
    print()
    show_conflict(file_path)
    print()

    while True:
        print(f"  {BLD}[M]{RST} Garder le mien   "
              f"{BLD}[U]{RST} Prendre upstream   "
              f"{BLD}[E]{RST} Editer dans VS Code   "
              f"{BLD}[Q]{RST} Annuler le rebase")
        choice = input(f"  Votre choix : ").strip().upper()

        if choice == 'M':
            r = git_cmd("checkout", "--theirs", "--", rel)
            if r.returncode != 0:
                print(f"  {RED}Erreur : {r.stderr.strip()}{RST}")
                continue
            git_cmd("add", "--", rel)
            print(f"  {GRN}✓{RST}  Votre version conservee.")
            return 'mine'

        elif choice == 'U':
            r = git_cmd("checkout", "--ours", "--", rel)
            if r.returncode != 0:
                print(f"  {RED}Erreur : {r.stderr.strip()}{RST}")
                continue
            git_cmd("add", "--", rel)
            print(f"  {GRN}✓{RST}  Version upstream conservee.")
            return 'upstream'

        elif choice == 'E':
            print(f"  {CYN}Ouverture VS Code — resolvez les conflits, "
                  f"sauvegardez et fermez l'onglet.{RST}")
            open_vscode(file_path)
            remaining_up, remaining_mine = count_conflict_lines(file_path)
            if remaining_up > 0 or remaining_mine > 0:
                print(f"  {YLW}[ATTENTION]{RST} Des marqueurs de conflit sont "
                      f"encore presents dans le fichier.")
                confirm = input(f"  Marquer quand meme comme resolu ? [o/N] ").strip().lower()
                if confirm != 'o':
                    continue
            git_cmd("add", "--", rel)
            print(f"  {GRN}✓{RST}  Fichier marque comme resolu.")
            return 'edit'

        elif choice == 'Q':
            return 'abort'

        else:
            print(f"  {YLW}Choix invalide. Tapez M, U, E ou Q.{RST}")

# ── Boucle de rebase ──────────────────────────────────────────────────────────

def get_conflicted_files() -> list[str]:
    return [
        f for f in git_out("diff", "--name-only", "--diff-filter=U").splitlines()
        if f.strip()
    ]

def has_conflicts(proc: subprocess.CompletedProcess) -> bool:
    combined = (proc.stdout or "") + (proc.stderr or "")
    return "CONFLICT" in combined or "conflict" in combined.lower()

def run_rebase(dry_run: bool) -> bool:
    """Lance le rebase et gere les conflits interactivement. Retourne True si succes."""

    # Branche de sauvegarde
    backup_branch = f"backup-avant-rebase-{datetime.now().strftime('%d%m%Y-%H%M%S')}"
    if not dry_run:
        r = git_cmd("branch", backup_branch)
        if r.returncode == 0:
            print(f"  {GRN}✓{RST}  Branche de sauvegarde : {CYN}{backup_branch}{RST}")
        else:
            print(f"  {YLW}[WARN]{RST} Impossible de creer la branche de sauvegarde.")
    else:
        print(f"  {YLW}[DRY-RUN]{RST} Branche de sauvegarde non creee.")

    if dry_run:
        merge_base   = git_out("merge-base", "HEAD", "upstream/development")
        local_files  = set(git_out("diff", "--name-only", merge_base, "HEAD").splitlines())
        remote_files = set(git_out("diff", "--name-only", merge_base, "upstream/development").splitlines())
        conflicts    = local_files & remote_files
        if conflicts:
            print(f"\n  {YLW}[DRY-RUN]{RST} {len(conflicts)} conflit(s) potentiel(s) :")
            for f in sorted(conflicts):
                print(f"    {YLW}~{RST}  {f}")
        else:
            print(f"\n  {GRN}✓{RST}  [DRY-RUN] Aucun conflit detecte.")
        return True

    # Lancement du rebase
    print(f"\n  {DIM}Lancement du rebase...{RST}\n")
    rc = git_interactive("rebase", "upstream/development")

    if rc == 0:
        print(f"\n  {GRN}✓{RST}  Rebase termine sans conflit.")
        return True

    # Boucle de resolution
    round_num = 0
    while True:
        conflicted = get_conflicted_files()

        if not conflicted:
            # Tous les conflits de ce commit sont resolus : on continue
            print(f"\n  {DIM}Continuation du rebase...{RST}\n")
            rc = git_interactive("rebase", "--continue")
            if rc == 0:
                print(f"\n  {GRN}✓{RST}  Rebase termine avec succes.")
                return True
            # git rebase --continue a rencontre de nouveaux conflits
            new_conflicts = get_conflicted_files()
            if new_conflicts:
                round_num += 1
                print(f"\n  {YLW}Nouveaux conflits detectes "
                      f"(commit suivant — round {round_num})...{RST}")
                continue
            # Erreur reelle
            print(f"\n  {RED}Erreur lors du rebase --continue.{RST}")
            abort = input(f"  Annuler le rebase ? [O/n] ").strip().lower()
            if abort != 'n':
                git_interactive("rebase", "--abort")
                print(f"  {YLW}Rebase annule. Votre branche est restauree.{RST}")
                print(f"  {DIM}Sauvegarde disponible : {backup_branch}{RST}")
            return False

        total = len(conflicted)
        for idx, rel in enumerate(conflicted, 1):
            result = resolve_conflict(rel, idx, total)
            if result == 'abort':
                git_interactive("rebase", "--abort")
                print(f"\n  {YLW}Rebase annule. Votre branche est restauree.{RST}")
                print(f"  {DIM}Sauvegarde disponible : {backup_branch}{RST}")
                return False

# ── Parsing des arguments ─────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="synchronise_upstream_tasmota.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
        add_help=False,
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Montre les conflits potentiels sans modifier les fichiers")
    parser.add_argument("-h", "-help", "--help", "--h",
                        action="store_true", dest="help")
    return parser

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = build_parser()
    args   = parser.parse_args()

    if args.help:
        print(__doc__)
        return

    print(f"\n{BLD}{WHT}=== Synchronisation upstream Tasmota ==={RST}")
    if args.dry_run:
        print(f"  {YLW}[DRY-RUN] simulation — aucun fichier ne sera modifie{RST}")
    print(f"  Repo    : {CYN}{REPO}{RST}")
    branch = git_out("branch", "--show-current")
    print(f"  Branche : {CYN}{branch}{RST}\n")

    # Verification upstream
    if not check_upstream_remote():
        print(f"\n{RED}[ERREUR]{RST} Remote 'upstream' introuvable.")
        print(f"  git remote add upstream https://github.com/arendst/Tasmota.git")
        sys.exit(1)

    # Modifications non commitees
    status = git_out("status", "--porcelain")
    if status and not args.dry_run:
        print(f"  {RED}[ERREUR]{RST} Vous avez des modifications non commitees :")
        for line in status.splitlines():
            print(f"    {YLW}{line}{RST}")
        print(f"\n  Committez ou stashez vos modifications avant de continuer.")
        print(f"  {DIM}git stash  (pour mettre de cote temporairement){RST}")
        sys.exit(1)

    t0 = time.monotonic()

    # Etape 1 : Fetch
    section("Mise a jour upstream (git fetch)", step=1, total=3)
    if not fetch_upstream() and not args.dry_run:
        sys.exit(1)

    # Etape 2 : Rebase
    section("Rebase sur upstream/development", step=2, total=3)
    success = run_rebase(dry_run=args.dry_run)

    # Etape 3 : Push
    if success and not args.dry_run:
        section("Pousser vers origin", step=3, total=3)
        elapsed = time.monotonic() - t0
        print(f"  Duree totale : {elapsed:.1f}s\n")
        push = input(f"  Pousser vers {CYN}origin/{branch}{RST} "
                     f"(--force-with-lease) ? [O/n] ").strip().lower()
        if push != 'n':
            print(f"  {DIM}git push --force-with-lease...{RST}", end="", flush=True)
            r = git_cmd("push", "origin", branch, "--force-with-lease")
            if r.returncode == 0:
                print(f"\r  {GRN}✓{RST}  Push reussi.                              ")
            else:
                print(f"\r  {RED}✗{RST}  Push echoue.")
                print(f"  {r.stderr.strip()}")
        else:
            print(f"  {DIM}Push ignore.{RST}")
    elif success and args.dry_run:
        print(f"\n  {YLW}[DRY-RUN]{RST} Simulation terminee.")

    print()


if __name__ == "__main__":
    main()
