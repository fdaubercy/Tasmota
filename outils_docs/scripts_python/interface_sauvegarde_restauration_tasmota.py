# -*- coding: utf-8 -*-
"""
interface_tasmota.py  -  Interface graphique pour les scripts Tasmota

Lance genere_sauvegarde_tasmota.py, restaure_sauvegarde_tasmota.py et
synchronise_upstream_tasmota.py avec un sélecteur d'options par cases à cocher.

Les paquets Python manquants sont installés automatiquement au démarrage.
"""
import sys
import os
import subprocess
import threading
import queue
import re
from pathlib import Path
from datetime import datetime

# ── Auto-installation des dépendances ─────────────────────────────────────────
# Les 3 scripts Tasmota n'utilisent que la bibliothèque standard Python.
# Ajoutez ici d'éventuels paquets tiers si vous en avez besoin.
REQUIRED_PACKAGES: list = []


def _ensure_packages(packages: list) -> None:
    for pkg in packages:
        try:
            __import__(pkg)
        except ImportError:
            print(f"  Installation automatique de '{pkg}'...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "--quiet", pkg]
                )
                print(f"  '{pkg}' installé avec succès.")
            except subprocess.CalledProcessError:
                print(f"  ERREUR : impossible d'installer '{pkg}'.")
                print(f"  Installez-le manuellement : pip install {pkg}")
                sys.exit(1)


_ensure_packages(REQUIRED_PACKAGES)

# ── Tkinter ───────────────────────────────────────────────────────────────────
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError:
    print("ERREUR : le module 'tkinter' est introuvable.")
    if sys.platform.startswith("linux"):
        print("  Sur Ubuntu/Debian : sudo apt install python3-tk")
        print("  Sur Fedora/RHEL   : sudo dnf install python3-tkinter")
    elif sys.platform == "darwin":
        print("  Sur macOS : réinstallez Python depuis python.org (inclut tkinter)")
    elif sys.platform == "win32":
        print("  Sur Windows : réinstallez Python en cochant 'tcl/tk and IDLE'")
    sys.exit(1)

# ── Constantes visuelles ──────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def _find_git_root() -> "Path | None":
    p = SCRIPT_DIR
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    return None


def _backup_path_today() -> "Path | None":
    """Retourne le chemin du dossier de sauvegarde du jour (même logique que le script)."""
    repo = _find_git_root()
    if repo is None:
        return None
    return repo.parent / f"Tasmota-sauvegarde {datetime.now().strftime('%d%m%Y')}"

BG_DARK  = "#1e1e1e"
BG_MID   = "#252526"
BG_PANEL = "#2d2d2d"
BG_ENTRY = "#3c3c3c"
BG_TERM  = "#0d1117"
FG_TEXT  = "#d4d4d4"
FG_DIM   = "#858585"
FG_HINT  = "#9cdcfe"
FG_GREEN = "#4ec9b0"
FG_AMBER = "#dcdcaa"
FG_RED   = "#f44747"
BTN_BLU  = "#0e639c"
BTN_RED  = "#7a1818"
FONT_UI  = ("Segoe UI", 9)
FONT_MON = ("Consolas", 9)
FONT_H1  = ("Segoe UI", 10, "bold")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


# ── Console de sortie ─────────────────────────────────────────────────────────

class OutputConsole(tk.Frame):
    """Zone de sortie style terminal avec gestion ANSI, CR/LF et entrée interactive."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_DARK, **kwargs)
        self._process = None
        self._build()

    def _build(self):
        text_frame = tk.Frame(self, bg=BG_DARK)
        text_frame.pack(fill="both", expand=True)

        self.text = tk.Text(
            text_frame, wrap="word", state="disabled",
            bg=BG_TERM, fg=FG_TEXT,
            font=FONT_MON, relief="flat",
            insertbackground="white",
            selectbackground="#264f78",
            padx=6, pady=4,
        )
        sb = ttk.Scrollbar(text_frame, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        self.text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Mark curseur d'insertion : avance avec chaque insert, revient au début
        # de la ligne courante sur \r (pour gérer la barre de progression).
        self.text.mark_set("_ins", "end")
        self.text.mark_gravity("_ins", "right")

        # Séparateur
        tk.Frame(self, bg="#444", height=1).pack(fill="x")

        # Ligne d'entrée interactive
        inp_row = tk.Frame(self, bg=BG_PANEL)
        inp_row.pack(fill="x")

        tk.Label(
            inp_row, text=" Entrée : ", fg=FG_DIM, bg=BG_PANEL, font=FONT_MON
        ).pack(side="left", pady=4)

        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            inp_row, textvariable=self.input_var,
            bg=BG_ENTRY, fg=FG_TEXT, insertbackground="white",
            font=FONT_MON, relief="flat", state="disabled",
        )
        self.input_entry.pack(side="left", fill="x", expand=True, pady=4, padx=2)
        self.input_entry.bind("<Return>", lambda _: self._send())

        self.send_btn = tk.Button(
            inp_row, text="Envoyer ↵",
            bg=BTN_BLU, fg="white", font=FONT_UI,
            relief="flat", state="disabled",
            command=self._send,
        )
        self.send_btn.pack(side="right", padx=(2, 6), pady=4)

    def set_process(self, process):
        self._process = process
        s = "normal" if process else "disabled"
        self.send_btn.config(state=s)
        self.input_entry.config(state=s)
        if process:
            self.input_entry.focus_set()

    def _send(self):
        if not self._process or self._process.poll() is not None:
            return
        line = self.input_var.get() + "\n"
        self.input_var.set("")
        try:
            self._process.stdin.write(line)
            self._process.stdin.flush()
        except (OSError, BrokenPipeError):
            pass
        self.append(f">> {line}")

    def clear(self):
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.mark_set("_ins", "end")
        self.text.config(state="disabled")

    def append(self, data: str):
        """Insère du texte en gérant \\r (barre de progression) et \\n.

        Le mark _ins joue le rôle de curseur :
          - texte normal → inséré à _ins, le mark avance (gravité 'right')
          - \\r          → efface le contenu de la ligne courante et ramène
                           _ins en colonne 0 (prêt à réécrire par-dessus)
          - \\n          → insère \\n à _ins, le mark passe à la ligne suivante
        """
        clean = strip_ansi(data)
        if not clean:
            return
        self.text.config(state="normal")

        i = 0
        while i < len(clean):
            ch = clean[i]
            if ch == "\r":
                pos  = self.text.index("_ins")
                line = pos.split(".")[0]
                self.text.delete(f"{line}.0", f"{line}.end")
                self.text.mark_set("_ins", f"{line}.0")
                i += 1
            elif ch == "\n":
                self.text.insert("_ins", "\n")
                i += 1
            else:
                j = i + 1
                while j < len(clean) and clean[j] not in ("\r", "\n"):
                    j += 1
                self.text.insert("_ins", clean[i:j])
                i = j

        self.text.see("_ins")
        self.text.config(state="disabled")


# ── Gestionnaire d'exécution de script ───────────────────────────────────────

class ScriptRunner:
    """Lance un script en sous-processus et achemine la sortie vers la console."""

    def __init__(self, console: OutputConsole, on_start=None, on_finish=None):
        self.console   = console
        self.on_start  = on_start
        self.on_finish = on_finish
        self._proc     = None
        self._thread   = None
        self._queue: queue.Queue = queue.Queue()

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def run(self, cmd: list, cwd=None):
        if self.is_running:
            messagebox.showwarning(
                "Script en cours",
                "Un script est déjà en cours d'exécution.\n"
                "Arrêtez-le avant d'en lancer un nouveau.",
            )
            return

        self.console.clear()
        ts = datetime.now().strftime("%H:%M:%S")
        args_str = " ".join(str(c) for c in cmd)
        self.console.append(f"[{ts}]  {args_str}\n\n")

        if self.on_start:
            self.on_start()

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        try:
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=cwd or SCRIPT_DIR,
                env=env,
            )
        except Exception as exc:
            self.console.append(f"\nERREUR au lancement :\n{exc}\n")
            if self.on_finish:
                self.on_finish(1)
            return

        self.console.set_process(self._proc)

        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()
        self._poll()

    def stop(self):
        if self.is_running:
            try:
                self._proc.terminate()
            except Exception:
                pass

    def _reader(self):
        # readline() se débloque dès qu'un \n arrive du processus fils
        # (qui flush sur chaque ligne grâce à line_buffering=True + PYTHONUNBUFFERED).
        try:
            for line in self._proc.stdout:
                self._queue.put(("data", line))
        except Exception:
            pass
        finally:
            self._proc.wait()
            self._queue.put(("done", self._proc.returncode))

    def _poll(self):
        # Collecter TOUT ce qui est disponible dans la queue en un seul passage,
        # puis faire un seul appel append() pour éviter de surcharger Tkinter.
        chunks = []
        done_rc = None
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "data":
                    chunks.append(payload)
                elif kind == "done":
                    done_rc = payload
                    break
        except queue.Empty:
            pass

        if chunks:
            self.console.append("".join(chunks))

        if done_rc is not None:
            ts = datetime.now().strftime("%H:%M:%S")
            ok = done_rc == 0
            msg = "Terminé avec succès" if ok else f"Terminé avec erreur (code {done_rc})"
            self.console.append(f"\n[{ts}]  {msg}\n")
            self.console.set_process(None)
            if self.on_finish:
                self.on_finish(done_rc)
            return

        self.console.text.after(25, self._poll)


# ── Classe de base pour les onglets ───────────────────────────────────────────

class TabBase(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent, bg=BG_DARK)
        self.runner: ScriptRunner = None
        self._run_btn:    tk.Button = None
        self._stop_btn:   tk.Button = None
        self._status_lbl: tk.Label  = None

    # ── Widgets réutilisables ──────────────────────────────────────────────────

    def _section(self, title: str) -> tk.LabelFrame:
        f = tk.LabelFrame(
            self, text=f"  {title}  ",
            bg=BG_DARK, fg=FG_HINT, font=FONT_UI,
            relief="groove", bd=1,
        )
        f.pack(fill="x", padx=10, pady=(8, 4))
        return f

    def _btn_row(self, label: str, cmd) -> tk.Frame:
        row = tk.Frame(self, bg=BG_DARK)
        row.pack(fill="x", padx=10, pady=4)

        self._run_btn = tk.Button(
            row, text=f"▶  {label}",
            bg=BTN_BLU, fg="white",
            font=FONT_H1, relief="flat",
            padx=14, pady=7,
            command=cmd,
        )
        self._run_btn.pack(side="left")

        self._stop_btn = tk.Button(
            row, text="■  Arrêter",
            bg=BTN_RED, fg="white",
            font=FONT_UI, relief="flat",
            padx=10, pady=7, state="disabled",
            command=lambda: self.runner and self.runner.stop(),
        )
        self._stop_btn.pack(side="left", padx=(6, 0))

        self._status_lbl = tk.Label(
            row, text="✓  Prêt", fg=FG_GREEN, bg=BG_DARK, font=FONT_UI
        )
        self._status_lbl.pack(side="left", padx=12)
        return row

    def _console(self) -> OutputConsole:
        c = OutputConsole(self)
        c.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        return c

    def _cb(self, parent, text: str, var: tk.BooleanVar) -> tk.Checkbutton:
        return tk.Checkbutton(
            parent, text=f"  {text}", variable=var,
            bg=BG_DARK, fg=FG_TEXT,
            selectcolor=BG_ENTRY,
            activebackground=BG_DARK, activeforeground=FG_TEXT,
            font=FONT_UI,
        )

    def _dir_field(self, parent, label: str, row: int,
                   var: tk.StringVar, optional: bool = False):
        tk.Label(
            parent, text=label, fg=FG_TEXT, bg=BG_DARK, font=FONT_UI
        ).grid(row=row, column=0, sticky="w", padx=10, pady=4)

        ent = tk.Entry(
            parent, textvariable=var, width=50,
            bg=BG_ENTRY, fg=FG_TEXT, insertbackground="white",
            font=FONT_MON, relief="flat",
        )
        ent.grid(row=row, column=1, sticky="ew", padx=(4, 2), pady=4)

        tk.Button(
            parent, text="Parcourir…",
            bg=BG_PANEL, fg=FG_TEXT, relief="flat", font=FONT_UI,
            command=lambda v=var: self._browse(v),
        ).grid(row=row, column=2, padx=(2, 10), pady=4)

        hint = "(optionnel)" if optional else ""
        tk.Label(parent, text=hint, fg=FG_DIM, bg=BG_DARK,
                 font=("Segoe UI", 8)).grid(row=row, column=3, sticky="w")

    @staticmethod
    def _browse(var: tk.StringVar):
        d = filedialog.askdirectory(title="Sélectionner un dossier")
        if d:
            var.set(d)

    # ── Callbacks on_start / on_finish ────────────────────────────────────────

    def _on_start(self):
        self._run_btn.config(state="disabled", bg="#444")
        self._stop_btn.config(state="normal")
        self._status_lbl.config(text="⏳  En cours…", fg=FG_AMBER)

    def _on_finish(self, rc: int):
        self._run_btn.config(state="normal", bg=BTN_BLU)
        self._stop_btn.config(state="disabled")
        self._status_lbl.config(
            text="✓  Succès" if rc == 0 else "✗  Erreur",
            fg=FG_GREEN if rc == 0 else FG_RED,
        )


# ── Onglet Sauvegarde ─────────────────────────────────────────────────────────

class SauvegardeTab(TabBase):

    def __init__(self, parent):
        super().__init__(parent)
        self._backup_path: "Path | None" = None
        self._build()

    def _build(self):
        # Options
        opts = self._section("genere_sauvegarde_tasmota.py")

        self.v_dryrun = tk.BooleanVar()
        self.v_open   = tk.BooleanVar()

        self._cb(
            opts,
            "Dry-run  —  simule la sauvegarde sans écrire aucun fichier",
            self.v_dryrun,
        ).pack(anchor="w", padx=10, pady=5)
        self._cb(
            opts,
            "Ouvrir INDEX.html dans le navigateur à la fin de la sauvegarde",
            self.v_open,
        ).pack(anchor="w", padx=10, pady=(0, 8))

        # Chemin du dossier de sauvegarde prévu
        path_frame = tk.Frame(opts, bg=BG_DARK)
        path_frame.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(
            path_frame, text="Dossier créé :", fg=FG_DIM, bg=BG_DARK, font=FONT_UI
        ).pack(side="left")

        self._backup_lbl = tk.Label(
            path_frame, text="", fg=FG_HINT, bg=BG_DARK,
            font=FONT_MON, anchor="w",
        )
        self._backup_lbl.pack(side="left", padx=(6, 10))

        self._open_btn = tk.Button(
            path_frame, text="📂  Ouvrir dans l'explorateur",
            bg=BG_PANEL, fg=FG_TEXT, relief="flat", font=FONT_UI,
            command=self._open_folder,
        )
        self._open_btn.pack(side="left")

        self._refresh_path_label()

        # Boutons
        self._btn_row("Lancer la sauvegarde", self._run)

        # Console
        console = self._console()
        self.runner = ScriptRunner(
            console, on_start=self._on_start, on_finish=self._on_finish_sv
        )

    def _refresh_path_label(self):
        """Met à jour l'affichage du chemin de sauvegarde (recalculé à chaque lancement)."""
        self._backup_path = _backup_path_today()
        if self._backup_path:
            self._backup_lbl.config(text=str(self._backup_path))
        else:
            self._backup_lbl.config(
                text="(repo git introuvable)", fg=FG_RED
            )

    def _open_folder(self):
        if not self._backup_path:
            messagebox.showinfo("Chemin introuvable",
                                "Impossible de déterminer le dossier de sauvegarde.")
            return
        if not self._backup_path.exists():
            messagebox.showinfo(
                "Dossier absent",
                f"Le dossier n'existe pas encore :\n{self._backup_path}\n\n"
                "Lancez d'abord la sauvegarde (sans Dry-run).",
            )
            return
        if sys.platform == "win32":
            os.startfile(self._backup_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(self._backup_path)])
        else:
            subprocess.Popen(["xdg-open", str(self._backup_path)])

    def _run(self):
        self._refresh_path_label()
        cmd = [sys.executable, "-u",
               str(SCRIPT_DIR / "genere_sauvegarde_tasmota.py")]
        if self.v_dryrun.get():
            cmd.append("--dry-run")
        if self.v_open.get():
            cmd.append("--open")
        self.runner.run(cmd)

    def _on_finish_sv(self, rc: int):
        self._on_finish(rc)
        # Rafraîchir le label (la date peut avoir changé à minuit)
        self._refresh_path_label()


# ── Onglet Restauration ───────────────────────────────────────────────────────

class RestaurationTab(TabBase):

    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        # Options
        opts = self._section("restaure_sauvegarde_tasmota.py")
        opts.columnconfigure(1, weight=1)

        self.v_source  = tk.StringVar()
        self.v_dest    = tk.StringVar()
        self.v_filter  = tk.StringVar()
        self.v_dryrun  = tk.BooleanVar()
        self.v_list    = tk.BooleanVar()
        self.v_prepare = tk.BooleanVar()

        # Dossiers
        self._dir_field(opts, "Sauvegarde source  (-s) :", 0,
                        self.v_source, optional=True)
        self._dir_field(opts, "Destination          (-d) :", 1,
                        self.v_dest,   optional=True)

        # Filtre
        tk.Label(opts, text="Filtre  (-f) :", fg=FG_TEXT, bg=BG_DARK,
                 font=FONT_UI).grid(row=2, column=0, sticky="w",
                                    padx=10, pady=4)
        filt_frame = tk.Frame(opts, bg=BG_DARK)
        filt_frame.grid(row=2, column=1, sticky="ew", padx=(4, 10), pady=4)
        tk.Entry(
            filt_frame, textvariable=self.v_filter, width=35,
            bg=BG_ENTRY, fg=FG_TEXT, insertbackground="white",
            font=FONT_MON, relief="flat",
        ).pack(side="left")
        tk.Label(
            filt_frame, text="  (sous-chaînes séparées par des espaces, ex : berry webcam)",
            fg=FG_DIM, bg=BG_DARK, font=("Segoe UI", 8),
        ).pack(side="left")

        # Dossiers à restaurer
        tk.Label(opts, text="Dossiers  (--dossiers) :", fg=FG_TEXT, bg=BG_DARK,
                 font=FONT_UI).grid(row=3, column=0, sticky="w", padx=10, pady=4)

        doss_frame = tk.Frame(opts, bg=BG_DARK)
        doss_frame.grid(row=3, column=1, sticky="w", padx=(4, 10), pady=4)

        self.v_dossiers = tk.StringVar(value="tous")
        for val, lbl in [("tous", "Tous (défaut)"),
                         ("crees", "Fichiers créés seulement"),
                         ("modifies", "Fichiers modifiés seulement")]:
            tk.Radiobutton(
                doss_frame, text=lbl, variable=self.v_dossiers, value=val,
                bg=BG_DARK, fg=FG_TEXT, selectcolor=BG_ENTRY,
                activebackground=BG_DARK, activeforeground=FG_TEXT,
                font=FONT_UI,
            ).pack(side="left", padx=(0, 16))

        # Cases à cocher
        cb_frame = tk.Frame(opts, bg=BG_DARK)
        cb_frame.grid(row=4, column=0, columnspan=4, sticky="w",
                      padx=10, pady=(4, 8))

        self._cb(cb_frame, "Dry-run", self.v_dryrun).pack(
            side="left", padx=(0, 20))
        self._cb(cb_frame, "Afficher le contenu (--list)", self.v_list).pack(
            side="left", padx=(0, 20))
        self._cb(cb_frame, "Générer les .patch (--prepare)", self.v_prepare).pack(
            side="left")

        # Note sur les invites interactives
        note = tk.Label(
            self,
            text="ℹ  Pour chaque fichier modifié, le script affiche le diff et demande confirmation.\n"
                 "   Répondez dans le champ 'Entrée' :  o = oui  |  n = ignorer  |  t = tous  |  q = quitter",
            fg=FG_AMBER, bg=BG_DARK, font=("Segoe UI", 8), justify="left",
        )
        note.pack(anchor="w", padx=12, pady=(0, 4))

        # Boutons
        self._btn_row("Lancer la restauration", self._run)

        # Console
        console = self._console()
        self.runner = ScriptRunner(
            console, on_start=self._on_start, on_finish=self._on_finish
        )

    def _run(self):
        cmd = [sys.executable, "-u",
               str(SCRIPT_DIR / "restaure_sauvegarde_tasmota.py")]

        src = self.v_source.get().strip()
        dst = self.v_dest.get().strip()
        flt = self.v_filter.get().strip()

        if src:
            cmd.extend(["-s", src])
        if dst:
            cmd.extend(["-d", dst])
        for token in flt.split():
            cmd.extend(["-f", token])

        dossiers = self.v_dossiers.get()
        if dossiers != "tous":
            cmd.extend(["--dossiers", dossiers])

        if self.v_list.get():
            cmd.append("--list")
        if self.v_prepare.get():
            cmd.append("--prepare")
        if self.v_dryrun.get():
            cmd.append("--dry-run")

        self.runner.run(cmd)


# ── Onglet Synchronisation ────────────────────────────────────────────────────

class SynchronisationTab(TabBase):

    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        # Options
        opts = self._section("synchronise_upstream_tasmota.py")

        self.v_dryrun = tk.BooleanVar()
        self._cb(
            opts,
            "Dry-run  —  montre les conflits potentiels sans modifier aucun fichier",
            self.v_dryrun,
        ).pack(anchor="w", padx=10, pady=5)

        # Note interactive
        note_txt = (
            "ℹ  La synchronisation est entièrement interactive.\n"
            "   • Pour chaque conflit : tapez  M  (garder le mien),  U  (prendre upstream),\n"
            "     E  (éditer dans VS Code)  ou  Q  (annuler le rebase).\n"
            "   • Pour les confirmations : tapez  o  ou  n.\n"
            "   → Utilisez le champ 'Entrée' de la console ci-dessous."
        )
        tk.Label(
            opts, text=note_txt,
            fg=FG_AMBER, bg=BG_DARK,
            font=("Segoe UI", 8), justify="left",
        ).pack(anchor="w", padx=10, pady=(0, 8))

        # Boutons
        self._btn_row("Lancer la synchronisation", self._run)

        # Console
        console = self._console()
        self.runner = ScriptRunner(
            console, on_start=self._on_start, on_finish=self._on_finish
        )

    def _run(self):
        cmd = [sys.executable, "-u",
               str(SCRIPT_DIR / "synchronise_upstream_tasmota.py")]
        if self.v_dryrun.get():
            cmd.append("--dry-run")
        self.runner.run(cmd)


# ── Fenêtre principale ────────────────────────────────────────────────────────

class TasmotaApp:

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Gestionnaire Tasmota")
        root.geometry("960x720")
        root.minsize(700, 500)
        root.configure(bg=BG_DARK)

        self._apply_style()
        self._build()

    def _apply_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TNotebook", background=BG_MID, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=BG_PANEL, foreground=FG_DIM,
            padding=[14, 7], font=FONT_UI,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", BG_DARK)],
            foreground=[("selected", FG_TEXT)],
        )
        style.configure("TScrollbar", background=BG_PANEL,
                        troughcolor=BG_DARK, borderwidth=0)

    def _build(self):
        # En-tête
        hdr = tk.Frame(self.root, bg="#11141a", pady=10)
        hdr.pack(fill="x")
        tk.Label(
            hdr,
            text="  Gestionnaire Tasmota",
            fg=FG_HINT, bg="#11141a",
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left")
        tk.Label(
            hdr,
            text=f"  Scripts : {SCRIPT_DIR}",
            fg=FG_DIM, bg="#11141a",
            font=("Segoe UI", 8),
        ).pack(side="right", padx=10)

        # Notebook
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=6, pady=6)

        sv = SauvegardeTab(nb)
        rs = RestaurationTab(nb)
        sy = SynchronisationTab(nb)

        nb.add(sv, text="  Sauvegarde  ")
        nb.add(rs, text="  Restauration  ")
        nb.add(sy, text="  Synchronisation  ")

        # Pied de page
        foot = tk.Frame(self.root, bg=BG_PANEL, pady=3)
        foot.pack(fill="x", side="bottom")
        tk.Label(
            foot,
            text="Python " + sys.version.split()[0],
            fg=FG_DIM, bg=BG_PANEL, font=("Segoe UI", 8),
        ).pack(side="right", padx=10)
        tk.Label(
            foot,
            text="Utilisez le champ 'Entrée' de chaque onglet pour répondre "
                 "aux invites interactives des scripts.",
            fg=FG_DIM, bg=BG_PANEL, font=("Segoe UI", 8),
        ).pack(side="left", padx=10)


# ── Point d'entrée ────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    TasmotaApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
