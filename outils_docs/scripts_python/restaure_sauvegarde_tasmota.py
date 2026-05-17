# -*- coding: utf-8 -*-
r"""
=============================================================================
  restaure_sauvegarde_tasmota.py  -  Restauration d'une sauvegarde Tasmota
=============================================================================

UTILISATION
-----------
  python restaure_sauvegarde_tasmota.py [options]

OPTIONS
-------
  -s <chemin>     Dossier de sauvegarde source.
                  Defaut : dernier dossier "Tasmota-sauvegarde JJ-MM-AAAA HHhMM"
                           trouve dans C:\Users\<user>\Documents\Github\

  -d <chemin>     Dossier de destination (fork Tasmota cible).
                  Defaut : demande via prompt interactif.

  -f <filtre>     Restaure uniquement les fichiers dont le chemin contient
                  <filtre> (insensible a la casse, sous-chaine).
                  Repeatable : -f berry -f webcam
                  Exemple : -f xdrv_52   restaure tous les fichiers xdrv_52*

  --dossiers <choix>
                  Limite la restauration a un sous-ensemble du backup.
                    crees     -> uniquement 1_fichiers_crees/
                    modifies  -> uniquement 2_fichiers_modifies/
                    tous      -> les deux (defaut)

  --list          Affiche le contenu du backup (fichiers, patches, rollbacks)
                  sans rien faire.

  --dry-run       Simule la restauration sans ecrire de fichiers.
                  Affiche ce qui serait fait (copie, patch, rollback).

  --prepare       Genere les fichiers .patch dans la sauvegarde en lisant
                  le depot git courant.  A lancer AVANT de reinitialiser
                  le fork.

  -h | -help | --help
                  Affiche ce message d'aide et quitte.

WORKFLOW RECOMMANDE
-------------------
  Etape 1 - AVANT de reinitialiser le fork :
    python restaure_sauvegarde_tasmota.py --prepare
    -> detecte automatiquement le backup le plus recent
    -> genere les .patch pour chaque fichier modifie

  Etape 2 - Reinitialiser le fork sur GitHub, puis cloner localement
            le nouveau depot dans un dossier de destination.

  Etape 3 - Inspecter le backup :
    python restaure_sauvegarde_tasmota.py --list

  Etape 4 - Simuler la restauration :
    python restaure_sauvegarde_tasmota.py --dry-run -d C:\...\Tasmota

  Etape 5 - Restaurer :
    python restaure_sauvegarde_tasmota.py -d C:\...\Tasmota
    -> copie les fichiers crees en entier
    -> applique uniquement les parties modifiees via les .patch
    -> sauvegarde les fichiers ecrases dans _rollback/ (annulation possible)

  Exemples :
    # Restaurer un seul fichier
    python restaure_sauvegarde_tasmota.py -f webcam -d C:\...\Tasmota

    # Inspecter la derniere sauvegarde
    python restaure_sauvegarde_tasmota.py --list

    # Simulation complete
    python restaure_sauvegarde_tasmota.py --dry-run \
        -s "C:\...\Tasmota-sauvegarde 08-05-2026 10h30" -d "C:\...\Tasmota"

    # Restaurer seulement les fichiers créés
    python restaure_sauvegarde_tasmota.py --dossiers crees -d C:\...\Tasmota

    # Restaurer seulement les modifications (patches) en dry-run
    python restaure_sauvegarde_tasmota.py --dossiers modifies --dry-run -d C:\...\Tasmota

    # o (ou Entrée) — applique ce fichier et passe au suivant
    # n — ignore ce fichier (compté dans le bilan final)
    # t — applique tous les fichiers restants sans redemander
    # q — arrête la restauration immédiatement
    # En mode --dry-run : affiche les diffs sans demander de confirmation (rien n'est écrit)

ROLLBACK
--------
  Avant d'ecraser chaque fichier de destination, le script cree une copie
  dans :  <sauvegarde>/_rollback_<timestamp>/
  Pour annuler une restauration, recopiez manuellement les fichiers du
  dossier _rollback vers le depot cible.

FICHIERS SUPPRIMES
------------------
  Si le backup contient 3_fichiers_supprimes/deleted.txt, la liste est
  affichee a la fin de la restauration. Ces fichiers doivent etre supprimes
  manuellement dans la destination.

=============================================================================
"""
import subprocess, shutil, sys, re, argparse, time
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
GITHUB_DIR = Path.home() / "Documents" / "Github"

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

RST  = _c("\033[0m");  BLD = _c("\033[1m");  DIM = _c("\033[2m")
GRN  = _c("\033[92m"); YLW = _c("\033[93m"); RED = _c("\033[91m")
CYN  = _c("\033[96m"); MGT = _c("\033[95m"); WHT = _c("\033[97m")

def print_legend(items: list):
    print(f"  {DIM}Legende :{RST}")
    for color, label in items:
        print(f"    {color}■{RST}  {label}")
    print()


def display_diff_preview(patch_text: str, max_lines: int = 60):
    """Affiche les hunks d'un patch avec coloration syntaxique."""
    display_lines = [
        l for l in patch_text.splitlines()
        if not l.startswith(("diff ", "index ", "--- ", "+++ "))
        and l != "\\ No newline at end of file"
    ]
    for i, line in enumerate(display_lines):
        if i >= max_lines:
            print(f"    {DIM}... {len(display_lines) - i} ligne(s) non affichee(s){RST}")
            break
        if line.startswith("@@"):
            print(f"    {CYN}{line}{RST}")
        elif line.startswith("+"):
            print(f"    {GRN}{line}{RST}")
        elif line.startswith("-"):
            print(f"    {RED}{line}{RST}")
        else:
            print(f"    {DIM}{line}{RST}")


def ask_file_confirmation() -> str:
    """Demande confirmation pour un fichier. Retourne 'o', 'n', 't' ou 'q'."""
    while True:
        rep = input(
            f"  Restaurer ? "
            f"[{GRN}o{RST}]ui  [{RED}n{RST}]on  [{YLW}t{RST}]ous  [{MGT}q{RST}]uitter : "
        ).strip().lower()
        if rep in ("o", "n", "t", "q"):
            return rep
        if rep == "":
            return "o"
        print(f"  {RED}Entrez o / n / t / q{RST}")

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

    def tick(self, label: str, status: str, ok: bool = True, warn: bool = False,
             label_color: str = ""):
        self.done += 1
        if not ok:
            self.errors += 1
        self._clear_bar()
        if ok and not warn:
            icon  = f"{GRN}✓{RST}";  color = GRN
        elif warn:
            icon  = f"{YLW}⚠{RST}";  color = YLW
        else:
            icon  = f"{RED}✗{RST}";  color = RED
        lc    = label_color if label_color else color
        short = (label[:self.LBL_W - 3] + "...") if len(label) > self.LBL_W else label
        print(f"  {icon} {lc}{short:<{self.LBL_W}}{RST}  {DIM}{status}{RST}")
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
            f"Restauration Tasmota\n"
            f"Date   : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"{'='*60}\n"
        )
        footer = f"\n{'='*60}\nDuree totale : {elapsed:.1f}s\n"
        path.write_text(header + "\n".join(self._lines) + footer, encoding='utf-8')
        print(f"\n  {DIM}Journal : {path.name}{RST}")

# ── Utilitaires generaux ──────────────────────────────────────────────────────

def find_git_root(start: Path) -> "Path | None":
    p = start.resolve()
    while p != p.parent:
        if (p / '.git').exists():
            return p
        p = p.parent
    return None


def parse_backup_date(folder_name: str) -> datetime:
    parts = folder_name.split(" ")
    if len(parts) >= 3:
        try:
            return datetime.strptime(parts[1] + " " + parts[2], "%d-%m-%Y %Hh%M")
        except ValueError:
            pass
    if len(parts) == 2 and len(parts[1]) == 8:
        try:
            return datetime.strptime(parts[1], "%d%m%Y")
        except ValueError:
            pass
    return datetime.min


def find_latest_backup(search_root: Path) -> "Path | None":
    if not search_root.exists():
        return None
    candidates = [d for d in search_root.iterdir()
                  if d.is_dir() and d.name.startswith("Tasmota-sauvegarde ")]
    return max(candidates, key=lambda d: parse_backup_date(d.name)) if candidates else None


def prompt_dir(label: str, default: "Path | None" = None) -> Path:
    hint = f"\n  {DIM}[defaut : {default}]{RST}" if default else ""
    while True:
        val = input(f"\n{BLD}{label}{RST}{hint}\n  > ").strip()
        if not val and default:
            return default
        p = Path(val)
        if p.exists() and p.is_dir():
            return p
        print(f"  {RED}[ERREUR]{RST} Dossier introuvable : {p}")


def git_cmd(*args, cwd: Path) -> str:
    r = subprocess.run(["git", "-c", "core.quotePath=false", *args],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=cwd)
    return r.stdout


def is_git_repo(path: Path) -> bool:
    return subprocess.run(["git", "rev-parse", "--git-dir"],
                          capture_output=True, cwd=path).returncode == 0


def _matches_filter(rel: str, filters: list[str]) -> bool:
    """True si le chemin relatif contient au moins un des filtres (insensible a la casse)."""
    rel_lower = rel.lower().replace("\\", "/")
    return any(f.lower() in rel_lower for f in filters)

# ── Rollback ──────────────────────────────────────────────────────────────────

def rollback_file(dest_file: Path, rollback_dir: Path, rel: str) -> bool:
    """Copie dest_file dans rollback_dir/rel avant ecrasement. Retourne True si fait."""
    if not dest_file.exists() or rollback_dir is None:
        return False
    rb_dest = rollback_dir / rel
    rb_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dest_file, rb_dest)
    return True

# ── Verification de coherence du backup ──────────────────────────────────────

def check_backup_integrity(backup_dir: Path) -> list[str]:
    """Verifie la structure du backup. Retourne une liste d'avertissements."""
    warnings: list[str] = []

    crees_dir  = backup_dir / "1_fichiers_crees"
    modifs_dir = backup_dir / "2_fichiers_modifies"

    if not crees_dir.exists() and not modifs_dir.exists():
        warnings.append(
            "Aucun dossier 1_fichiers_crees/ ni 2_fichiers_modifies/ — "
            "backup vide ou structure incorrecte"
        )
        return warnings

    if modifs_dir.exists():
        source_files = {
            str(f.relative_to(modifs_dir)).replace("\\", "/")
            for f in modifs_dir.rglob("*")
            if f.is_file() and f.suffix not in (".patch", ".html")
        }
        patch_bases = {
            str(f.relative_to(modifs_dir)).replace("\\", "/")[:-6]
            for f in modifs_dir.rglob("*.patch")
        }
        missing = source_files - patch_bases
        orphans = patch_bases - source_files
        if missing:
            warnings.append(
                f"{len(missing)} fichier(s) modifie(s) sans .patch "
                f"(restauration par copie complete pour ces fichiers)"
            )
        if orphans:
            warnings.append(
                f"{len(orphans)} .patch sans fichier source correspondant "
                f"(ces patches seront ignores)"
            )

    return warnings

# ── Mode --list ───────────────────────────────────────────────────────────────

def list_backup(backup_dir: Path):
    """Affiche le contenu d'un backup sans rien faire."""
    section("CONTENU DU BACKUP")

    backup_date = parse_backup_date(backup_dir.name)
    date_fmt    = (backup_date.strftime("%d/%m/%Y %H:%M")
                   if backup_date != datetime.min else "?")
    print(f"\n  {BLD}{backup_dir.name}{RST}  {DIM}(date : {date_fmt}){RST}\n")

    # -- Fichiers crees
    crees_root = backup_dir / "1_fichiers_crees"
    crees: list[str] = []
    if crees_root.exists():
        crees = sorted(
            str(f.relative_to(crees_root)).replace("\\", "/")
            for f in crees_root.rglob("*") if f.is_file()
        )
    print(f"  {BLD}Fichiers crees ({len(crees)}){RST}")
    for rel in crees:
        print(f"    {GRN}+{RST}  {rel}")
    if not crees:
        print(f"    {DIM}(aucun){RST}")

    # -- Fichiers modifies
    modifs_root = backup_dir / "2_fichiers_modifies"
    modifs: list[str] = []
    if modifs_root.exists():
        modifs = sorted({
            str(f.relative_to(modifs_root)).replace("\\", "/")
            for f in modifs_root.rglob("*")
            if f.is_file() and f.suffix not in (".patch", ".html")
        })
    print(f"\n  {BLD}Fichiers modifies ({len(modifs)}){RST}")
    for rel in modifs:
        has_patch = (modifs_root / (rel + ".patch")).exists()
        has_diff  = (modifs_root / (rel + ".diff.html")).exists()
        patch_tag = (f"  {GRN}[.patch]{RST}" if has_patch
                     else f"  {YLW}[sans .patch — copie complete]{RST}")
        diff_tag  = f"  {DIM}[.diff.html]{RST}" if has_diff else ""
        print(f"    {YLW}~{RST}  {rel}{patch_tag}{diff_tag}")
    if not modifs:
        print(f"    {DIM}(aucun){RST}")

    # -- Fichiers supprimes
    suppr_file = backup_dir / "3_fichiers_supprimes" / "deleted.txt"
    suppr: list[str] = []
    if suppr_file.exists():
        suppr = [l.strip() for l in
                 suppr_file.read_text(encoding='utf-8').splitlines() if l.strip()]
    print(f"\n  {BLD}Fichiers supprimes ({len(suppr)}){RST}")
    for rel in suppr:
        print(f"    {RED}-{RST}  {rel}")
    if not suppr:
        print(f"    {DIM}(aucun){RST}")

    # -- Journaux et rollbacks
    logs      = sorted(backup_dir.glob("log_*.txt"))
    rollbacks = sorted(backup_dir.glob("_rollback_*"))
    if logs or rollbacks:
        print(f"\n  {BLD}Journaux / Rollbacks{RST}")
        for f in logs:
            size_kb = f.stat().st_size / 1024
            print(f"    {DIM}[log]  {f.name}  ({size_kb:.1f} Ko){RST}")
        for d in rollbacks:
            if d.is_dir():
                nb = sum(1 for _ in d.rglob("*") if _.is_file())
                print(f"    {DIM}[rb]   {d.name}  ({nb} fichier(s)){RST}")

    # -- Verification de coherence
    warnings = check_backup_integrity(backup_dir)
    print()
    if warnings:
        print(f"  {YLW}[AVERTISSEMENTS]{RST}")
        for w in warnings:
            print(f"    {YLW}⚠{RST}  {w}")
    else:
        print(f"  {GRN}✓{RST}  Structure du backup coherente")

    total = len(crees) + len(modifs) + len(suppr)
    print(f"\n  Total : {BLD}{total}{RST} fichier(s) personnel(s) references\n")

# ── Etape --prepare : generation des .patch ──────────────────────────────────

def generate_patches_for_backup(backup_dir: Path, repo: Path) -> dict:
    src_root = backup_dir / "2_fichiers_modifies"
    if not src_root.exists():
        print(f"  {YLW}[SKIP]{RST} Dossier 2_fichiers_modifies absent.")
        return {}

    items = sorted([
        f for f in src_root.rglob("*")
        if f.is_file() and f.suffix not in (".patch", ".html")
    ])
    if not items:
        print(f"  {YLW}Aucun fichier a traiter.{RST}")
        return {}

    print_legend([
        (GRN, "Patch genere         -> restauration selective (hunks) a la prochaine etape"),
        (CYN, "Patch deja present   -> restauration selective (hunks) a la prochaine etape"),
        (DIM, "Identique a upstream -> pas de patch genere, copie complete si restaure"),
    ])
    progress = Progress(len(items), "patch(es)")
    results: dict = {}

    for item in items:
        rel        = str(item.relative_to(src_root)).replace("\\", "/")
        patch_dest = src_root / (rel + ".patch")

        if patch_dest.exists():
            progress.tick(rel, "deja present", ok=True, label_color=CYN)
            results[rel] = "deja_present"
            continue

        patch_text = git_cmd("diff", "upstream/development", "HEAD", "--", rel, cwd=repo)

        if not patch_text.strip():
            progress.tick(rel, "identique a upstream", ok=True, label_color=DIM)
            results[rel] = "identique"
            continue

        patch_dest.parent.mkdir(parents=True, exist_ok=True)
        patch_dest.write_text(patch_text, encoding="utf-8")
        nb_add = patch_text.count("\n+")
        nb_del = patch_text.count("\n-")
        progress.tick(rel, f"+{nb_add} / -{nb_del} lignes  ->  {patch_dest.name}",
                      ok=True, label_color=GRN)
        results[rel] = "genere"

    progress.finish()
    return results

# ── Applicateur de patch Python ───────────────────────────────────────────────

def apply_unified_patch(dest_content: str, patch_text: str) -> "tuple[str, list[str]]":
    if not patch_text.strip():
        return dest_content, []

    result       = dest_content.splitlines(keepends=True)
    errors: list = []
    offset       = 0
    patch_lines  = patch_text.splitlines(keepends=True)
    i = 0

    while i < len(patch_lines):
        s = patch_lines[i].rstrip("\r\n")
        if s.startswith(("diff ", "index ", "--- ", "+++ ")):
            i += 1
            continue
        if not s.startswith("@@"):
            i += 1
            continue

        m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", s)
        if not m:
            i += 1
            continue

        old_start  = int(m.group(1))
        hunk_label = s
        i += 1
        old_lines: list = []
        new_lines: list = []

        while i < len(patch_lines):
            l  = patch_lines[i]
            s2 = l.rstrip("\r\n")
            if s2.startswith("@@") or s2.startswith("diff "):
                break
            if s2 == r"\ No newline at end of file":
                i += 1
                continue
            if not l or l[0] not in (" ", "-", "+"):
                i += 1
                continue
            ch = l[0];  text = l[1:]
            if ch == " ":
                old_lines.append(text);  new_lines.append(text)
            elif ch == "-":
                old_lines.append(text)
            elif ch == "+":
                new_lines.append(text)
            i += 1

        expected = old_start - 1 + offset

        def norm(lines):
            return [x.rstrip("\r\n") for x in lines]

        actual_pos = None
        if old_lines:
            target = norm(old_lines)
            for shift in range(0, 26):
                for sign in ([0] if shift == 0 else [1, -1]):
                    p = expected + sign * shift
                    if p < 0 or p + len(old_lines) > len(result):
                        continue
                    if norm(result[p : p + len(old_lines)]) == target:
                        actual_pos = p
                        break
                if actual_pos is not None:
                    break
        else:
            actual_pos = expected

        if actual_pos is None:
            errors.append(f"Hunk non applique ({hunk_label})")
            continue

        result[actual_pos : actual_pos + len(old_lines)] = new_lines
        offset += len(new_lines) - len(old_lines)

    return "".join(result), errors

# ── Copie des fichiers crees ──────────────────────────────────────────────────

def copy_created_files(backup_dir: Path, dest_dir: Path,
                       dry_run: bool = False,
                       rollback_dir: "Path | None" = None,
                       logger: "Logger | None" = None,
                       only_files: "list[str] | None" = None) -> list:
    src_root = backup_dir / "1_fichiers_crees"
    if not src_root.exists():
        print(f"  {YLW}[SKIP]{RST} Dossier 1_fichiers_crees absent.")
        return []

    all_files = sorted(f for f in src_root.rglob("*") if f.is_file())
    if only_files:
        all_files = [f for f in all_files
                     if _matches_filter(
                         str(f.relative_to(src_root)).replace("\\", "/"),
                         only_files)]

    if not all_files:
        print(f"  {DIM}Aucun fichier cree correspond au filtre.{RST}")
        return []

    progress = Progress(len(all_files))
    results: list = []

    for src in all_files:
        rel     = src.relative_to(src_root)
        rel_str = str(rel).replace("\\", "/")
        dest    = dest_dir / rel

        rolled = False
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if rollback_dir:
                rolled = rollback_file(dest, rollback_dir, rel_str)
            shutil.copy2(src, dest)

        rb_tag = f"  {DIM}[rb]{RST}" if rolled else ""
        status = "[dry-run]" if dry_run else f"copie{rb_tag}"
        progress.tick(rel_str, status, ok=True)
        if logger:
            logger.log(f"CREE {rel_str}: {'dry-run' if dry_run else 'copie'}"
                       + (" [rollback]" if rolled else ""))
        results.append((rel_str, "copie"))

    progress.finish()
    return results

# ── Application des fichiers modifies ────────────────────────────────────────

def apply_modified_files(backup_dir: Path, dest_dir: Path,
                         dry_run: bool = False,
                         rollback_dir: "Path | None" = None,
                         logger: "Logger | None" = None,
                         only_files: "list[str] | None" = None) -> list:
    src_root = backup_dir / "2_fichiers_modifies"
    if not src_root.exists():
        print(f"  {YLW}[SKIP]{RST} Dossier 2_fichiers_modifies absent.")
        return []

    all_rels = sorted({
        str(f.relative_to(src_root)).replace("\\", "/")
        for f in src_root.rglob("*")
        if f.is_file() and f.suffix not in (".patch", ".html")
    })
    if only_files:
        all_rels = [r for r in all_rels if _matches_filter(r, only_files)]

    if not all_rels:
        print(f"  {DIM}Aucun fichier modifie correspond au filtre.{RST}")
        return []

    print_legend([
        (GRN, ".patch applique selectivement (hunks uniquement)"),
        (YLW, ".patch present mais fichier absent en destination -> copie complete"),
        (RED, ".patch present mais echec hunk(s)               -> copie complete"),
        (MGT, "Pas de .patch                                   -> copie complete"),
    ])

    results: list  = []
    apply_all      = False
    SEP            = f"{'─' * 66}"

    for idx, rel in enumerate(all_rels, 1):
        src_file   = src_root / rel
        patch_file = src_root / (rel + ".patch")
        dest_file  = dest_dir / rel

        # ── En-tete ──────────────────────────────────────────────────────────
        print(f"\n  {CYN}{SEP}{RST}")
        print(f"  {BLD}[{idx}/{len(all_rels)}]  {rel}{RST}")
        print(f"  {CYN}{SEP}{RST}\n")

        # ── Preview + determination de l'action ──────────────────────────────
        if patch_file.exists():
            patch_text = patch_file.read_text(encoding="utf-8", errors="replace")
            if not dest_file.exists():
                situation   = "absent"
                new_content = None
                patch_errors = []
                print(f"  {YLW}Fichier absent en destination -> sera cree (copie complete){RST}\n")
            else:
                dest_content = dest_file.read_text(encoding="utf-8", errors="replace")
                new_content, patch_errors = apply_unified_patch(dest_content, patch_text)
                if patch_errors:
                    situation = "patch_echec"
                    display_diff_preview(patch_text)
                    print(f"\n  {RED}⚠ {len(patch_errors)} hunk(s) en echec -> copie complete{RST}")
                    for e in patch_errors:
                        print(f"    {DIM}! {e}{RST}")
                    print()
                else:
                    situation = "patch_ok"
                    display_diff_preview(patch_text)
                    print()
        else:
            patch_text   = None
            new_content  = None
            patch_errors = []
            situation    = "sans_patch"
            print(f"  {MGT}Pas de fichier .patch -> copie complete du fichier de sauvegarde{RST}\n")

        # ── Confirmation (sauf dry-run ou apply_all) ─────────────────────────
        if not dry_run and not apply_all:
            rep = ask_file_confirmation()
            if rep == "q":
                print(f"\n  {YLW}Restauration interrompue.{RST}")
                break
            elif rep == "n":
                print(f"  {DIM}ignore{RST}")
                if logger:
                    logger.log(f"MODIF {rel}: ignore par l'utilisateur")
                results.append((rel, "ignore"))
                continue
            elif rep == "t":
                apply_all = True

        # ── Application ──────────────────────────────────────────────────────
        if situation == "patch_ok":
            if not dry_run:
                if rollback_dir:
                    rollback_file(dest_file, rollback_dir, rel)
                dest_file.write_text(new_content, encoding="utf-8")
            status = "[dry-run] patch OK" if dry_run else "patch applique"
            color  = GRN
            if logger:
                logger.log(f"MODIF {rel}: patch OK")
            results.append((rel, "patch_ok"))

        elif situation == "absent":
            if not dry_run:
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dest_file)
            status = "[dry-run] copie (absent)" if dry_run else "copie (absent dans dest.)"
            color  = YLW
            if logger:
                logger.log(f"MODIF {rel}: copie (absent)")
            results.append((rel, "copie_absent"))

        elif situation == "patch_echec":
            if not dry_run:
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                if rollback_dir:
                    rollback_file(dest_file, rollback_dir, rel)
                shutil.copy2(src_file, dest_file)
            nb_e   = len(patch_errors)
            status = (f"[dry-run] {nb_e} hunk(s) echec -> copie"
                      if dry_run else f"{nb_e} hunk(s) echec -> copie complete")
            color  = RED
            if logger:
                logger.log(f"MODIF {rel}: patch partiel {nb_e} erreur(s)")
            results.append((rel, f"patch_partiel_{nb_e}_erreurs"))

        else:  # sans_patch
            if not dry_run:
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                if rollback_dir:
                    rollback_file(dest_file, rollback_dir, rel)
                shutil.copy2(src_file, dest_file)
            status = "[dry-run] copie (sans patch)" if dry_run else "copie complete (pas de .patch)"
            color  = MGT
            if logger:
                logger.log(f"MODIF {rel}: copie sans patch")
            results.append((rel, "copie_complete_sans_patch"))

        print(f"  {GRN}✓{RST} {color}{rel}{RST}  {DIM}{status}{RST}")

    return results

# ── Rapport final ─────────────────────────────────────────────────────────────

def print_summary(r_created: list, r_modified: list, t_total: float):
    section("BILAN DE LA RESTAURATION")

    def stats(results, label):
        ok      = sum(1 for _, s in results if s in ("copie", "patch_ok", "copie_absent"))
        warn    = sum(1 for _, s in results if "sans_patch" in s or "partiel" in s)
        errors  = sum(1 for _, s in results if "erreur" in s)
        ignored = sum(1 for _, s in results if s == "ignore")
        icon    = f"{GRN}✓{RST}" if errors == 0 else f"{RED}✗{RST}"
        w_str   = f"  {YLW}{warn} fallback{RST}" if warn else ""
        e_str   = f"  {RED}{errors} erreur(s){RST}" if errors else ""
        i_str   = f"  {DIM}{ignored} ignore(s){RST}" if ignored else ""
        print(f"  {icon}  {BLD}{label:<35}{RST}  "
              f"{GRN}{ok} OK{RST}{w_str}{e_str}{i_str}  "
              f"{DIM}/ {len(results)} total{RST}")
        if errors:
            for rel, st in results:
                if "erreur" in st:
                    print(f"       {RED}- {rel}  ({st}){RST}")

    stats(r_created,  "Fichiers crees (copie entiere)")
    stats(r_modified, "Fichiers modifies (patch/copie)")
    print(f"\n  Duree totale : {t_total:.1f}s\n")

# ── Parsing des arguments ─────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="restaure_sauvegarde_tasmota.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
        add_help=False,
    )
    parser.add_argument("-s", "--source",  metavar="CHEMIN")
    parser.add_argument("-d", "--dest",    metavar="CHEMIN")
    parser.add_argument("-f", "--file",    metavar="FILTRE",
                        action="append", dest="files",
                        help="Filtre sur le chemin (sous-chaine, repetable)")
    parser.add_argument("--dossiers", metavar="crees|modifies|tous",
                        choices=["crees", "modifies", "tous"], default="tous",
                        help="Dossiers a restaurer (defaut : tous)")
    parser.add_argument("--list",    action="store_true",
                        help="Affiche le contenu du backup sans restaurer")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simule sans ecrire de fichiers")
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

    t_global = time.monotonic()
    print(f"\n{BLD}{WHT}=== Restauration sauvegarde Tasmota ==={RST}\n")
    do_crees    = args.dossiers in ("tous", "crees")
    do_modifies = args.dossiers in ("tous", "modifies")

    if args.dry_run:
        print(f"  {YLW}[DRY-RUN] simulation — aucun fichier ne sera ecrit{RST}\n")
    if args.dossiers != "tous":
        label = "1_fichiers_crees" if args.dossiers == "crees" else "2_fichiers_modifies"
        print(f"  {CYN}[DOSSIER]{RST}  {label} uniquement\n")
    if args.files:
        print(f"  {CYN}[FILTRE]{RST}  {' | '.join(args.files)}\n")

    # ── Dossier de sauvegarde ─────────────────────────────────────────────────
    if args.source:
        backup_dir = Path(args.source)
        if not backup_dir.exists() or not backup_dir.is_dir():
            print(f"{RED}[ERREUR]{RST} Dossier de sauvegarde introuvable : {backup_dir}")
            sys.exit(1)
    else:
        latest = find_latest_backup(GITHUB_DIR)
        if latest:
            print(f"  Derniere sauvegarde detectee : {CYN}{latest.name}{RST}")
        backup_dir = prompt_dir("Dossier de sauvegarde", default=latest)

    backup_date = parse_backup_date(backup_dir.name)
    date_str    = backup_date.strftime("%d/%m/%Y %H:%M") if backup_date != datetime.min else "?"
    print(f"\n  {GRN}✓{RST}  Backup : {BLD}{backup_dir.name}{RST}  {DIM}(date : {date_str}){RST}")

    # ── MODE --list ───────────────────────────────────────────────────────────
    if args.list:
        list_backup(backup_dir)
        return

    # ── MODE --prepare ────────────────────────────────────────────────────────
    if args.prepare:
        section("GENERATION DES FICHIERS .PATCH")

        repo = find_git_root(SCRIPT_DIR)
        if not repo:
            repo_str = input("Chemin du repo Tasmota git (vide pour annuler) : ").strip()
            if not repo_str:
                print("Annule.")
                return
            repo = Path(repo_str)
            if not is_git_repo(repo):
                print(f"{RED}[ERREUR]{RST} {repo} n'est pas un depot git valide.")
                sys.exit(1)

        print(f"  Repo source  : {CYN}{repo}{RST}")
        print(f"  Backup cible : {CYN}{backup_dir}{RST}\n")

        t0      = time.monotonic()
        results = generate_patches_for_backup(backup_dir, repo)
        elapsed = time.monotonic() - t0

        nb_new   = sum(1 for s in results.values() if s == "genere")
        nb_deja  = sum(1 for s in results.values() if s == "deja_present")
        nb_ident = sum(1 for s in results.values() if s == "identique")

        print(f"\n  {GRN}✓{RST}  {BLD}{nb_new}{RST} .patch genere(s)  "
              f"{DIM}{nb_deja} deja present(s)  {nb_ident} identique(s) a upstream{RST}  "
              f"({elapsed:.1f}s)")
        print(f"\n  Vous pouvez maintenant reinitialiser le fork,")
        print(f"  puis relancer sans --prepare pour la restauration.\n")
        return

    # ── Verification de coherence du backup ───────────────────────────────────
    integrity_warnings = check_backup_integrity(backup_dir)
    if integrity_warnings:
        print(f"\n  {YLW}[VERIF BACKUP]{RST}")
        for w in integrity_warnings:
            print(f"    {YLW}⚠{RST}  {w}")
        print()

    # ── MODE restauration ─────────────────────────────────────────────────────
    mod_root  = backup_dir / "2_fichiers_modifies"
    nb_patch  = sum(1 for _ in mod_root.rglob("*.patch")) if (do_modifies and mod_root.exists()) else 0
    nb_modifs = sum(
        1 for f in mod_root.rglob("*")
        if f.is_file() and f.suffix not in (".patch", ".html")
    ) if (do_modifies and mod_root.exists()) else 0
    nb_crees  = sum(
        1 for _ in (backup_dir / "1_fichiers_crees").rglob("*") if _.is_file()
    ) if (do_crees and (backup_dir / "1_fichiers_crees").exists()) else 0

    if nb_patch == 0 and nb_modifs > 0 and not args.dry_run:
        print(f"\n  {YLW}[ATTENTION]{RST} Aucun fichier .patch dans ce backup.")
        print(f"  Les {nb_modifs} fichiers modifies seront {YLW}copies en entier{RST}.")
        print(f"  Pour une application selective, lancez d'abord :")
        print(f"    {DIM}python restaure_sauvegarde_tasmota.py --prepare{RST}\n")
        rep = input("Continuer quand meme ? (o/n) : ").strip().lower()
        if rep != "o":
            print("Annule.")
            return

    # ── Dossier de destination ────────────────────────────────────────────────
    if args.dest:
        dest_dir = Path(args.dest)
        if not dest_dir.exists() or not dest_dir.is_dir():
            print(f"{RED}[ERREUR]{RST} Dossier de destination introuvable : {dest_dir}")
            sys.exit(1)
    else:
        default_dest = find_git_root(SCRIPT_DIR)
        dest_dir = prompt_dir("Dossier de destination (fork Tasmota cible)",
                              default=default_dest)

    # ── Resume et confirmation ────────────────────────────────────────────────
    mod_mode  = f"{GRN}via .patch{RST}" if nb_patch > 0 else f"{YLW}copie complete{RST}"
    filt_info = (f"  Filtre            : {CYN}{' | '.join(args.files)}{RST}\n"
                 if args.files else "")
    print(f"\n  Source backup     : {CYN}{backup_dir}{RST}")
    print(f"  Destination       : {CYN}{dest_dir}{RST}")
    print(f"{filt_info}", end="")
    if do_crees:
        print(f"  Fichiers crees    : {BLD}{nb_crees}{RST}  (copie complete)")
    else:
        print(f"  Fichiers crees    : {DIM}[ignore]{RST}")
    if do_modifies:
        print(f"  Fichiers modifies : {BLD}{nb_modifs}{RST}  ({mod_mode})")
    else:
        print(f"  Fichiers modifies : {DIM}[ignore]{RST}")
    if not args.dry_run:
        print(f"  Rollback          : {DIM}<sauvegarde>/_rollback_<timestamp>/{RST}")

    mode_tag = f"  {YLW}[DRY-RUN]{RST}" if args.dry_run else ""
    confirm  = input(f"\n{BLD}Confirmer la restauration ?{RST}{mode_tag} (o/n) : ").strip().lower()
    if confirm != "o":
        print("Annule.")
        return

    # ── Initialisation rollback et logger ─────────────────────────────────────
    logger = Logger()
    logger.log(f"Backup      : {backup_dir}")
    logger.log(f"Destination : {dest_dir}")
    logger.log(f"Mode        : {'dry-run' if args.dry_run else 'restauration'}")
    if args.files:
        logger.log(f"Filtre      : {' | '.join(args.files)}")

    rollback_dir: "Path | None" = None
    if not args.dry_run:
        ts           = datetime.now().strftime("%Y%m%d_%H%M%S")
        rollback_dir = backup_dir / f"_rollback_{ts}"
        logger.log(f"Rollback    : {rollback_dir}")

    # ── Execution ─────────────────────────────────────────────────────────────
    nb_steps  = (1 if do_crees else 0) + (1 if do_modifies else 0)
    step_num  = 0
    r_created  = []
    r_modified = []

    if do_crees:
        step_num += 1
        section("Copie des fichiers crees", step=step_num, total=nb_steps)
        print(f"  {DIM}{nb_crees} fichier(s) a copier{RST}\n")
        r_created = copy_created_files(backup_dir, dest_dir,
                                       dry_run=args.dry_run,
                                       rollback_dir=rollback_dir,
                                       logger=logger,
                                       only_files=args.files)

    if do_modifies:
        step_num += 1
        section("Application des modifications", step=step_num, total=nb_steps)
        print(f"  {DIM}{nb_modifs} fichier(s)  |  {nb_patch} .patch disponible(s){RST}\n")
        r_modified = apply_modified_files(backup_dir, dest_dir,
                                          dry_run=args.dry_run,
                                          rollback_dir=rollback_dir,
                                          logger=logger,
                                          only_files=args.files)

    # ── Rapport et log ────────────────────────────────────────────────────────
    t_total = time.monotonic() - t_global
    print_summary(r_created, r_modified, t_total)

    if rollback_dir and rollback_dir.exists():
        rb_count = sum(1 for _ in rollback_dir.rglob("*") if _.is_file())
        print(f"  {DIM}Rollback : {rollback_dir.name}  ({rb_count} fichier(s)){RST}")

    # -- Rappel des fichiers a supprimer manuellement
    suppr_file = backup_dir / "3_fichiers_supprimes" / "deleted.txt"
    if suppr_file.exists() and not args.files:
        suppr = [l.strip() for l in
                 suppr_file.read_text(encoding='utf-8').splitlines() if l.strip()]
        if suppr:
            print(f"\n  {YLW}[INFO]{RST} Ce backup reference {len(suppr)} fichier(s) "
                  f"supprime(s) dans votre fork.")
            print(f"  A supprimer manuellement dans la destination si necessaire :")
            for rel in suppr[:5]:
                print(f"    {RED}-{RST}  {rel}")
            if len(suppr) > 5:
                print(f"    {DIM}... et {len(suppr) - 5} autre(s). "
                      f"Voir 3_fichiers_supprimes/deleted.txt{RST}")

    if not args.dry_run:
        log_path = backup_dir / f"log_restauration_{datetime.now().strftime('%d%m%Y_%H%M%S')}.txt"
        logger.save(log_path)


if __name__ == "__main__":
    main()
