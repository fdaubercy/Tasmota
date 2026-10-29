"""Execution en serie des `pio run` de la page Build et televersement : refus, suivi, arret.

Un lancement = des lignes (env, methode COM ou OTA, port, IP) et des actions cochees parmi
compiler / upload / erase_upload / buildfs / uploadfs. Les envs passent l'un apres l'autre, un seul fils
pio a la fois. Dans un env, ordre fixe : compiler -> televerser le firmware (ou effacer puis televerser) ->
construire le FS -> televerser le FS. Un echec arrete CET env (actions suivantes « annulee »), les autres continuent (choix 8 de la
spec docs/superpowers/specs/2026-10-24-page-build-televersement-design.md).

Commandes (choix 9) : compiler = `run -e X` ; upload = `run -e X -t upload` (compile si besoin : si
« compiler » est aussi coche, seul upload part) ; erase_upload = `-t erase_upload` (choix 19 : par cable
seulement, l'un OU l'autre avec upload, a sa place, compile si besoin comme lui) ; buildfs = `-t buildfs` ;
uploadfs par cable = `-t uploadfs`, SAUF pour un env a custom_files_upload dont le firmware part par cable
(upload / erase_upload) : post_esp32 y ecrit deja le FS, buildfs et uploadfs suivent alors le sort de cet envoi
sans pio run a part (_plan, 2026-10-26). Port COM par `--upload-port` (jamais PLATFORMIO_UPLOAD_PORT ni
PLATFORMIO_EXTRA_SCRIPTS : ils entrent dans l'empreinte du projet et purgeraient .pio/build).
En OTA, la page envoie elle-meme (build_ota_fs, spec choix 7 revise) : upload = `run -e X` puis la
fonction injectee `ota_firmware` (firmware de .pio/build/<env>/ par /u2) ; uploadfs = buildfs (s'il
n'est pas deja coche), puis les fichiers de .pio/build/<env>/littlefs.bin (l'image du buildfs, extraite
dans un dossier temporaire par build_ota_fs.extrait_image) envoyes par la fonction injectee `ota_fs`
(/ufsu). Jamais littlefs_data : post_esp32.py le remplit a chaque edition des liens (choix 10.1).

Refus avant de lancer (choix 11) : build deja en cours (garde_build), port COM tenu ou absent (erase_upload
est un envoi), IP OTA vide, erase_upload en OTA ou avec upload. Le controle « build en cours » est refait avant chaque env
suivant : la serie attend (evenement `attente`) puis reprend. Pendant qu'un fils de la serie tourne,
rien n'est controle : la serie ne se bloque pas sur ses propres `pio run`.

Pause « rebranchez la carte » (choix 11 revise, 2026-10-25) : deux lignes COM d'un meme lancement peuvent
partager un port (une seule carte branchee a la fois). Pour un env dont l'envoi COM passe par un port deja
servi par un env PRECEDENT de la serie, la compilation (si cochee) se fait d'abord, en un pio run a part ;
puis, juste avant son premier envoi COM, la serie emet `attente_carte` et attend la reponse de la page
(`reprend` : continuer ou passer). L'envoi qui suit une compilation reussie part en `-t nobuild -t upload`
(resp. erase_upload) : le pre-script incremente CFG_HOLDER a chaque pio run, un `-t upload` seul recompilerait
tout ; nobuild reprend le firmware deja compile (builder/main.py de la plateforme, cible nobuild). Continuer :
attente d'un build externe eventuel, puis le port est reverifie ; absent ou tenu -> la pause RESTE ouverte
(nouvel `attente_carte` avec le message : rebrancher puis Continuer, ou Passer). Passer : actions restantes
« annulee », env « passe ». Les deux arrets mettent fin a la pause (env « arrete », range dans `arretes`, pas
dans les echecs ; actions restantes « annulee ») ; aucun envoi n'est en vol pendant une pause.

Evenements numerotes (modele maintenance/synchro_fork_session.Session, rejoues par `depuis`) :
  debut    env=None : lignes et actions du lancement ; env=X : debut d'un env
  etape    env, action, etape, pourcent, detail (+ commande au depart d'un fils)
  duree    env, action, etape, secondes : emis des la fin de l'etape
  ligne    env, action, texte (sans ANSI)
  echec    env, action, motif, extrait
  fin_env  env, resultat (succes | echec | arrete | passe), statuts {action: succes | echec | annulee}
  attente  env, builds (liste vide = reprise)
  attente_carte  env, port, precedent (env precedent sur ce port), fait (actions deja reussies), erreur ("" ou
           port absent / tenu apres Continuer) : pause, la page demande de brancher la carte
  reprise_carte  env, port, choix (continuer | passer | arret) : fin de la pause
  fin      env=None, resultat (termine | arrete), succes, echecs, passes, arretes, non_lances, fichiers_modifies

Journal complet de chaque fils (sans ANSI) dans <dossier>/journaux/ ; par env, dans
<dossier>/references.json, le total des .o et les objets du dernier build incremental reussi (base du %) ;
sans total pour un env, celui du plus grand env de la meme puce, affiche « ≈ » (_total_estime).
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
import build_solidification
from build_progression import (ETAPE_COMPILATION, ETAPE_EFFACEMENT, ETAPE_ENVOI, ETAPE_LIENS, ETAPE_PREBUILD, Suivi,
                               retire_ansi)

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
PIO_PENV = Path.home() / ".platformio" / "penv" / "Scripts" / "pio.exe"
ORDRE = ("compiler", "upload", "erase_upload", "buildfs", "uploadfs")
ENVOIS = {"upload", "erase_upload", "uploadfs"}
TELEVERSEMENTS = ("upload", "erase_upload")         # televerser le firmware : l'un OU l'autre (choix 19)
COMPILENT = ("compiler",) + TELEVERSEMENTS           # leur pio run compile : base du % et objets de reference
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
                 ota_firmware=build_ota_fs.envoie_firmware_ota, sondage=5.0,
                 solidification=build_solidification.vides, par_maitre=build_ota_fs.joint_par_maitre,
                 coupe_sleep=build_ota_fs.coupe_sleep):
        self.racine = Path(racine)
        self.dossier = Path(dossier)
        self.commande_pio = commande_pio(pio)
        self.builds_en_cours = builds_en_cours
        self.port_libre = port_libre
        self.ota_fs = ota_fs
        self.ota_firmware = ota_firmware
        self.par_maitre = par_maitre                    # `IP:port` : redirection du maitre posee, carte jointe verifiee
        self.coupe_sleep = coupe_sleep                  # `IP:port` : Sleep 0 sur le maitre le temps de l'envoi
        self.solidification = solidification            # modules solidifies vides, controles a la fin du pre-build
        self.sondage = sondage
        self.verrou = threading.Condition()
        self.evenements = []
        self.numero = 0
        self._actif = False
        self._proc = None
        self._arret = False
        self._arret_immediat = False
        self._envoi = False                              # un envoi vers une carte est en vol (envoi_en_cours)
        self._pause = None                               # pause « rebranchez la carte » : {env, port, precedent, choix}
        self._fs_par_firmware = set()                    # envs dont l'envoi serie du firmware ecrit aussi le FS (controle)

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

    def envoi_en_cours(self):
        """Vrai pendant un envoi vers une carte : upload / uploadfs par cable une fois en phase
        Televersement (la compilation et la construction du FS qui precedent n'en sont pas), erase_upload
        des l'Effacement de la flash (le couper laisserait une flash vide), ou envoi OTA par la page. build_web.arrete_serie attend sa fin avant de tuer quoi que ce soit."""
        with self.verrou:
            return self._actif and self._envoi

    def _marque_envoi(self, envoi):
        with self.verrou:
            self._envoi = envoi

    def pause_en_cours(self):
        """{env, port, precedent} pendant une pause « rebranchez la carte », sinon None."""
        with self.verrou:
            if self._pause is None:
                return None
            return {k: self._pause[k] for k in ("env", "port", "precedent")}

    def reprend(self, env, choix):
        """Reponse de la page a la pause : « continuer » (carte branchee) ou « passer » (cet env).

        ValueError : choix invalide ; RuntimeError : aucune pause en cours, ou elle attend un autre env.
        """
        if choix not in ("continuer", "passer"):
            raise ValueError(f"choix invalide : {choix!r} (continuer ou passer)")
        with self.verrou:
            if not self._actif or self._pause is None:
                raise RuntimeError("aucune pause en cours")
            if self._pause["env"] != env:
                raise RuntimeError(f"la pause en cours attend la carte {self._pause['env']}, pas {env}")
            if self._pause["choix"] is not None:
                raise RuntimeError("cette pause a déjà reçu une réponse")
            self._pause["choix"] = choix
            self.verrou.notify_all()

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
        if set(TELEVERSEMENTS) <= set(actions):
            motifs.append("« Téléverser le firmware » et « Effacer puis téléverser » : l'une ou l'autre, pas les deux")
        envoi = bool(set(actions) & ENVOIS)
        connus = {e.nom: e for e in build_envs.liste_envs(self.racine)}
        self._fs_par_firmware = {nom for nom, e in connus.items() if e.fs_avec_firmware}   # lu par _plan
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
                if "erase_upload" in actions:
                    motifs.append(f"{nom} : « Effacer puis téléverser » se fait par câble (COM) seulement")
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
        for port in ports:                              # un port partage : pause avant l'env suivant (choix 11 revise)
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

        Un envoi OTA (fonctions ota_firmware, ota_fs) ne se tue pas : la serie s'arrete a sa fin. Les
        etapes pas encore commencees de l'env (envoi OTA compris) sont « annulee » ; un fils pio fini
        avec le code 0 reste un succes, meme si l'arret arrive pendant la lecture de sa fin.
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
        succes, echecs, passes, arretes, non_lances, pio_lance = [], [], [], [], [], False
        envoi_com = bool(set(ordonnees) & ENVOIS)
        servis = {}                                      # port COM -> dernier env de la serie qui l'a servi
        try:
            self._ajoute("debut", None, lignes=[asdict(l) for l in lignes], actions=ordonnees)
            for i, ligne in enumerate(lignes):
                if self._arrete_demande() or (i > 0 and not self._attend_builds(ligne.env)):
                    non_lances = [l.env for l in lignes[i:]]
                    break
                port = ligne.port.upper() if envoi_com and ligne.methode == "com" else ""
                resultat, lance_pio = self._execute_env(ligne, ordonnees, servis.get(port) if port else None)
                if port:
                    servis[port] = ligne.env
                pio_lance = pio_lance or lance_pio
                {"succes": succes, "passe": passes, "arrete": arretes}.get(resultat, echecs).append(ligne.env)
        except Exception as erreur:                     # garde-fou : la page doit toujours recevoir `fin`
            self._ajoute("echec", None, action="", motif=f"erreur inattendue de la série : {erreur!r}", extrait=[])
        finally:
            arrete = self._arrete_demande()
            champs = {"fichiers_modifies": FICHIERS_MODIFIES,
                      "message": "Fichiers réécrits par le build, à commiter : " + ", ".join(FICHIERS_MODIFIES)
                      } if pio_lance else {"fichiers_modifies": []}
            # `fin` puis liberation sous le meme verrou (RLock de la Condition) : personne ne voit une serie
            # libre sans son `fin`, et un nouveau lancement ne peut pas s'intercaler avant lui.
            with self.verrou:
                self._ajoute("fin", None, resultat="arrete" if arrete else "termine", succes=succes,
                             echecs=echecs, passes=passes, arretes=arretes, non_lances=non_lances, **champs)
                self._actif, self._proc, self._pause = False, None, None

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

    def _plan(self, ligne, actions, pause=False):
        """[(type, action de suivi, cible pio, actions couvertes, actions reussies si ok)] dans l'ordre.

        « couvertes » : celles qu'un echec de l'etape met en echec ; « reussies » : celles qu'un succes
        de l'etape acheve (une compilation qui prepare un envoi OTA n'acheve pas l'upload).
        `pause` (port deja servi par un env precedent) : une etape « pause » juste avant le premier envoi
        COM ; compiler + televerser y deviennent deux pio run, pour compiler avant la pause, et l'envoi part
        en `-t nobuild -t <cible>` (cible pio a plusieurs mots : un -t par mot) pour ne pas tout recompiler.
        """
        plan = []
        televerse = next((a for a in TELEVERSEMENTS if a in actions), None)
        # Envoi serie du firmware d'un env a custom_files_upload : post_esp32 (esp32_build_filesystem) construit
        # littlefs.bin et esptool l'ecrit avec le firmware. buildfs / uploadfs coches ne refont pas ce travail
        # (buildfs prendrait meme le data_dir du lancement precedent) : ils suivent le sort de cet envoi.
        par_firmware = [a for a in ("buildfs", "uploadfs") if a in actions] \
            if televerse and ligne.methode == "com" and ligne.env in self._fs_par_firmware else []
        if televerse:
            couvre = [a for a in ("compiler", televerse) if a in actions]
            if ligne.methode == "com" and pause and "compiler" in actions:
                plan.append(("pio", "compiler", "", ["compiler"], ["compiler"]))
                plan.append(("pio", televerse, "nobuild " + televerse, [televerse] + par_firmware,
                             [televerse] + par_firmware))
            elif ligne.methode == "com":
                plan.append(("pio", televerse, televerse, couvre + par_firmware, couvre + par_firmware))
            else:                                        # upload OTA (erase_upload en OTA : refuse par controle)
                plan.append(("pio", "upload", "", couvre, [a for a in couvre if a == "compiler"]))   # compilation
                plan.append(("ota_firmware", "upload", "", ["upload"], ["upload"]))
        elif "compiler" in actions:
            plan.append(("pio", "compiler", "", ["compiler"], ["compiler"]))
        if "buildfs" in actions and not par_firmware:
            plan.append(("pio", "buildfs", "buildfs", ["buildfs"], ["buildfs"]))
        if "uploadfs" in actions and not par_firmware:
            if ligne.methode == "com":
                plan.append(("pio", "uploadfs", "uploadfs", ["uploadfs"], ["uploadfs"]))
            else:
                if "buildfs" not in actions:
                    plan.append(("pio", "buildfs", "buildfs", ["uploadfs"], []))  # preparation de l'envoi
                plan.append(("ota_fs", "uploadfs", "", ["uploadfs"], ["uploadfs"]))
        if pause and ligne.methode == "com":
            i = next((i for i, etape in enumerate(plan) if etape[0] == "pio" and etape[2].split()[-1:] and
                      etape[2].split()[-1] in ENVOIS), None)
            if i is not None:
                plan.insert(i, ("pause", plan[i][1], "", [plan[i][1]], []))
        return plan

    def _execute_env(self, ligne, actions, precedent=None):
        """Un env ; `precedent` : env precedent de la serie sur le meme port COM (pause avant l'envoi)."""
        env, debut = ligne.env, time.monotonic()
        self._ajoute("debut", env, actions=actions, methode=ligne.methode, port=ligne.port, ip=ligne.ip)
        statuts = {a: "annulee" for a in actions}
        plan = self._plan(ligne, actions, pause=precedent is not None)
        resultat, lance_pio = "succes", False
        for genre, action, cible, couvre, reussies in plan:
            if self._arrete_demande(immediat=True):     # arret immediat entre deux etapes : le reste « annulee »
                resultat = "arrete"
                break
            if genre == "pause":
                choix = self._attend_carte(ligne, precedent, [a for a in actions if statuts[a] == "succes"])
                if choix in ("arret", "passer"):         # le reste « annulee »
                    resultat = "arrete" if choix == "arret" else "passe"
                    break
                continue
            if genre == "pio":
                lance_pio = True
                ok, motif, extrait, etape = self._lance_pio(ligne, action, cible)
            else:
                ok, motif, extrait, etape = self._lance_ota(ligne, genre)
            if ok is None:                               # arret immediat avant le lancement du fils
                resultat = "arrete"
                break
            if ok:
                statuts.update({a: "succes" for a in reussies})
                continue
            televerse = action in TELEVERSEMENTS and "compiler" in couvre
            if televerse and etape in (ETAPE_PREBUILD, ETAPE_COMPILATION, ETAPE_LIENS):
                statuts["compiler"] = "echec"          # echec avant le televersement : upload annulee
            elif televerse:
                statuts.update({"compiler": "succes", action: "echec"})
            else:
                statuts.update({a: "echec" for a in couvre})
            self._ajoute("echec", env, action=action, motif=motif, extrait=extrait)
            resultat = "arrete" if self._arrete_demande(immediat=True) else "echec"
            break
        self._ajoute("fin_env", env, resultat=resultat, statuts=statuts,
                     secondes=round(time.monotonic() - debut, 2))
        return resultat, lance_pio

    def _attend_carte(self, ligne, precedent, fait):
        """Pause avant l'envoi : renvoie continuer | passer | arret.

        Attend `reprend` ou un arret (les deux arrets y mettent fin : rien n'est en vol). Apres « continuer » :
        un build externe apparu pendant la pause est attendu, puis le port est reverifie ; absent ou tenu, la
        pause est rouverte avec le message (nouvel attente_carte) : rebrancher puis Continuer, ou Passer.
        `attente_carte` est emis et la pause posee sous la meme prise du verrou : une reponse ne peut pas
        arriver entre les deux.
        """
        env, port, erreur = ligne.env, ligne.port.upper(), ""
        while True:
            with self.verrou:
                self._ajoute("attente_carte", env, port=port, precedent=precedent, fait=fait, erreur=erreur)
                self._pause = {"env": env, "port": port, "precedent": precedent, "choix": None}
                while self._pause["choix"] is None and not self._arret:
                    self.verrou.wait(1.0)
                choix = "arret" if self._arret else self._pause["choix"]
                self._pause = None
            if choix == "continuer" and not self._attend_builds(env):
                choix = "arret"
            if choix != "continuer":
                break
            etat = self.port_libre(port)
            if etat not in ("tenu", "absent"):
                break
            erreur = (f"{port} absent : rebranchez la carte {env} puis cliquez Continuer (ou Passer cet env)"
                      if etat == "absent" else
                      f"{port} tenu par un autre outil (pont série, sniffeur, testeur ?) : libérez-le puis cliquez "
                      "Continuer (ou Passer cet env)")
        self._ajoute("reprise_carte", env, port=port, choix=choix)
        return choix

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
        args = ["run", "-e", env] + [x for c in cible.split() for x in ("-t", c)]   # « nobuild upload » : deux -t
        environ = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", PYTHONUNBUFFERED="1")
        for heritee in ("TASMOTA_OTA_IP", "PLATFORMIO_UPLOAD_PORT", "PLATFORMIO_EXTRA_SCRIPTS"):
            environ.pop(heritee, None)                  # PLATFORMIO_* : empreinte -> purge de .pio/build
        if action in ENVOIS and ligne.methode == "com":
            args += ["--upload-port", ligne.port]
        references = self._references() if action in COMPILENT else {}
        ref = references.get(env)
        ref = ref if isinstance(ref, dict) else {"total": ref}      # ancien format : un entier = le total
        total, estime = ref.get("total"), False
        if not total:
            total = _total_estime(env, references)
            estime = total is not None
        # envoi par cable : durees des zones du dernier envoi reussi -> % de l'envoi entier (A13)
        zones = ref.get("zones") if action in TELEVERSEMENTS and ligne.methode == "com" else None
        suivi = Suivi(action, total, ref.get("increment"), estime=estime, zones=zones)
        change, termine = self._chrono(env, action)
        commande = "pio " + " ".join(args)
        self._ajoute("etape", env, action=action, etape=suivi.etape, pourcent=None, detail="", commande=commande)
        change(suivi.etape)
        try:                                             # pio lit data_dir AVANT le pre-script (build_envs.ecrit_data_dir)
            dossier = build_envs.ecrit_data_dir(self.racine, env)
            note = f"--- data_dir = {dossier} (posé par la page avant pio)" if dossier else ""
        except OSError as erreur:                        # le pre-script pose aussi PROJECT_DATA_DIR : on continue
            note = f"--- data_dir non posé par la page : {erreur}"
        if note:
            self._ajoute("ligne", env, action=action, texte=note)
        drapeaux = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        with self.verrou:
            if self._arret_immediat:                     # ok None : fils jamais lance, action « annulee »
                return None, "arrêt immédiat demandé", [], suivi.etape
            try:
                proc = subprocess.Popen(self.commande_pio + args, cwd=self.racine, env=environ,
                                        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                        errors="replace", bufsize=1, creationflags=drapeaux)
            except OSError as erreur:
                return False, f"pio introuvable ou non lançable : {erreur}", [], suivi.etape
            self._proc = proc
        refus, controle = "", action in COMPILENT   # solidification controlee une fois, si le firmware est lie
        with proc, self._journal(env, action, commande) as journal:
            if note:
                journal.write(note + "\n")
            for brut in proc.stdout:
                texte = retire_ansi(brut).rstrip("\r\n")
                journal.write(texte + "\n")
                self._ajoute("ligne", env, action=action, texte=texte)
                ev = suivi.ligne(brut)
                if ev is not None:
                    change(ev["etape"])
                    self._marque_envoi(action in ENVOIS and ev["etape"] in (ETAPE_ENVOI, ETAPE_EFFACEMENT))
                    self._ajoute("etape", env, action=action, **ev)
                    if controle and ev["etape"] in (ETAPE_COMPILATION, ETAPE_LIENS):
                        # Pre-build fini (solidification comprise) : un module vide ferait echouer l'edition des
                        # liens a la toute fin ; on arrete pio tout de suite (build_solidification).
                        controle = False
                        manquants = self.solidification(self.racine)
                        if manquants:
                            refus = build_solidification.motif(manquants)
                            journal.write(f"--- {refus} : pio arrêté par la page\n")
                            self._ajoute("ligne", env, action=action, texte=f"✗ {refus} : pio arrêté par la page")
                            tue_arbre(proc)
                            break
            code = proc.wait()
            journal.write(f"--- code de sortie {code}\n")
        with self.verrou:
            self._proc, self._envoi = None, False
        termine()
        if refus:
            return False, refus, [refus], ETAPE_PREBUILD
        if code == 0:                                    # fini avec succes, meme si l'arret immediat arrive
            if action in COMPILENT:                      # juste apres : l'upload a bien eu lieu
                self._memorise_reference(env, suivi)
            return True, "", [], suivi.etape
        if self._arrete_demande(immediat=True):
            return False, "arrêt immédiat : arbre de processus tué", suivi.extrait_erreur, suivi.etape
        return False, f"pio a échoué (code de sortie {code})", suivi.extrait_erreur, suivi.etape

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
        self._marque_envoi(True)                         # l'envoi OTA ne se coupe pas (arrete_serie attend)
        remet = None
        try:
            if ":" in ligne.ip:
                maitre = ligne.ip.rsplit(":", 1)[0]
                valeur, remet = self.coupe_sleep(maitre)
                rapporte({"etape": build_ota_fs.ETAPE_CONNEXION, "pourcent": None,
                          "detail": f"Sleep du maître {maitre} : {valeur} -> 0 le temps de l'envoi"})
                rapporte({"etape": build_ota_fs.ETAPE_CONNEXION, "pourcent": 100, "detail": self.par_maitre(
                    ligne.ip, build_envs.persist_carte(self.racine, env), env, rapporte)})
            if genre == "ota_firmware":
                self.ota_firmware(env, ligne.ip, build, rapporte)
            else:
                sauvegardes = self.dossier / "persist"
                sauvegardes.mkdir(parents=True, exist_ok=True)
                # Les fichiers de littlefs.bin, l'image que le buildfs precedent vient d'ecrire : PAS
                # littlefs_data, rempli par post_esp32.py a chaque edition des liens (spec, choix 10.1).
                image = build / "littlefs.bin"
                with tempfile.TemporaryDirectory(prefix=f"build-fs-{env}-", ignore_cleanup_errors=True) as provisoire:
                    fichiers = Path(provisoire) / "fs"
                    rapporte({"etape": build_ota_fs.ETAPE_IMAGE, "pourcent": None, "detail": str(image)})
                    nombre = build_ota_fs.extrait_image(image, fichiers)
                    rapporte({"etape": build_ota_fs.ETAPE_IMAGE, "pourcent": 100, "detail": f"{nombre} fichiers"})
                    # L'image est-elle bien celle de CET env ? (P4 avec le FS de la cuve le 2026-10-26)
                    identite = build_ota_fs.verifie_identite(fichiers, build_envs.persist_carte(self.racine, env), env)
                    rapporte({"etape": build_ota_fs.ETAPE_IMAGE, "pourcent": 100, "detail": identite})
                    self.ota_fs(env, ligne.ip, fichiers, sauvegardes, rapporte)
        except RuntimeError as erreur:
            return False, str(erreur), [], dernier["etape"]
        except Exception as erreur:
            return False, f"erreur inattendue pendant l'envoi : {erreur!r}", [], dernier["etape"]
        finally:
            if remet and (echec := remet()):             # sans changer l'etape rendue
                self._ajoute("etape", env, action=action, etape=dernier["etape"], pourcent=None, detail=echec)
            self._marque_envoi(False)
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
        f = open(chemin, "w", encoding="utf-8", newline="\n", buffering=1)   # ligne a ligne : /sortie le lit en direct
        f.write(f"--- {commande}\n")
        return f

    def _references(self):
        try:
            donnees = json.loads((self.dossier / "references.json").read_text(encoding="utf-8"))
            return donnees if isinstance(donnees, dict) else {}
        except (OSError, ValueError):
            return {}

    def _memorise_reference(self, env, suivi):
        build = self.racine / ".pio" / "build" / env
        nb = sum(1 for _ in build.rglob("*.o")) if build.is_dir() else 0
        if nb <= 0 and not suivi.zones_ecrites:
            return
        references = self._references()
        ancien = references.get(env) if isinstance(references.get(env), dict) else {}
        nouveau = dict(ancien)
        if nb > 0:
            increment = ancien.get("increment")
            if not suivi.repris and 0 < suivi.nb_o < nb:     # build incremental : sa taille devient la base
                increment = suivi.nb_o
            nouveau.update(total=nb, increment=increment)
        if suivi.zones_ecrites:                          # envoi par cable : durees de ses zones (A13)
            nouveau["zones"] = suivi.zones_ecrites
        references[env] = nouveau
        self.dossier.mkdir(parents=True, exist_ok=True)
        provisoire = self.dossier / "references.json.tmp"
        provisoire.write_text(json.dumps(references, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(provisoire, self.dossier / "references.json")


def _total_estime(env, references):
    """Total de .o d'un env jamais compile par la page : le plus grand total connu d'un env de la meme puce
    (nom avant le premier tiret : tasmota32s3, tasmota32p4...), None si aucun. Le plus grand, car un total
    trop petit bloquerait le % a 99 bien avant la fin. Remplace par le vrai total au premier build reussi."""
    puce = env.split("-")[0]
    totaux = []
    for nom, ref in references.items():
        total = ref.get("total") if isinstance(ref, dict) else ref
        if nom != env and nom.split("-")[0] == puce and isinstance(total, int) and total > 0:
            totaux.append(total)
    return max(totaux, default=None)


def _ipv4(texte):
    """IPv4, ou `IPv4:port` (esclave joint par la redirection du maitre)."""
    ip, deux_points, port = texte.partition(":")
    try:
        ipaddress.IPv4Address(ip)
    except ValueError:
        return False
    return not deux_points or (port.isdigit() and 0 < int(port) < 65536)
