"""Banc de build_serie (execution en serie des `pio run`, refus, arret) avec le faux pio.

Code de sortie 0 = vert. Le VRAI pio n'est jamais lance : BUILD_WEB_PIO est pose ici sur
build_faux_pio.py, et le banc s'arrete avant tout lancement si la serie resout une autre commande.
Depot d'essai, donnees de l'outil et journal du faux pio : dans des dossiers temporaires.
"""

import ctypes
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent
FAUX_PIO = ICI / "build_faux_pio.py"
os.environ["BUILD_WEB_PIO"] = str(FAUX_PIO)
os.environ["TASMOTA_OTA_IP"] = "9.9.9.9"          # temoins : variables heritees qui ne doivent atteindre
os.environ["PLATFORMIO_UPLOAD_PORT"] = "COM99"    # aucun fils pio (les deux dernieres entrent dans
os.environ["PLATFORMIO_EXTRA_SCRIPTS"] = "post:x.py"   # l'empreinte du projet -> purge de .pio/build)

import build_faux_pio as faux                    # noqa: E402
import build_serie as bs                         # noqa: E402  (apres BUILD_WEB_PIO)
from build_serie import Ligne                    # noqa: E402
from test_build_ota_fs import FICHIERS_IMAGE, arbre, fabrique_image   # noqa: E402  (vraie image LittleFS)

ECHECS = []
ESC = "\x1b"
A, B, C = "tasmota32-essai-a", "tasmota32-essai-b", "tasmota32-essai-c"
P8266 = "tasmota-essai-8266"

CENV = f"""\
[env:tasmota32-essai-base]
extra_scripts           = pre:outils_docs/scripts_python/build/pre_utilitaires_platformio.py

[env:{A}]
extends                 = env:tasmota32-essai-base
upload_port             = COM12

[env:{B}]
extends                 = env:tasmota32-essai-base

[env:{C}]
extends                 = env:tasmota32-essai-base

[env:{P8266}]
build_flags             = -D FIRMWARE_ESSAI
"""


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


# -- montage ----------------------------------------------------------------------------------------

def firmware_ok(env, ip, dossier_build, rapporte):
    """Envoi du firmware simule : jamais la vraie fonction (elle contacterait une carte)."""


class Montage:
    """Depot d'essai + dossier de donnees + scenario et journal du faux pio."""

    def __init__(self, t, scenario=None, builds=None, ports=None, ota_fs=None, ota_firmware=firmware_ok,
                 classe=None):
        self.t = Path(t)
        self.racine = self.t / "depot"
        self.racine.mkdir()
        (self.racine / "platformio_tasmota_cenv.ini").write_text(CENV, encoding="utf-8")
        self.dossier = self.t / "donnees"
        self.scenario = self.t / "scenario.json"
        self.scenario.write_text(json.dumps(scenario or {}), encoding="utf-8")
        self.journal = self.t / "journal.jsonl"
        os.environ[faux.VAR_SCENARIO] = str(self.scenario)
        os.environ[faux.VAR_JOURNAL] = str(self.journal)
        self.appels_builds = 0
        self.builds = builds or (lambda n: [])
        self.ports = ports or {}
        self.serie = (classe or bs.Serie)(self.racine, self.dossier, builds_en_cours=self._builds,
                              port_libre=lambda p: self.ports.get(p, "libre"), ota_fs=ota_fs,
                              ota_firmware=ota_firmware, sondage=0.05)
        self.n = 0

    def _builds(self):
        self.appels_builds += 1
        return self.builds(self.appels_builds)

    def lance(self, lignes, actions, delai=20.0):
        """Lance et attend l'evenement `fin` ; renvoie les evenements de ce lancement."""
        self.serie.lance(lignes, set(actions))
        return self.attend("fin", delai)

    def attend(self, type_, delai=20.0, **filtre):
        """Evenements depuis le dernier releve jusqu'au premier `type_` (filtre sur ses champs)."""
        recus, limite = [], time.monotonic() + delai
        while time.monotonic() < limite:
            for e in self.serie.depuis(self.n, 0.2):
                self.n = e["n"]
                recus.append(e)
                if e["type"] == type_ and all(e.get(k) == v for k, v in filtre.items()):
                    return recus
        ECHECS.append(f"delai depasse en attendant {type_} {filtre}")
        print(f"KO   delai depasse en attendant {type_} {filtre}")
        return recus

    def appels(self, type_="debut"):
        if not self.journal.is_file():
            return []
        return [json.loads(l) for l in self.journal.read_text(encoding="utf-8").splitlines()
                if json.loads(l)["type"] == type_]


def du_type(evenements, type_, **filtre):
    return [e for e in evenements if e["type"] == type_ and all(e.get(k) == v for k, v in filtre.items())]


def vivant(pid):
    """Vrai si le processus `pid` tourne encore (Windows : OpenProcess + GetExitCodeProcess)."""
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, pid)          # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = ctypes.c_ulong()
    try:
        return bool(k.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == 259   # STILL_ACTIVE
    finally:
        k.CloseHandle(h)


def com(env, port="COM12"):
    return Ligne(env, "com", port, "")


def ota(env, ip="192.168.0.50"):
    return Ligne(env, "ota", "", ip)


# -- garde-fou ----------------------------------------------------------------------------------------

def garde_fou():
    """Le banc ne doit jamais pouvoir lancer le vrai pio."""
    with tempfile.TemporaryDirectory() as t:
        s = bs.Serie(Path(t), Path(t) / "d")
        commande = s.commande_pio
    attendu = [sys.executable, "-S", "-u", str(FAUX_PIO)]
    if commande != attendu:
        print(f"ARRET : la serie resout {commande!r} au lieu du faux pio {attendu!r}")
        sys.exit(2)
    verifie(commande, attendu, "garde-fou : BUILD_WEB_PIO -> faux pio lance par le Python courant")


# -- tests ----------------------------------------------------------------------------------------------

def test_commandes():
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t)
        m.lance([com(A)], {"compiler"})
        m.lance([com(A)], {"upload"})
        m.lance([com(A)], {"compiler", "upload"})
        m.lance([com(A)], {"buildfs"})
        m.lance([com(A, "COM12")], {"uploadfs"})
        argv = [a["argv"] for a in m.appels()]
        verifie(argv, [["run", "-e", A],
                       ["run", "-e", A, "-t", "upload", "--upload-port", "COM12"],
                       ["run", "-e", A, "-t", "upload", "--upload-port", "COM12"],
                       ["run", "-e", A, "-t", "buildfs"],
                       ["run", "-e", A, "-t", "uploadfs", "--upload-port", "COM12"]],
                "commandes : compiler, upload COM, compiler+upload (un seul -t upload), buildfs, uploadfs COM")
        a = m.appels()[0]
        verifie((a["pythonioencoding"], a["pythonutf8"], Path(a["cwd"]).resolve()),
                ("utf-8", "1", m.racine.resolve()), "commandes : PYTHONIOENCODING, PYTHONUTF8, cwd = racine")


def test_serie_upload_ota_par_page():
    appels = []

    def faux_firmware(env, ip, dossier_build, rapporte):
        appels.append((env, ip, dossier_build))
        rapporte({"etape": "Téléversement", "pourcent": 40, "detail": "x.bin vers " + ip})
        if ip == "192.168.0.66":
            raise RuntimeError("Téléversement : refusé par la carte")

    with tempfile.TemporaryDirectory() as t:
        m = Montage(t, ota_firmware=faux_firmware)
        ev = m.lance([ota(A, "192.168.0.50")], {"upload"})
        m.lance([ota(A, "192.168.0.50")], {"compiler", "buildfs"})
        pio = m.appels()
        verifie(pio[0]["argv"], ["run", "-e", A],
                "serie_upload_ota_par_page : pio compile seulement (ni -t upload ni --upload-port)")
        verifie(appels, [(A, "192.168.0.50", m.racine / ".pio" / "build" / A)],
                "serie_upload_ota_par_page : puis envoi par la page (env, ip, .pio/build/<env>)")
        verifie([(a["ota_ip"], a["platformio_upload_port"], a["platformio_extra_scripts"]) for a in pio],
                [(None, None, None)] * 3,
                "serie_upload_ota_par_page : temoins, aucune variable TASMOTA_OTA_IP / PLATFORMIO_* heritee")
        verifie([e["pourcent"] for e in du_type(ev, "etape", etape="Téléversement")][-1:], [40],
                "serie_upload_ota_par_page : progression de l'envoi -> evenement etape")
        verifie(du_type(ev, "fin_env")[0]["statuts"], {"upload": "succes"}, "serie_upload_ota_par_page : succes")
        ev = m.lance([ota(A, "192.168.0.66"), ota(B)], {"compiler", "upload"})
        verifie([x["statuts"] for x in du_type(ev, "fin_env")],
                [{"compiler": "succes", "upload": "echec"}, {"compiler": "succes", "upload": "succes"}],
                "serie_upload_ota_par_page : envoi refuse -> compiler succes, upload echec, la serie continue")
        e = du_type(ev, "echec", env=A)
        verifie(bool(e) and e[0]["motif"].startswith("Téléversement : "), True,
                "serie_upload_ota_par_page : motif de l'envoi transmis")
        (Path(t) / "sans").mkdir()
        m2 = Montage(Path(t) / "sans", ota_firmware=None)
        verifie(bool(m2.serie.controle([ota(A)], {"upload"})), True,
                "serie_upload_ota_par_page : sans fonction d'envoi, upload OTA refuse")


def test_ordre_actions():
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t)
        ev = m.lance([com(A)], {"uploadfs", "buildfs", "upload", "compiler"})
        verifie([a["cible"] for a in m.appels()], ["upload", "buildfs", "uploadfs"],
                "ordre_actions : upload (compile compris), buildfs, uploadfs")
        verifie(du_type(ev, "fin_env")[0]["statuts"],
                {"compiler": "succes", "upload": "succes", "buildfs": "succes", "uploadfs": "succes"},
                "ordre_actions : quatre actions en succes")


def test_serie_un_par_un():
    with tempfile.TemporaryDirectory() as t:
        lent = {"build": {"delai": 0.03}, "buildfs": {"delai": 0.03}}
        m = Montage(t, {"*": lent})
        m.lance([com(A), com(B), com(C)], {"compiler", "buildfs"})
        debuts, fins = m.appels("debut"), m.appels("fin")
        verifie((len(debuts), len(fins)), (6, 6), "serie_un_par_un : six fils lances et termines")
        chevauche = any(debuts[i + 1]["t"] < fins[i]["t"] for i in range(len(fins) - 1))
        verifie(chevauche, False, "serie_un_par_un : jamais deux fils vivants")
        verifie([d["env"] for d in debuts], [A, A, B, B, C, C], "serie_un_par_un : ordre des lignes")


def test_serie_continue_apres_echec():
    with tempfile.TemporaryDirectory() as t:
        echec = {"upload": {"code": 1, "lignes": ["Compiling .pio/build/{env}/src/a.cpp.o",
                                                    "src/a.cpp:3:1: error: 'x' was not declared",
                                                    "*** [.pio/build/{env}/src/a.cpp.o] Error 1",
                                                    "[FAILED] Took 0.20 seconds"]}}
        m = Montage(t, {B: echec})
        ev = m.lance([com(A, "COM1"), com(B, "COM2"), com(C, "COM3")], {"compiler", "upload"})
        statuts = {e["env"]: e["statuts"] for e in du_type(ev, "fin_env")}
        verifie(statuts.get(B), {"compiler": "echec", "upload": "annulee"},
                "serie_continue_apres_echec : env 2 en echec a la compilation, upload annulee")
        verifie((statuts.get(A), statuts.get(C)), ({"compiler": "succes", "upload": "succes"},) * 2,
                "serie_continue_apres_echec : env 1 et env 3 menes au bout")
        e = du_type(ev, "echec", env=B)
        verifie(bool(e) and any("error:" in x for x in e[0]["extrait"]), True,
                "serie_continue_apres_echec : evenement echec avec l'extrait d'erreur")
        verifie(du_type(ev, "fin")[0]["echecs"], [B], "serie_continue_apres_echec : fin cite l'env en echec")


def test_duree_des_la_fin():
    with tempfile.TemporaryDirectory() as t:
        lignes = [f"Compiling .pio/build/{{env}}/src/x{i}.o" for i in range(5)]
        lignes += ["Linking .pio/build/{env}/firmware.elf", "@pause 0.4", "[SUCCESS] Took 1 seconds"]
        m = Montage(t, {A: {"build": {"lignes": lignes, "delai": 0.05}}})
        ev = m.lance([com(A)], {"compiler"})
        d = du_type(ev, "duree", etape="Compilation")
        succes = [e for e in du_type(ev, "ligne") if "[SUCCESS]" in e["texte"]]
        verifie(bool(d) and bool(succes) and d[0]["n"] < succes[0]["n"], True,
                "duree_des_la_fin : duree de Compilation emise avant la fin du fils")
        verifie(bool(d) and 0.15 <= d[0]["secondes"] < 0.4, True,
                f"duree_des_la_fin : secondes plausibles ({d[0]['secondes'] if d else None})")
        verifie(bool(du_type(ev, "duree", etape="Édition des liens")), True,
                "duree_des_la_fin : derniere etape mesuree a la fin du fils")


def test_refus_build_en_cours():
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t, builds=lambda n: ["tasmota32-x upload"])
        motifs = m.serie.controle([com(A)], {"compiler"})
        verifie(any("build" in x and "tasmota32-x upload" in x for x in motifs), True,
                "refus_build_en_cours : motif cite le build")
        try:
            m.serie.lance([com(A)], {"compiler"})
            refuse = False
        except RuntimeError:
            refuse = True
        verifie((refuse, m.appels()), (True, []), "refus_build_en_cours : lance refuse, aucun fils")
        m.builds = lambda n: None
        verifie(any("détection" in x for x in m.serie.controle([com(A)], {"compiler"})), True,
                "refus_build_en_cours : detection impossible -> refus")
        m.builds = lambda n: []
        verifie(m.serie.controle([com(A)], {"compiler"}), [], "refus_build_en_cours : temoin, rien en cours")


def test_refus_port_tenu():
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t, ports={"COM7": "tenu", "COM9": "absent"})
        verifie(any("COM7" in x for x in m.serie.controle([com(A, "COM7")], {"upload"})), True,
                "refus_port_tenu : port tenu refuse")
        verifie(any("COM9" in x for x in m.serie.controle([com(A, "COM9")], {"uploadfs"})), True,
                "refus_port_tenu : port absent refuse")
        verifie(m.serie.controle([com(A, "COM7")], {"compiler", "buildfs"}), [],
                "refus_port_tenu : temoin, compiler seul ne regarde pas le port")


def test_refus_meme_port():
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t)
        motifs = m.serie.controle([com(A, "COM34"), com(B, "COM34")], {"upload"})
        verifie(any("COM34" in x for x in motifs), True, "refus_meme_port : deux envois sur COM34 refuses")
        verifie(m.serie.controle([com(A, "COM34"), com(B, "COM34")], {"compiler"}), [],
                "refus_meme_port : deux compilations seules acceptees")
        verifie(m.serie.controle([com(A, "COM34"), ota(B)], {"upload"}), [],
                "refus_meme_port : temoin, une ligne OTA n'occupe pas le port")


def test_refus_ip_vide():
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t)
        verifie(any(A in x and "IP" in x for x in m.serie.controle([ota(A, "")], {"upload"})), True,
                "refus_ip_vide : OTA sans IP refusee")
        verifie(bool(m.serie.controle([ota(A, "192.168.0.300")], {"upload"})), True,
                "refus_ip_vide : IP invalide refusee")
        verifie(bool(m.serie.controle([ota(P8266)], {"upload"})), True,
                "refus_ip_vide : env sans OTA (ESP8266) refuse en OTA")
        verifie(bool(m.serie.controle([com("tasmota32-inconnu")], {"compiler"})), True,
                "refus_ip_vide : env inconnu refuse")
        verifie(m.serie.controle([ota(A, "192.168.0.50")], {"upload"}), [], "refus_ip_vide : temoin, IP saisie")


def test_serie_attend_build_externe():
    with tempfile.TemporaryDirectory() as t:
        # appel 1 : controle du lancement ; appels 2 et 3 (avant l'env 2) : build de VS Code ; puis libre
        m = Montage(t, builds=lambda n: ["tasmota32-vscode"] if n in (2, 3) else [])
        ev = m.lance([com(A), com(B)], {"compiler"})
        att = du_type(ev, "attente", env=B)
        fin_a = du_type(ev, "fin_env", env=A)
        debut_b = du_type(ev, "debut", env=B)
        verifie(bool(att) and att[0]["builds"] == ["tasmota32-vscode"], True,
                "serie_attend_build_externe : evenement attente avec le build")
        verifie(bool(att and fin_a and debut_b) and fin_a[0]["n"] < att[0]["n"] < debut_b[0]["n"], True,
                "serie_attend_build_externe : attente entre l'env 1 et l'env 2")
        verifie([e["resultat"] for e in du_type(ev, "fin_env")], ["succes", "succes"],
                "serie_attend_build_externe : reprise, les deux envs en succes")
        verifie(m.appels_builds, 4, "serie_attend_build_externe : sondage jusqu'a liberation")


def test_serie_attend_detection_impossible():
    with tempfile.TemporaryDirectory() as t:
        # appel 1 : lancement ; appels 2 et 3 (avant l'env 2) : PowerShell en echec (None) ; puis libre
        heures_none = []

        def builds(n):
            if n in (2, 3):
                heures_none.append(time.time())
                return None
            return []

        m = Montage(t, builds=builds)
        ev = m.lance([com(A), com(B)], {"compiler"})
        att = du_type(ev, "attente", env=B)
        verifie([e["builds"] for e in att], [["détection impossible"], []],
                "serie_attend_detection_impossible : attente (detection impossible) puis reprise")
        debut_b = [a["t"] for a in m.appels() if a["env"] == B]
        verifie(bool(debut_b) and len(heures_none) == 2 and debut_b[0] > max(heures_none), True,
                "serie_attend_detection_impossible : aucun fils lance pendant la detection impossible")
        verifie([e["resultat"] for e in du_type(ev, "fin_env")], ["succes", "succes"],
                "serie_attend_detection_impossible : les deux envs en succes apres reprise")


def test_arret_apres_env():
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t, {A: {"build": {"lignes": ["Compiling a.o", "@pause 0.5", "[SUCCESS]"]}}})
        m.serie.lance([com(A), com(B), com(C)], {"compiler"})
        m.attend("debut", env=A)
        m.serie.arrete(False)
        ev = m.attend("fin")
        verifie([a["env"] for a in m.appels()], [A], "arret_apres_env : seul l'env en cours va au bout")
        f = du_type(ev, "fin")
        verifie(bool(f) and (f[0]["resultat"], f[0]["non_lances"]) == ("arrete", [B, C]), True,
                "arret_apres_env : fin arrete, envs suivants non lances")
        verifie([e["resultat"] for e in du_type(ev, "fin_env")], ["succes"], "arret_apres_env : env 1 en succes")


def test_arret_immediat():
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t, {A: {"build": {"petit_fils": True, "lignes": ["@pause 20", "[SUCCESS]"]}}})
        m.serie.lance([com(A), com(B)], {"compiler", "buildfs"})
        m.attend("ligne", texte="petit-fils lance")
        pids = [m.appels("debut")[0]["pid"], m.appels("petit_fils")[0]["pid"]]
        debut = time.monotonic()
        m.serie.arrete(True)
        ev = m.attend("fin", delai=10)
        verifie(time.monotonic() - debut < 5, True, "arret_immediat : arret en moins de 5 s")
        time.sleep(0.3)
        verifie([vivant(p) for p in pids], [False, False], "arret_immediat : arbre tue (fils et petit-fils)")
        verifie(du_type(ev, "fin_env")[0]["statuts"] if du_type(ev, "fin_env") else None,
                {"compiler": "echec", "buildfs": "annulee"}, "arret_immediat : env en echec, suite annulee")
        verifie(([a["env"] for a in m.appels()], m.serie.en_cours()), ([A], False),
                "arret_immediat : env 2 non lance, serie terminee")
        for p in pids:                                   # menage si l'arbre n'a pas ete tue
            if vivant(p):
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(p)], capture_output=True)


class SerieArretFinFils(bs.Serie):
    """Arret immediat demande juste apres la fin du fils pio `upload` (code deja lu), avant le verdict."""

    def _chrono(self, env, action):
        change, termine = super()._chrono(env, action)

        def termine_puis_arret():
            termine()
            if action == "upload":
                self.arrete(True)
        return change, termine_puis_arret


def test_upload_reussi_puis_arret_immediat():
    """I2 : un upload qui a reussi (code 0) reste un succes meme si l'arret immediat arrive juste apres."""
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t, classe=SerieArretFinFils)
        ev = m.lance([com(A)], {"upload", "buildfs"})
        fe = du_type(ev, "fin_env")
        verifie((fe[0]["statuts"], fe[0]["resultat"]) if fe else None,
                ({"upload": "succes", "buildfs": "annulee"}, "arrete"),
                "upload_reussi_puis_arret_immediat : upload succes (code 0), buildfs annulee, env arrete")
        verifie((du_type(ev, "echec"), [a["cible"] for a in m.appels()]), ([], ["upload"]),
                "upload_reussi_puis_arret_immediat : aucun echec annonce, buildfs non lance")


class SerieArretApresPio(bs.Serie):
    """Arret immediat demande des que le `pio run` qui precede un envoi OTA est fini (avec succes)."""

    def _lance_pio(self, ligne, action, cible):
        resultat = super()._lance_pio(ligne, action, cible)
        self.arrete(True)
        return resultat


def test_ota_annule_si_arret_immediat():
    """I5 : arret immediat demande avant l'envoi OTA -> l'envoi n'est pas fait, action « annulee »."""
    firmwares, fs = [], []
    with tempfile.TemporaryDirectory() as t:
        image = Path(t) / "image.bin"
        fabrique_image(image, FICHIERS_IMAGE)              # sans le correctif, ota_fs serait bien appele
        m = Montage(t, {"*": {"buildfs": {"image": str(image)}}}, classe=SerieArretApresPio,
                    ota_firmware=lambda *a: firmwares.append(a), ota_fs=lambda *a: fs.append(a))
        ev = m.lance([ota(A)], {"compiler", "upload"})
        fe = du_type(ev, "fin_env")
        verifie((firmwares, fe[0]["statuts"] if fe else None, fe[0]["resultat"] if fe else None, du_type(ev, "echec")),
                ([], {"compiler": "succes", "upload": "annulee"}, "arrete", []),
                "ota_annule_si_arret_immediat : firmware non envoye, compiler succes, upload annulee, pas d'echec")
        ev = m.lance([ota(A)], {"uploadfs"})
        fe = du_type(ev, "fin_env")
        verifie((fs, fe[0]["statuts"] if fe else None, fe[0]["resultat"] if fe else None),
                ([], {"uploadfs": "annulee"}, "arrete"),
                "ota_annule_si_arret_immediat : FS non envoye apres le buildfs de preparation, uploadfs annulee")


class SerieTemoinFin(bs.Serie):
    """Note l'etat de la serie au moment ou `fin` est emis."""

    def _ajoute(self, type_, env, **champs):
        if type_ == "fin":
            self.actif_a_la_fin = self._actif
        super()._ajoute(type_, env, **champs)


def test_fin_avant_liberation():
    """M1 : `fin` est emis AVANT que la serie ne se declare libre (sous le meme verrou)."""
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t, classe=SerieTemoinFin)
        m.lance([com(A)], {"compiler"})
        verifie((getattr(m.serie, "actif_a_la_fin", None), m.serie.en_cours()), (True, False),
                "fin_avant_liberation : serie encore active quand fin est emis, libre apres")


def test_journal_ecrit():
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t, {A: {"build": {"lignes": [f"{ESC}[32mCompiling .pio/build/x/a.o{ESC}[0m",
                                                  "[SUCCESS] é"]}}})
        m.lance([com(A)], {"compiler"})
        journaux = list((m.dossier / "journaux").glob("*.log"))
        texte = journaux[0].read_text(encoding="utf-8") if journaux else ""
        verifie((len(journaux), "Compiling .pio/build/x/a.o" in texte, ESC in texte, "[SUCCESS] é" in texte),
                (1, True, False, True), "journal_ecrit : un journal sans ANSI dans journaux/")


def test_reference_o_memorisee():
    with tempfile.TemporaryDirectory() as t:
        lignes = ["Compiling a.o", "Compiling b.o", "[SUCCESS]"]
        m = Montage(t, {A: {"build": {"lignes": lignes, "o": 4}}, B: {"build": {"code": 1, "o": 7}}})
        m.lance([com(A), com(B)], {"compiler"})
        ref = json.loads((m.dossier / "references.json").read_text(encoding="utf-8"))
        verifie(ref, {A: 4}, "reference_o_memorisee : 4 .o apres succes ; temoin, rien pour un echec")
        ev = m.lance([com(A)], {"compiler"})
        compiles = [e for e in du_type(ev, "etape", etape="Compilation") if e["detail"].endswith("fichiers")]
        verifie([(e["pourcent"], e["detail"]) for e in compiles], [(25, "1/4 fichiers"), (50, "2/4 fichiers")],
                "reference_o_memorisee : relue au lancement suivant (2/4 = 50 %)")


def test_rappel_fichiers_modifies():
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t)
        ev = m.lance([com(A)], {"compiler"})
        f = du_type(ev, "fin")
        fichiers = f[0].get("fichiers_modifies", []) if f else []
        verifie(("platformio_override.ini" in fichiers, "tasmota/user_config_override.h" in fichiers),
                (True, True), "rappel_fichiers_modifies : fin cite les deux fichiers reecrits")


def test_refus_double_lancement():
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t, {A: {"build": {"lignes": ["@pause 0.4", "[SUCCESS]"]}}})
        m.serie.lance([com(A)], {"compiler"})
        try:
            m.serie.lance([com(B)], {"compiler"})
            refuse = False
        except RuntimeError:
            refuse = True
        verifie((refuse, m.serie.en_cours()), (True, True), "refus_double_lancement : 2e lancement refuse")
        verifie(any("cours" in x for x in m.serie.controle([com(B)], {"compiler"})), True,
                "refus_double_lancement : motif lancement en cours")
        m.attend("fin")
        verifie([a["env"] for a in m.appels()], [A], "refus_double_lancement : un seul fils")


def test_uploadfs_ota():
    appels = []

    def faux_ota(env, ip, dossier_fs, sauvegardes, rapporte):
        appels.append((env, ip, Path(dossier_fs), arbre(dossier_fs), sauvegardes, sauvegardes.is_dir()))
        rapporte({"etape": "Envoi des fichiers", "pourcent": 50, "detail": "1/2 fichiers"})
        if ip == "192.168.0.66":
            raise RuntimeError("Sauvegarde du persist : carte injoignable")

    with tempfile.TemporaryDirectory() as t:
        image = Path(t) / "image-du-buildfs.bin"            # copiee par le faux buildfs dans .pio/build/<env>/
        fabrique_image(image, FICHIERS_IMAGE)
        m = Montage(t, {"*": {"buildfs": {"image": str(image)}}}, ota_fs=faux_ota)
        perime = m.racine / ".pio" / "build" / A / "littlefs_data"      # temoin : reste d'un build firmware
        perime.mkdir(parents=True)
        (perime / "_persist.json").write_bytes(b'{"perime": true}')
        (perime / "perime.be").write_bytes(b"print('perime')")
        ev = m.lance([ota(A, "192.168.0.50")], {"uploadfs"})
        verifie([a["cible"] for a in m.appels()], ["buildfs"], "uploadfs_ota : buildfs lance avant l'envoi")
        recu = appels[0] if appels else (None,) * 6
        verifie((recu[0], recu[1], recu[4], recu[5]), (A, "192.168.0.50", m.dossier / "persist", True),
                "uploadfs_ota : ota_fs(env, ip, <fichiers de l'image>, persist/, rapporte)")
        verifie(recu[3], FICHIERS_IMAGE,
                "uploadfs_ota : fichiers envoyes = contenu de littlefs.bin (image du buildfs), sous-dossiers compris")
        verifie((recu[2] != perime, "perime.be" in (recu[3] or {})), (True, False),
                "uploadfs_ota : temoin, littlefs_data perime a cote n'est PAS utilise")
        verifie(bool(recu[2]) and recu[2].exists(), False, "uploadfs_ota : dossier d'extraction efface apres l'envoi")
        verifie([e["pourcent"] for e in du_type(ev, "etape", etape="Envoi des fichiers")][-1:], [50],
                "uploadfs_ota : rapporte -> evenement etape")
        verifie(bool(du_type(ev, "duree", etape="Envoi des fichiers")), True, "uploadfs_ota : duree de l'envoi")
        verifie(du_type(ev, "fin_env")[0]["statuts"], {"uploadfs": "succes"}, "uploadfs_ota : succes")
        m.lance([ota(A, "192.168.0.50")], {"buildfs", "uploadfs"})
        verifie([a["cible"] for a in m.appels()][1:], ["buildfs"], "uploadfs_ota : buildfs coche, pas lance deux fois")
        ev = m.lance([ota(A, "192.168.0.66"), ota(B)], {"uploadfs"})
        e = du_type(ev, "echec", env=A)
        verifie(bool(e) and "injoignable" in e[0]["motif"], True, "uploadfs_ota : RuntimeError -> echec avec motif")
        verifie([x["resultat"] for x in du_type(ev, "fin_env")], ["echec", "succes"],
                "uploadfs_ota : la serie continue apres l'echec de l'envoi")
        (Path(t) / "sans").mkdir()
        m2 = Montage(Path(t) / "sans", ota_fs=None)
        verifie(bool(m2.serie.controle([ota(A)], {"uploadfs"})), True,
                "uploadfs_ota : sans fonction d'envoi, uploadfs OTA refuse")
        # buildfs reussi mais sans littlefs.bin (le faux buildfs ne copie rien) : echec clair, rien envoye
        (Path(t) / "sans-image").mkdir()
        appels.clear()
        m3 = Montage(Path(t) / "sans-image", ota_fs=faux_ota)
        ev = m3.lance([ota(A, "192.168.0.50")], {"uploadfs"})
        e = du_type(ev, "echec", env=A)
        verifie((bool(e) and "littlefs.bin" in e[0]["motif"] and "absent" in e[0]["motif"], appels), (True, []),
                "uploadfs_ota : littlefs.bin absent apres buildfs -> echec qui le dit, ota_fs non appele")


def test_garde_build_importable():
    module = bs.garde_build()
    verifie(callable(getattr(module, "builds_en_cours", None)), True,
            "garde_build : builds_en_cours importe sans lancer main()")


def principal():
    garde_fou()
    for test in (test_commandes, test_serie_upload_ota_par_page, test_ordre_actions, test_serie_un_par_un,
                 test_serie_continue_apres_echec, test_duree_des_la_fin, test_refus_build_en_cours,
                 test_refus_port_tenu, test_refus_meme_port, test_refus_ip_vide,
                 test_serie_attend_build_externe, test_serie_attend_detection_impossible,
                 test_arret_apres_env, test_arret_immediat, test_upload_reussi_puis_arret_immediat,
                 test_ota_annule_si_arret_immediat, test_fin_avant_liberation,
                 test_journal_ecrit, test_reference_o_memorisee, test_rappel_fichiers_modifies,
                 test_refus_double_lancement, test_uploadfs_ota, test_garde_build_importable):
        test()
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
