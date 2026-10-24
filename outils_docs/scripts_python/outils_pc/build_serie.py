"""Execution en serie des `pio run` de la page Build et televersement : refus, suivi, arret.

Un lancement = des lignes (env, methode COM ou OTA, port, IP) et des actions cochees parmi
compiler / upload / buildfs / uploadfs. Les envs passent l'un apres l'autre, un seul fils pio a la
fois. Dans un env, ordre fixe : compiler -> televerser le firmware -> construire le FS -> televerser
le FS. Un echec arrete CET env (actions suivantes « annulee »), les autres continuent (choix 8 de la
spec docs/superpowers/specs/2026-10-24-page-build-televersement-design.md).

Commandes (choix 9) : compiler = `run -e X` ; upload = `run -e X -t upload` (compile si besoin : si
« compiler » est aussi coche, seul upload part) ; buildfs = `-t buildfs` ; uploadfs par cable =
`-t uploadfs`. Port COM par `--upload-port` (jamais PLATFORMIO_UPLOAD_PORT ni
PLATFORMIO_EXTRA_SCRIPTS : ils entrent dans l'empreinte du projet et purgeraient .pio/build).
En OTA, la page envoie elle-meme (build_ota_fs, spec choix 7 revise) : upload = `run -e X` puis la
fonction injectee `ota_firmware` (firmware de .pio/build/<env>/ par /u2) ; uploadfs = buildfs (s'il
n'est pas deja coche), puis les fichiers de .pio/build/<env>/littlefs.bin (l'image du buildfs, extraite
dans un dossier temporaire par build_ota_fs.extrait_image) envoyes par la fonction injectee `ota_fs`
(/ufsu). Jamais littlefs_data : post_esp32.py le remplit a chaque edition des liens (choix 10.1).

Refus avant de lancer (choix 11) : build deja en cours (garde_build), port COM tenu ou absent, deux
envois COM sur le meme port, IP OTA vide. Le controle « build en cours » est refait avant chaque env
suivant : la serie attend (evenement `attente`) puis reprend. Pendant qu'un fils de la serie tourne,
rien n'est controle : la serie ne se bloque pas sur ses propres `pio run`.

Evenements numerotes (modele maintenance/synchro_fork_session.Session, rejoues par `depuis`) :
  debut    env=None : lignes et actions du lancement ; env=X : debut d'un env
  etape    env, action, etape, pourcent, detail (+ commande au depart d'un fils)
  duree    env, action, etape, secondes : emis des la fin de l'etape
  ligne    env, action, texte (sans ANSI)
  echec    env, action, motif, extrait
  fin_env  env, resultat (succes | echec | arrete), statuts {action: succes | echec | annulee}
  attente  env, builds (liste vide = reprise)
  fin      env=None, resultat (termine | arrete), succes, echecs, non_lances, fichiers_modifies

Journal complet de chaque fils (sans ANSI) dans <dossier>/journaux/ ; nombre de .o du dernier
succes de chaque env dans <dossier>/references.json (base du % de compilation).
"""

import ipaddress
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import build_envs
import build_ota_fs
from build_progression import ETAPE_COMPILATION, ETAPE_ENVOI, ETAPE_LIENS, ETAPE_PREBUILD, Suivi, retire_ansi

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
PIO_PENV = Path.home() / ".platformio" / "penv" / "Scripts" / "pio.exe"
ORDRE = ("compiler", "upload", "buildfs", "uploadfs")
ENVOIS = {"upload", "uploadfs"}
ETAPE_ENVOI_FS = "Envoi des fichiers"
FICHIERS_MODIFIES = ["platformio_override.ini", "tasmota/user_config_override.h"]
MAX_EVENEMENTS = 50000
DETECTION_IMPOSSIBLE = "détection impossible"
NOM_ENV = re.compile(r"[A-Za-z0-9_.-]+")


@dataclass
class Ligne:
    env: str
    methode: str          # "com" | "ota"
    port: str             # COMn (methode com)
    ip: str               # IPv4 (methode ota)


# -- fonctions par defaut (injectables pour les bancs) -------------------------------------------------

def garde_build():
    """Module .claude/hooks/garde_build.py, importe sans executer son main() (qui lit stdin)."""
    hooks = str(DEPOT / ".claude" / "hooks")
    if hooks not in sys.path:
        sys.path.append(hooks)                          # en dernier : ne masque aucun module
    import garde_build as module
    return module


def builds_en_cours_defaut():
    """Libelles des builds en cours, [] si aucun, None si la detection a echoue (PowerShell)."""
    try:
        return garde_build().builds_en_cours()
    except (OSError, subprocess.TimeoutExpired, ImportError):
        return None


def port_libre_defaut(port):
    """"libre", "tenu" (ouvert par un autre outil), "absent", ou "inconnu" (pyserial absent)."""
    try:
        import serial
        from serial.tools import list_ports
    except ImportError:
        return "inconnu"
    if port.upper() not in {p.device.upper() for p in list_ports.comports()}:
        return "absent"
    s = serial.Serial()
    s.port, s.dtr, s.rts = port, False, False          # pas de reset de l'ESP32 a l'ouverture
    try:
        s.open()
    except serial.SerialException as erreur:
        texte = str(erreur)
        return "absent" if "FileNotFoundError" in texte else "tenu"
    s.close()
    return "libre"


def commande_pio(pio=None):
    """Commande de pio : `pio`, sinon BUILD_WEB_PIO (bancs), sinon le pio du penv.

    Un `.py` (le faux pio des bancs, stdlib seule) part avec le Python courant, sans `site` (-S) :
    trois fois plus rapide a demarrer avec le penv de PlatformIO (0,2 s au lieu de 0,6 s).
    """
    chemin = str(pio or os.environ.get("BUILD_WEB_PIO") or PIO_PENV)
    return [sys.executable, "-S", "-u", chemin] if chemin.lower().endswith(".py") else [chemin]


def tue_arbre(proc):
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        proc.kill()


# -- la serie ---------------------------------------------------------------------------------------

class Serie:
    def __init__(self, racine, dossier, pio=None, builds_en_cours=builds_en_cours_defaut,
                 port_libre=port_libre_defaut, ota_fs=build_ota_fs.envoie_fs_ota,
                 ota_firmware=build_ota_fs.envoie_firmware_ota, sondage=5.0):
        self.racine = Path(racine)
        self.dossier = Path(dossier)
        self.commande_pio = commande_pio(pio)
        self.builds_en_cours = builds_en_cours
        self.port_libre = port_libre
        self.ota_fs = ota_fs
        self.ota_firmware = ota_firmware
        self.sondage = sondage
        self.verrou = threading.Condition()
        self.evenements = []
        self.numero = 0
        self._actif = False
        self._proc = None
        self._arret = False
        self._arret_immediat = False

    # -- evenements -------------------------------------------------------------------------------------

    def _ajoute(self, type_, env, **champs):
        with self.verrou:
            self.numero += 1
            self.evenements.append({"n": self.numero, "type": type_, "env": env, **champs})
            del self.evenements[:-MAX_EVENEMENTS]
            self.verrou.notify_all()

    def depuis(self, n, attente=15.0):
        """Evenements de numero > n ; attend au plus `attente` s s'il n'y en a pas (flux SSE)."""
        with self.verrou:
            if self.numero <= n:
                self.verrou.wait(attente)
            return [e for e in self.evenements if e["n"] > n]

    def en_cours(self):
        with self.verrou:
            return self._actif

    # -- controle avant lancement ---------------------------------------------------------------------

    def controle(self, lignes, actions):
        """Motifs de refus (liste vide = lancement possible)."""
        motifs = []
        if self.en_cours():
            motifs.append("un lancement est déjà en cours")
        if not actions or not set(actions) <= set(ORDRE):
            motifs.append(f"actions invalides : {sorted(actions)!r} (attendu parmi {', '.join(ORDRE)})")
        if not lignes:
            motifs.append("aucun environnement coché")
        envoi = bool(set(actions) & ENVOIS)
        connus = {e.nom: e for e in build_envs.liste_envs(self.racine)}
        vus, ports = set(), {}
        for ligne in lignes:
            nom = ligne.env
            if nom in vus:
                motifs.append(f"{nom} : coché deux fois")
            vus.add(nom)
            if not NOM_ENV.fullmatch(nom or "") or nom not in connus:
                motifs.append(f"{nom} : environnement inconnu")
                continue
            if ligne.methode not in ("com", "ota"):
                motifs.append(f"{nom} : méthode invalide {ligne.methode!r}")
            elif envoi and ligne.methode == "com":
                if not build_envs.PORT_VALIDE.fullmatch(ligne.port or ""):
                    motifs.append(f"{nom} : port COM à saisir (COMn), reçu {ligne.port!r}")
                else:
                    ports.setdefault(ligne.port.upper(), []).append(nom)
            elif envoi and ligne.methode == "ota":
                if not connus[nom].ota_possible:
                    motifs.append(f"{nom} : OTA impossible pour cet environnement")
                if not ligne.ip:
                    motifs.append(f"{nom} : IP OTA à saisir")
                elif not _ipv4(ligne.ip):
                    motifs.append(f"{nom} : IP OTA invalide {ligne.ip!r}")
                if "uploadfs" in actions and self.ota_fs is None:
                    motifs.append(f"{nom} : téléversement du FS en OTA pas encore disponible")
                if "upload" in actions and self.ota_firmware is None:
                    motifs.append(f"{nom} : téléversement du firmware en OTA pas encore disponible")
        for port, noms in ports.items():
            if len(noms) > 1:
                motifs.append(f"{port} : une seule carte par port, envoi demandé pour {', '.join(noms)}")
            etat = self.port_libre(port)
            if etat in ("tenu", "absent"):
                quoi = "tenu par un autre outil (pont série, sniffeur, testeur ?)" if etat == "tenu" else "absent"
                motifs.append(f"{port} : port {quoi}")
        builds = self.builds_en_cours()
        if builds is None:
            motifs.append("détection des builds en cours impossible (PowerShell) : réessayer")
        elif builds:
            motifs.append(f"un build est déjà en cours ({', '.join(builds)})")
        return motifs

    # -- lancement et arret -----------------------------------------------------------------------------

    def lance(self, lignes, actions):
        lignes, actions = list(lignes), set(actions)
        motifs = self.controle(lignes, actions)
        with self.verrou:
            if self._actif:
                motifs = motifs or ["un lancement est déjà en cours"]
            if motifs:
                raise RuntimeError(" ; ".join(motifs))
            self._actif, self._arret, self._arret_immediat = True, False, False
        threading.Thread(target=self._execute, args=(lignes, actions), daemon=True).start()

    def arrete(self, immediat=False):
        """Arret apres l'env en cours ; `immediat` tue aussi l'arbre du fils pio en cours.

        Un envoi OTA (fonctions ota_firmware, ota_fs) ne se tue pas : la serie s'arrete a sa fin.
        """
        with self.verrou:
            if not self._actif:
                return
            self._arret = True
            self._arret_immediat = self._arret_immediat or immediat
            proc = self._proc if immediat else None
            self.verrou.notify_all()                     # reveille une attente de build externe
        if proc is not None:
            tue_arbre(proc)

    def _arrete_demande(self, immediat=False):
        with self.verrou:
            return self._arret_immediat if immediat else self._arret

    # -- execution ----------------------------------------------------------------------------------------

    def _execute(self, lignes, actions):
        ordonnees = [a for a in ORDRE if a in actions]
        succes, echecs, non_lances, pio_lance = [], [], [], False
        try:
            self._ajoute("debut", None, lignes=[asdict(l) for l in lignes], actions=ordonnees)
            for i, ligne in enumerate(lignes):
                if self._arrete_demande() or (i > 0 and not self._attend_builds(ligne.env)):
                    non_lances = [l.env for l in lignes[i:]]
                    break
                resultat, lance_pio = self._execute_env(ligne, ordonnees)
                pio_lance = pio_lance or lance_pio
                (succes if resultat == "succes" else echecs).append(ligne.env)
        except Exception as erreur:                     # garde-fou : la page doit toujours recevoir `fin`
            self._ajoute("echec", None, action="", motif=f"erreur inattendue de la série : {erreur!r}", extrait=[])
        finally:
            arrete = self._arrete_demande()
            champs = {"fichiers_modifies": FICHIERS_MODIFIES,
                      "message": "Fichiers réécrits par le build, à commiter : " + ", ".join(FICHIERS_MODIFIES)
                      } if pio_lance else {"fichiers_modifies": []}
            with self.verrou:
                self._actif, self._proc = False, None
            self._ajoute("fin", None, resultat="arrete" if arrete else "termine", succes=succes,
                         echecs=echecs, non_lances=non_lances, **champs)

    def _attend_builds(self, env):
        """Attend qu'aucun build externe ne tourne ; False si l'arret est demande pendant l'attente.

        Detection impossible (None : PowerShell en erreur ou trop lent, typiquement machine chargee
        par un build) = build possible : on attend et on resonde, comme au lancement on refuse.
        """
        signale = None
        while True:
            builds = self.builds_en_cours()
            if builds is None:
                builds = [DETECTION_IMPOSSIBLE]
            if not builds:
                if signale:
                    self._ajoute("attente", env, builds=[])
                return True
            if builds != signale:
                self._ajoute("attente", env, builds=builds)
                signale = builds
            with self.verrou:
                if not self._arret:
                    self.verrou.wait(self.sondage)
                if self._arret:
                    return False

    def _plan(self, ligne, actions):
        """[(type, action de suivi, cible pio, actions couvertes)] dans l'ordre d'execution."""
        plan = []
        if "upload" in actions:
            couvre = [a for a in ("compiler", "upload") if a in actions]
            if ligne.methode == "com":
                plan.append(("pio", "upload", "upload", couvre))
            else:
                plan.append(("pio", "upload", "", couvre))                       # compilation seule
                plan.append(("ota_firmware", "upload", "", couvre))
        elif "compiler" in actions:
            plan.append(("pio", "compiler", "", ["compiler"]))
        if "buildfs" in actions:
            plan.append(("pio", "buildfs", "buildfs", ["buildfs"]))
        if "uploadfs" in actions:
            if ligne.methode == "com":
                plan.append(("pio", "uploadfs", "uploadfs", ["uploadfs"]))
            else:
                if "buildfs" not in actions:
                    plan.append(("pio", "buildfs", "buildfs", ["uploadfs"]))     # preparation de l'envoi
                plan.append(("ota_fs", "uploadfs", "", ["uploadfs"]))
        return plan

    def _execute_env(self, ligne, actions):
        env, debut = ligne.env, time.monotonic()
        self._ajoute("debut", env, actions=actions, methode=ligne.methode, port=ligne.port, ip=ligne.ip)
        statuts = {a: "annulee" for a in actions}
        plan = self._plan(ligne, actions)
        resultat, lance_pio = "succes", False
        for k, (genre, action, cible, couvre) in enumerate(plan):
            if genre == "pio":
                lance_pio = True
                ok, motif, extrait, etape = self._lance_pio(ligne, action, cible)
            else:
                ok, motif, extrait, etape = self._lance_ota(ligne, genre)
            prepare = genre == "pio" and cible == "buildfs" and couvre == ["uploadfs"]
            if ok:
                if not prepare:
                    statuts.update({a: "succes" for a in couvre})
                continue
            if action == "upload" and "compiler" in couvre and etape in (ETAPE_PREBUILD, ETAPE_COMPILATION,
                                                                         ETAPE_LIENS):
                statuts["compiler"] = "echec"          # echec avant le televersement : upload annulee
            elif action == "upload" and "compiler" in couvre:
                statuts.update(compiler="succes", upload="echec")
            else:
                statuts.update({a: "echec" for a in couvre})
            self._ajoute("echec", env, action=action, motif=motif, extrait=extrait)
            resultat = "arrete" if self._arrete_demande(immediat=True) else "echec"
            break
        self._ajoute("fin_env", env, resultat=resultat, statuts=statuts,
                     secondes=round(time.monotonic() - debut, 2))
        return resultat, lance_pio

    def _chrono(self, env, action):
        """Mesure des etapes : renvoie (change(etape), termine()) qui emettent `duree` a chaque fin."""
        courant = {"etape": None, "t": time.monotonic()}

        def change(etape):
            maintenant = time.monotonic()
            if courant["etape"] is not None and etape != courant["etape"]:
                self._ajoute("duree", env, action=action, etape=courant["etape"],
                             secondes=round(maintenant - courant["t"], 3))
            if etape != courant["etape"]:
                courant.update(etape=etape, t=maintenant)

        def termine():
            change(None)

        return change, termine

    def _lance_pio(self, ligne, action, cible):
        """Un fils pio ; renvoie (ok, motif, extrait d'erreur, derniere etape)."""
        env = ligne.env
        args = ["run", "-e", env] + (["-t", cible] if cible else [])
        environ = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", PYTHONUNBUFFERED="1")
        for heritee in ("TASMOTA_OTA_IP", "PLATFORMIO_UPLOAD_PORT", "PLATFORMIO_EXTRA_SCRIPTS"):
            environ.pop(heritee, None)                  # PLATFORMIO_* : empreinte -> purge de .pio/build
        if action in ENVOIS and ligne.methode == "com":
            args += ["--upload-port", ligne.port]
        suivi = Suivi(action, self._references().get(env) if action in ("compiler", "upload") else None)
        change, termine = self._chrono(env, action)
        commande = "pio " + " ".join(args)
        self._ajoute("etape", env, action=action, etape=suivi.etape, pourcent=None, detail="", commande=commande)
        change(suivi.etape)
        drapeaux = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        with self.verrou:
            if self._arret_immediat:
                return False, "arrêt immédiat demandé", [], suivi.etape
            try:
                proc = subprocess.Popen(self.commande_pio + args, cwd=self.racine, env=environ,
                                        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                        errors="replace", bufsize=1, creationflags=drapeaux)
            except OSError as erreur:
                return False, f"pio introuvable ou non lançable : {erreur}", [], suivi.etape
            self._proc = proc
        with proc, self._journal(env, action, commande) as journal:
            for brut in proc.stdout:
                texte = retire_ansi(brut).rstrip("\r\n")
                journal.write(texte + "\n")
                self._ajoute("ligne", env, action=action, texte=texte)
                ev = suivi.ligne(brut)
                if ev is not None:
                    change(ev["etape"])
                    self._ajoute("etape", env, action=action, **ev)
            code = proc.wait()
            journal.write(f"--- code de sortie {code}\n")
        with self.verrou:
            self._proc = None
        termine()
        if self._arrete_demande(immediat=True):
            return False, "arrêt immédiat : arbre de processus tué", suivi.extrait_erreur, suivi.etape
        if code != 0:
            return False, f"pio a échoué (code de sortie {code})", suivi.extrait_erreur, suivi.etape
        if action in ("compiler", "upload"):
            self._memorise_reference(env)
        return True, "", [], suivi.etape

    def _lance_ota(self, ligne, genre):
        """Envoi OTA par la page : genre "ota_firmware" (action upload) ou "ota_fs" (uploadfs)."""
        env = ligne.env
        action, initiale = ("upload", ETAPE_ENVOI) if genre == "ota_firmware" else ("uploadfs", ETAPE_ENVOI_FS)
        change, termine = self._chrono(env, action)
        dernier = {"etape": initiale}

        def rapporte(info):
            etape = str(info.get("etape") or initiale)
            dernier["etape"] = etape
            change(etape)
            self._ajoute("etape", env, action=action, etape=etape, pourcent=info.get("pourcent"),
                         detail=str(info.get("detail") or ""))

        rapporte({"etape": initiale, "pourcent": None, "detail": f"vers {ligne.ip}"})
        build = self.racine / ".pio" / "build" / env
        try:
            if genre == "ota_firmware":
                self.ota_firmware(env, ligne.ip, build, rapporte)
            else:
                sauvegardes = self.dossier / "persist"
                sauvegardes.mkdir(parents=True, exist_ok=True)
                # Les fichiers de littlefs.bin, l'image que le buildfs precedent vient d'ecrire : PAS
                # littlefs_data, rempli par post_esp32.py a chaque edition des liens (spec, choix 10.1).
                image = build / "littlefs.bin"
                with tempfile.TemporaryDirectory(prefix=f"build-fs-{env}-") as provisoire:
                    fichiers = Path(provisoire) / "fs"
                    rapporte({"etape": build_ota_fs.ETAPE_IMAGE, "pourcent": None, "detail": str(image)})
                    nombre = build_ota_fs.extrait_image(image, fichiers)
                    rapporte({"etape": build_ota_fs.ETAPE_IMAGE, "pourcent": 100, "detail": f"{nombre} fichiers"})
                    self.ota_fs(env, ligne.ip, fichiers, sauvegardes, rapporte)
        except RuntimeError as erreur:
            return False, str(erreur), [], dernier["etape"]
        except Exception as erreur:
            return False, f"erreur inattendue pendant l'envoi : {erreur!r}", [], dernier["etape"]
        finally:
            termine()
        return True, "", [], dernier["etape"]

    # -- fichiers de donnees ----------------------------------------------------------------------------

    def _journal(self, env, action, commande):
        dossier = self.dossier / "journaux"
        dossier.mkdir(parents=True, exist_ok=True)
        base = f"{time.strftime('%Y%m%d-%H%M%S')}-{env}-{action}"
        chemin, i = dossier / f"{base}.log", 1
        while chemin.exists():
            i += 1
            chemin = dossier / f"{base}-{i}.log"
        f = open(chemin, "w", encoding="utf-8", newline="\n")
        f.write(f"--- {commande}\n")
        return f

    def _references(self):
        try:
            donnees = json.loads((self.dossier / "references.json").read_text(encoding="utf-8"))
            return donnees if isinstance(donnees, dict) else {}
        except (OSError, ValueError):
            return {}

    def _memorise_reference(self, env):
        build = self.racine / ".pio" / "build" / env
        nb = sum(1 for _ in build.rglob("*.o")) if build.is_dir() else 0
        if nb <= 0:
            return
        references = self._references()
        references[env] = nb
        self.dossier.mkdir(parents=True, exist_ok=True)
        provisoire = self.dossier / "references.json.tmp"
        provisoire.write_text(json.dumps(references, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(provisoire, self.dossier / "references.json")


def _ipv4(texte):
    try:
        ipaddress.IPv4Address(texte)
        return True
    except ValueError:
        return False
