# -*- coding: utf-8 -*-
r"""
=============================================================================
  genere_sauvegarde_tasmota.py  -  Sauvegarde des fichiers perso Tasmota
=============================================================================

UTILISATION
-----------
  python genere_sauvegarde_tasmota.py [options]

OPTIONS
-------
  --dry-run   Simule la sauvegarde sans ecrire de fichiers.
  --open      Ouvre INDEX.html dans le navigateur apres la sauvegarde.
  -h | --help Affiche ce message d'aide et quitte.

DESCRIPTION
-----------
  Auto-detecte via git diff les fichiers crees / modifies / supprimes
  par rapport a upstream/development.

  Fichiers crees  (A) : copies dans  1_fichiers_crees/  (arborescence preservee)
  Fichiers modifies (M) : dans  2_fichiers_modifies/  avec :
    - copie du fichier HEAD
    - <fichier>.diff.html  (diff visuel colore; omis pour les fichiers binaires)
    - <fichier>.patch      (diff unifie pour restauration selective)
  Fichiers supprimes (D) : listes dans  3_fichiers_supprimes/deleted.txt
  INDEX.html      : rapport cliquable a la racine du dossier de sauvegarde
  log_sauvegarde_*.txt : journal horodate de l'operation

  Dossier de sauvegarde : ...\Github\Tasmota-sauvegarde JJ-MM-AAAA HHhMM

AVERTISSEMENT UPSTREAM
----------------------
  Le remote "upstream" doit etre configure et recemment fetch :
    git remote add upstream https://github.com/arendst/Tasmota.git
    git fetch upstream
  Si le dernier fetch date de plus de 7 jours, un avertissement s'affiche.

=============================================================================
"""
import subprocess, shutil, difflib, sys, argparse, time, os
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

REPO   = find_git_root()
BACKUP = REPO.parent / f"Tasmota-sauvegarde {datetime.now().strftime('%d-%m-%Y %Hh%M')}"

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

# ── Barre de progression ──────────────────────────────────────────────────────

class Progress:
    BAR_W = 32
    LBL_W = 55

    def __init__(self, total: int, unit: str = "fichier(s)"):
        self.total   = total
        self.unit    = unit
        self.done    = 0
        self.errors  = 0
        self.t0      = time.monotonic()
        self._barlen = 0
        self._draw()

    def tick(self, label: str, status: str, ok: bool = True, warn: bool = False):
        self.done += 1
        if not ok:
            self.errors += 1
        self._clear_bar()
        if ok and not warn:
            icon = f"{GRN}✓{RST}";  color = GRN
        elif warn:
            icon = f"{YLW}⚠{RST}";  color = YLW
        else:
            icon = f"{RED}✗{RST}";  color = RED
        short = (label[:self.LBL_W - 3] + "...") if len(label) > self.LBL_W else label
        print(f"  {icon} {color}{short:<{self.LBL_W}}{RST}  {DIM}{status}{RST}")
        self._draw()

    def finish(self):
        self._clear_bar()
        elapsed = time.monotonic() - self.t0
        bar     = "#" * self.BAR_W
        ok_cnt  = self.done - self.errors
        color   = GRN if self.errors == 0 else YLW
        print(f"  {color}[{bar}]{RST} {BLD}100%{RST}  "
              f"{self.done}/{self.total}  {elapsed:.1f}s  "
              f"{GRN}{ok_cnt} OK{RST}"
              + (f"  {YLW}{self.errors} avert.{RST}" if self.errors else ""))

    def _draw(self):
        if self.total == 0:
            return
        pct    = self.done / self.total
        filled = int(self.BAR_W * pct)
        arrow  = ">" if filled < self.BAR_W else ""
        bar    = "#" * filled + arrow + "-" * (self.BAR_W - filled - len(arrow))
        elapsed = time.monotonic() - self.t0
        eta_str = ""
        if self.done > 0 and self.done < self.total:
            eta     = elapsed / self.done * (self.total - self.done)
            eta_str = f"  eta {eta:.0f}s"
        line = (f"  {CYN}[{bar}]{RST} {pct:3.0%}  "
                f"{self.done}/{self.total}  {elapsed:.1f}s{eta_str}")
        self._barlen = len(line) - (len(CYN) + len(RST))
        print(line, end="", flush=True)

    def _clear_bar(self):
        if self._barlen:
            print(f"\r{' ' * (self._barlen + 20)}\r", end="", flush=True)
            self._barlen = 0

# ── Interaction utilisateur ───────────────────────────────────────────────────

def ask_yes_no(question: str, default: str = "n") -> bool:
    """Pose une question o/n sur stdout et lit la réponse sur stdin.

    Utilise print() + readline() plutôt que input() pour que la question
    se termine par \\n et soit reçue immédiatement par la GUI (qui utilise
    readline() pour lire stdout du sous-processus).
    """
    hint = "[O/n]" if default.lower() in ("o", "y") else "[o/N]"
    while True:
        print(f"\n  {YLW}?{RST}  {BLD}{question}{RST}  {DIM}{hint}{RST}")
        try:
            rep = sys.stdin.readline().strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        if not rep:
            rep = default.lower()
        if rep in ("o", "oui", "y", "yes"):
            return True
        if rep in ("n", "non", "no"):
            return False
        print(f"  Repondez par  o  (oui) ou  n  (non).")


# ── Entetes de section ────────────────────────────────────────────────────────

def section(title: str, step: int = 0, total: int = 0, width: int = 68):
    step_str = f"  ETAPE {step}/{total}  " if step else "  "
    text     = f"{step_str}{title}"
    pad      = max(0, width - len(text) - 4)
    print(f"\n{MGT}{BLD}{'='*width}{RST}")
    print(f"{MGT}{BLD}  {text}{' '*pad}{RST}")
    print(f"{MGT}{BLD}{'='*width}{RST}")

# ── Journal ───────────────────────────────────────────────────────────────────

class Logger:
    def __init__(self):
        self._lines: list[str] = []
        self.t0 = time.monotonic()

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._lines.append(f"[{ts}] {msg}")

    def save(self, path: Path):
        elapsed = time.monotonic() - self.t0
        header  = (
            f"Sauvegarde Tasmota\n"
            f"Date   : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"Repo   : {REPO}\n"
            f"Backup : {BACKUP}\n"
            f"{'='*60}\n"
        )
        footer = f"\n{'='*60}\nDuree totale : {elapsed:.1f}s\n"
        path.write_text(header + "\n".join(self._lines) + footer, encoding='utf-8')
        print(f"\n  {DIM}Journal : {path.name}{RST}")

# ── Utilitaires git ───────────────────────────────────────────────────────────

def git_cmd(*args, cwd: Path = REPO) -> str:
    r = subprocess.run(["git", "-c", "core.quotePath=false", *args],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=cwd)
    return r.stdout

def check_upstream_remote() -> bool:
    r = subprocess.run(["git", "remote", "get-url", "upstream"],
                       capture_output=True, text=True, cwd=REPO)
    return r.returncode == 0

def check_upstream_freshness() -> int:
    """Retourne l'age en jours du dernier commit fetch sur upstream/development. -1 si inconnu."""
    ts_str = git_cmd("log", "upstream/development", "--format=%ct", "-1").strip()
    if not ts_str:
        return -1
    try:
        return (datetime.now() - datetime.fromtimestamp(int(ts_str))).days
    except Exception:
        return -1

def fetch_upstream() -> bool:
    """Lance git fetch upstream et retourne True si succès."""
    print(f"\n  {DIM}>>> git fetch upstream{RST}")
    r = subprocess.run(
        ["git", "fetch", "upstream"],
        cwd=REPO, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if r.returncode == 0:
        print(f"  {GRN}✓{RST}  Fetch upstream termine avec succes.\n")
        return True
    print(f"  {RED}✗{RST}  Fetch echoue :\n  {r.stderr.strip()}\n")
    return False

# ── Detection des fichiers binaires ──────────────────────────────────────────

_BINARY_EXT = {
    '.bin', '.elf', '.hex', '.a', '.o', '.lib', '.so', '.dll', '.exe',
    '.ico', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg',
    '.zip', '.tar', '.gz', '.7z', '.rar', '.pdf',
}

def is_binary(path: Path) -> bool:
    if path.suffix.lower() in _BINARY_EXT:
        return True
    try:
        return b'\x00' in path.read_bytes()[:8192]
    except Exception:
        return True

# ── Detection des fichiers modifies vs upstream ───────────────────────────────

def detect_changed_files() -> tuple[list[str], list[str], list[str]]:
    """Retourne (added, modified, deleted) via git diff upstream/development HEAD."""
    output   = git_cmd("diff", "upstream/development", "HEAD", "--name-status")
    added:    list[str] = []
    modified: list[str] = []
    deleted:  list[str] = []
    for line in output.splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        status, path = parts[0].strip(), parts[1].strip()
        if status.startswith("A"):
            added.append(path)
        elif status.startswith("M"):
            modified.append(path)
        elif status.startswith("D"):
            deleted.append(path)
    return added, modified, deleted

# ── Copie des fichiers crees ──────────────────────────────────────────────────

def copy_added_files(added: list[str], dry_run: bool,
                     logger: Logger) -> list[tuple]:
    if not added:
        print(f"  {DIM}Aucun fichier cree detecte.{RST}")
        return []

    progress = Progress(len(added))
    results: list[tuple] = []

    for rel in added:
        src = REPO / rel
        if not src.exists():
            progress.tick(rel, "introuvable dans HEAD", ok=False)
            logger.log(f"ERREUR cree/{rel}: introuvable dans HEAD")
            results.append((rel, "introuvable"))
            continue

        dest = BACKUP / "1_fichiers_crees" / rel
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

        status = "[dry-run]" if dry_run else "copie"
        progress.tick(rel, status)
        logger.log(f"CREE {rel}")
        results.append((rel, "copie"))

    progress.finish()
    return results

# ── Sauvegarde des fichiers modifies ─────────────────────────────────────────

def backup_modified_files(modified: list[str], dry_run: bool,
                          logger: Logger) -> list[tuple]:
    if not modified:
        print(f"  {DIM}Aucun fichier modifie detecte.{RST}")
        return []

    progress = Progress(len(modified), "fichier(s) + diff + patch")
    results: list[tuple] = []

    for rel in modified:
        src = REPO / rel
        if not src.exists():
            progress.tick(rel, "introuvable dans HEAD", ok=False)
            logger.log(f"ERREUR modif/{rel}: introuvable dans HEAD")
            results.append((rel, "introuvable"))
            continue

        dest   = BACKUP / "2_fichiers_modifies" / rel
        binary = is_binary(src)

        # -- Copie du fichier HEAD
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

        # -- Patch unifie (toujours genere, meme pour les binaires)
        patch_text = git_cmd("diff", "upstream/development", "HEAD", "--", rel)
        nb_add = patch_text.count("\n+")
        nb_del = patch_text.count("\n-")
        patch_dest = BACKUP / "2_fichiers_modifies" / (rel + ".patch")
        if not dry_run and patch_text.strip():
            patch_dest.parent.mkdir(parents=True, exist_ok=True)
            patch_dest.write_text(patch_text, encoding='utf-8')

        # -- Diff HTML (texte uniquement)
        if not binary:
            upstream_raw   = git_cmd("show", f"upstream/development:{rel}")
            head_text      = src.read_text(encoding='utf-8', errors='replace')
            upstream_lines = upstream_raw.splitlines(keepends=True)
            head_lines     = head_text.splitlines(keepends=True)
            differ   = difflib.HtmlDiff(wrapcolumn=120)
            html_out = differ.make_file(
                upstream_lines, head_lines,
                fromdesc=f"upstream/development/{rel}",
                todesc=f"HEAD/{rel}",
                context=True, numlines=3,
            )
            html_dest = BACKUP / "2_fichiers_modifies" / (rel + ".diff.html")
            if not dry_run:
                html_dest.parent.mkdir(parents=True, exist_ok=True)
                html_dest.write_text(html_out, encoding='utf-8')

        if dry_run:
            status = "[dry-run]" + (" [binaire]" if binary else "")
        elif binary:
            status = f".patch (+{nb_add}/-{nb_del})  [binaire — pas de diff.html]"
        else:
            status = f"diff.html + .patch  (+{nb_add}/-{nb_del})"

        progress.tick(rel, status, warn=binary)
        logger.log(f"MODIF {rel}: +{nb_add}/-{nb_del}"
                   + (" [binaire]" if binary else ""))
        results.append((rel, "sauvegarde_binaire" if binary else "sauvegarde"))

    progress.finish()
    return results

# ── Sauvegarde de la liste des fichiers supprimes ─────────────────────────────

def save_deleted_files(deleted: list[str], dry_run: bool,
                       logger: Logger) -> list[tuple]:
    if not deleted:
        print(f"  {DIM}Aucun fichier supprime detecte.{RST}")
        return []

    dest    = BACKUP / "3_fichiers_supprimes" / "deleted.txt"
    content = "\n".join(deleted) + "\n"

    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding='utf-8')

    tag = "[dry-run]" if dry_run else f"-> {dest.parent.name}/deleted.txt"
    ico = f"{YLW}⚠{RST}" if dry_run else f"{GRN}✓{RST}"
    print(f"  {ico}  {len(deleted)} fichier(s) supprime(s) liste(s)  {DIM}{tag}{RST}")
    for rel in deleted:
        print(f"    {RED}-{RST}  {DIM}{rel}{RST}")
        logger.log(f"SUPPRIME {rel}")

    return [(rel, "supprime") for rel in deleted]

# ── Generation de l'INDEX.html ────────────────────────────────────────────────

def generate_index_html(added_results: list, modified_results: list,
                        deleted_results: list, dry_run: bool) -> "Path | None":
    import html as _html
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    rows_added = ""
    for rel, status in added_results:
        bg   = "#d4f4d4" if status == "copie" else "#ffd4d4"
        link = f'<a href="1_fichiers_crees/{rel.replace(chr(92), "/")}">{_html.escape(rel)}</a>'
        rows_added += f'<tr style="background:{bg}"><td>{link}</td><td>{status}</td></tr>\n'

    rows_modified = ""
    for rel, status in modified_results:
        is_bin  = status == "sauvegarde_binaire"
        bg      = "#d4f4d4" if status in ("sauvegarde", "sauvegarde_binaire") else "#ffd4d4"
        rel_fwd = rel.replace("\\", "/")
        f_link  = f'<a href="2_fichiers_modifies/{rel_fwd}">{_html.escape(rel)}</a>'
        d_link  = (f'<a href="2_fichiers_modifies/{rel_fwd}.diff.html">[diff]</a>'
                   if not is_bin else
                   '<span style="color:#999">[binaire]</span>')
        p_link  = f'<a href="2_fichiers_modifies/{rel_fwd}.patch">[patch]</a>'
        rows_modified += (f'<tr style="background:{bg}">'
                          f'<td>{f_link}</td>'
                          f'<td>{d_link} {p_link}</td>'
                          f'<td>{status}</td></tr>\n')

    rows_deleted = ""
    for rel, _ in deleted_results:
        rows_deleted += (f'<tr style="background:#ffe8e8">'
                         f'<td>{_html.escape(rel)}</td>'
                         f'<td style="color:#c00">A supprimer manuellement</td></tr>\n')

    dry_badge = ('<span style="color:orange;font-weight:bold">'
                 ' [DRY-RUN — aucun fichier ecrit]</span>') if dry_run else ""

    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8">
<title>Sauvegarde Tasmota — {_html.escape(BACKUP.name)}</title>
<style>
  body{{font-family:Arial,sans-serif;margin:24px;color:#222}}
  h1{{color:#333}} h2{{color:#555;margin-top:24px}}
  table{{border-collapse:collapse;width:100%;margin-top:8px}}
  th,td{{border:1px solid #ccc;padding:6px 10px;text-align:left;vertical-align:top}}
  th{{background:#e8e8e8;font-weight:bold}}
  a{{color:#0055cc;text-decoration:none}} a:hover{{text-decoration:underline}}
  .meta{{background:#f6f6f6;padding:10px 14px;border-radius:4px;
         border-left:4px solid #aaa;margin-bottom:16px;font-size:.95em}}
</style>
</head>
<body>
<h1>Sauvegarde Tasmota{dry_badge}</h1>
<div class="meta">
  <b>Date&nbsp;:</b> {date_str} &nbsp;&nbsp;
  <b>Repo&nbsp;:</b> {_html.escape(str(REPO))} &nbsp;&nbsp;
  <b>Backup&nbsp;:</b> {_html.escape(str(BACKUP))}
</div>

<h2>Fichiers crees ({len(added_results)})</h2>
<table>
<tr><th>Fichier</th><th>Statut</th></tr>
{rows_added or '<tr><td colspan="2"><em>Aucun</em></td></tr>'}
</table>

<h2>Fichiers modifies ({len(modified_results)})</h2>
<table>
<tr><th>Fichier</th><th>Liens</th><th>Statut</th></tr>
{rows_modified or '<tr><td colspan="3"><em>Aucun</em></td></tr>'}
</table>

<h2>Fichiers supprimes ({len(deleted_results)})</h2>
<table>
<tr><th>Fichier</th><th>Action</th></tr>
{rows_deleted or '<tr><td colspan="2"><em>Aucun</em></td></tr>'}
</table>
</body></html>"""

    index_dest = BACKUP / "INDEX.html"
    if not dry_run:
        BACKUP.mkdir(parents=True, exist_ok=True)
        index_dest.write_text(html_content, encoding='utf-8')
        print(f"  {GRN}✓{RST}  INDEX.html  {DIM}-> {index_dest}{RST}")
        return index_dest
    else:
        print(f"  {YLW}[dry-run]{RST}  INDEX.html (non ecrit)")
        return None

# ── Rapport final ─────────────────────────────────────────────────────────────

def print_summary(added_results: list, modified_results: list,
                  deleted_results: list, elapsed: float):
    section("BILAN DE LA SAUVEGARDE")

    def _row(results, label, ok_statuses):
        ok  = sum(1 for _, s in results if s in ok_statuses)
        err = sum(1 for _, s in results if s == "introuvable")
        ico = f"{GRN}✓{RST}" if err == 0 else f"{RED}✗{RST}"
        print(f"  {ico}  {BLD}{label:<42}{RST}  "
              f"{GRN}{ok} OK{RST}"
              + (f"  {RED}{err} erreur(s){RST}" if err else "")
              + f"  {DIM}/ {len(results)} total{RST}")
        for rel, st in results:
            if st == "introuvable":
                print(f"       {RED}- {rel}{RST}")

    _row(added_results,    "Fichiers crees   (copie entiere)",
         ("copie",))
    _row(modified_results, "Fichiers modifies (diff + patch)",
         ("sauvegarde", "sauvegarde_binaire"))

    nb_del = len(deleted_results)
    if nb_del:
        print(f"  {YLW}⚠{RST}  {BLD}{'Fichiers supprimes (liste)':<42}{RST}  "
              f"{YLW}{nb_del} reference(s){RST}  {DIM}-> deleted.txt{RST}")

    print(f"\n  Duree    : {elapsed:.1f}s")
    print(f"  Dossier  : {CYN}{BACKUP}{RST}\n")

# ── Parsing des arguments ─────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="genere_sauvegarde_tasmota.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
        add_help=False,
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Simule sans ecrire de fichiers")
    parser.add_argument("--open", action="store_true",
                        help="Ouvre INDEX.html dans le navigateur a la fin")
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

    t0 = time.monotonic()
    print(f"\n{BLD}{WHT}=== Sauvegarde Tasmota ==={RST}")
    if args.dry_run:
        print(f"  {YLW}[DRY-RUN] simulation — aucun fichier ne sera ecrit{RST}")
    print(f"  Repo   : {CYN}{REPO}{RST}")
    print(f"  Backup : {CYN}{BACKUP}{RST}\n")

    # -- Verification du remote upstream
    if not check_upstream_remote():
        print(f"\n{RED}[ERREUR]{RST} Remote 'upstream' introuvable.")
        print(f"  Configurez-le avec :")
        print(f"    git remote add upstream https://github.com/arendst/Tasmota.git")
        print(f"    git fetch upstream\n")
        sys.exit(1)

    # -- Fraicheur du fetch upstream
    age_days = check_upstream_freshness()
    if age_days < 0:
        print(f"  {YLW}[ATTENTION]{RST} upstream/development introuvable.")
        print(f"  Le remote upstream n'a peut-etre jamais ete fetch.")
        print(f"  Sans fetch, le diff sera incomplet ou vide.\n")
        if ask_yes_no("Lancer 'git fetch upstream' maintenant ?", default="o"):
            fetch_upstream()
            age_days = check_upstream_freshness()
            if age_days < 0:
                print(f"  {YLW}Fetch realise mais upstream/development toujours introuvable.{RST}\n")
        else:
            print(f"  {DIM}Sauvegarde continuee sans fetch (diff potentiellement incomplet).{RST}\n")
    elif age_days > 7:
        print(f"  {YLW}[ATTENTION]{RST} Le dernier fetch upstream date de "
              f"{BLD}{age_days} jour(s){RST}.")
        print(f"  Le diff pourrait ne pas refleter l'etat actuel de Tasmota.\n")
        if ask_yes_no(f"Mettre a jour via 'git fetch upstream' ?", default="o"):
            fetch_upstream()
        else:
            print(f"  {DIM}Sauvegarde continuee sans fetch.{RST}\n")
    else:
        print(f"  {GRN}✓{RST}  Upstream fetch : {DIM}il y a {age_days} jour(s){RST}\n")

    # -- Detection des fichiers
    section("Detection des fichiers modifies vs upstream", step=1, total=5)
    added, modified, deleted = detect_changed_files()
    print(f"  {GRN}✓{RST}  "
          f"{BLD}{len(added)}{RST} cree(s)  |  "
          f"{BLD}{len(modified)}{RST} modifie(s)  |  "
          f"{BLD}{len(deleted)}{RST} supprime(s)\n")

    if not added and not modified and not deleted:
        print(f"  {YLW}Aucun fichier personnel detecte — rien a sauvegarder.{RST}\n")
        return

    logger = Logger()
    logger.log(f"Repo   : {REPO}")
    logger.log(f"Backup : {BACKUP}")
    logger.log(f"Detectes : {len(added)} crees, {len(modified)} modifies, "
               f"{len(deleted)} supprimes")
    if args.dry_run:
        logger.log("Mode : dry-run (aucune ecriture)")

    if not args.dry_run:
        BACKUP.mkdir(parents=True, exist_ok=True)

    # -- Copie des fichiers crees
    section("Copie des fichiers crees", step=2, total=5)
    r_added = copy_added_files(added, dry_run=args.dry_run, logger=logger)

    # -- Sauvegarde des fichiers modifies
    section("Sauvegarde des fichiers modifies", step=3, total=5)
    r_modified = backup_modified_files(modified, dry_run=args.dry_run, logger=logger)

    # -- Liste des fichiers supprimes
    section("Liste des fichiers supprimes", step=4, total=5)
    r_deleted = save_deleted_files(deleted, dry_run=args.dry_run, logger=logger)

    # -- INDEX.html
    section("Generation de l'INDEX.html", step=5, total=5)
    index_path = generate_index_html(r_added, r_modified, r_deleted,
                                     dry_run=args.dry_run)

    # -- Fichier de log
    if not args.dry_run:
        log_path = BACKUP / f"log_sauvegarde_{datetime.now().strftime('%d%m%Y_%H%M%S')}.txt"
        logger.save(log_path)

    print_summary(r_added, r_modified, r_deleted, time.monotonic() - t0)

    # -- Ouverture INDEX.html
    if args.open and index_path and index_path.exists():
        print(f"  {DIM}Ouverture de {index_path.name}...{RST}")
        try:
            os.startfile(index_path)
        except Exception as e:
            print(f"  {YLW}[WARN]{RST} Impossible d'ouvrir le navigateur : {e}")


if __name__ == "__main__":
    main()
