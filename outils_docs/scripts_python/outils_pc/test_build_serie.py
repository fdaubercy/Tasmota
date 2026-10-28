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
D = "tasmota32-essai-fs"                          # embarque des fichiers (custom_files_upload) : fs_avec_firmware
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

[env:{D}]
extends                 = env:tasmota32-essai-base
custom_files_upload     = data/essai/
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


def test_ota_par_maitre():
    """A11 : `IP:port` -> redirection et identite par le maitre AVANT l'envoi ; refus du maitre -> rien d'envoye."""
    appels = []

    def par_maitre(adresse, persist, env, rapporte):
        appels.append(("maitre", adresse, env))
        if adresse.endswith(":8082"):
            raise RuntimeError("Connexion par le maître : 192.168.0.43:8082 mène à CAPTEURS-CUVE")
        return "carte jointe par le maître : X"

    with tempfile.TemporaryDirectory() as t:
        m = Montage(t, ota_firmware=lambda env, ip, *a: appels.append(("envoi", ip, env)))
        m.serie.par_maitre = par_maitre
        verifie([bool(m.serie.controle([ota(A, ip)], {"upload"})) for ip in
                 ("192.168.0.43:8081", "192.168.0.43:0", "192.168.0.43:65536", "192.168.0.43:", "x:8081")],
                [False, True, True, True, True], "ota_par_maitre : IPv4:port accepte, port hors 1-65535 ou IP fausse refuses")
        ev = m.lance([ota(A, "192.168.0.43:8081"), ota(B, "192.168.0.43:8082"), ota(C, "192.168.0.50")], {"upload"})
        verifie(appels, [("maitre", "192.168.0.43:8081", A), ("envoi", "192.168.0.43:8081", A),
                         ("maitre", "192.168.0.43:8082", B), ("envoi", "192.168.0.50", C)],
                "ota_par_maitre : maitre consulte avant l'envoi, refus -> pas d'envoi, IP seule -> pas de maitre")
        verifie([x["statuts"]["upload"] for x in du_type(ev, "fin_env")], ["succes", "echec", "succes"],
                "ota_par_maitre : statuts des trois envs")
        verifie([e["detail"] for e in du_type(ev, "etape", env=A, etape="Connexion par le maître")], ["carte jointe par le maître : X"],
                "ota_par_maitre : carte jointe affichee dans la ligne de l'env")


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


def test_meme_port_accepte():
    """Choix 11 revise : deux envois sur le meme port sont acceptes (pause « rebranchez la carte ») ;
    le port est toujours verifie (tenu, absent)."""
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t, ports={"COM35": "tenu"})
        verifie(m.serie.controle([com(A, "COM34"), com(B, "COM34")], {"upload"}), [],
                "meme_port : deux envois sur COM34 acceptes (la serie fera une pause)")
        verifie(m.serie.controle([com(A, "COM34"), com(B, "COM34")], {"compiler"}), [],
                "meme_port : deux compilations seules acceptees")
        motifs = m.serie.controle([com(A, "COM35"), com(B, "COM35")], {"upload"})
        verifie(any("COM35" in x and "tenu" in x for x in motifs), True,
                "meme_port : temoin, port partage mais tenu par un autre outil -> refus")


# -- pause « rebranchez la carte » (deux envs d'une meme serie sur le meme port COM) ------------------

PAUSE_PORT = "COM34"


def lance_pause(m, lignes, actions):
    """Lance et attend la pause (evenement attente_carte) ; renvoie les evenements recus jusque-la."""
    m.serie.lance(lignes, set(actions))
    return m.attend("attente_carte")


def test_pause_avant_envoi():
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t)
        ev = lance_pause(m, [com(A, PAUSE_PORT), com(B, PAUSE_PORT)], {"compiler", "upload"})
        pause = du_type(ev, "attente_carte")
        verifie([(p["env"], p["port"], p["precedent"], p.get("fait"), p.get("erreur")) for p in pause],
                [(B, PAUSE_PORT, A, ["compiler"], "")],
                "pause : attente_carte (env, port, env precedent, deja fait : compilation, pas d'erreur)")
        verifie([a["argv"] for a in m.appels()],
                [["run", "-e", A, "-t", "upload", "--upload-port", PAUSE_PORT], ["run", "-e", B]],
                "pause : la compilation de l'env 2 se fait AVANT la pause, son envoi pas encore")
        verifie((m.serie.en_cours(), m.serie.envoi_en_cours(), m.serie.pause_en_cours()),
                (True, False, {"env": B, "port": PAUSE_PORT, "precedent": A}),
                "pause : serie en cours, aucun envoi en vol, pause exposee")
        time.sleep(0.3)
        verifie(len(m.appels()), 2, "pause : rien n'est lance tant que l'utilisateur n'a pas repondu")
        # apres la reponse, une pause bornee de controle des builds externes : un build est apparu pendant la pause
        k = m.appels_builds + 1
        m.builds = lambda n: ["tasmota32-vscode"] if n == k else []
        m.serie.reprend(B, "continuer")
        ev = m.attend("fin")
        verifie([a["argv"] for a in m.appels()][2:],
                [["run", "-e", B, "-t", "nobuild", "-t", "upload", "--upload-port", PAUSE_PORT]],
                "pause : Continuer -> envoi de l'env 2 sans recompiler (-t nobuild -t upload)")
        etapes_envoi = [e["etape"] for e in du_type(ev, "etape", env=B, action="upload")]
        verifie(("Compilation" in etapes_envoi, "Téléversement" in etapes_envoi), (False, True),
                f"pause : suivi de l'envoi sans etape Compilation ({etapes_envoi})")
        verifie([(e["env"], e["choix"]) for e in du_type(ev, "reprise_carte")], [(B, "continuer")],
                "pause : evenement reprise_carte (choix continuer)")
        verifie([e["builds"] for e in du_type(ev, "attente", env=B)], [["tasmota32-vscode"], []],
                "pause : build apparu pendant la pause -> attente avant l'envoi, puis reprise")
        verifie(du_type(ev, "fin_env", env=B)[0]["statuts"] if du_type(ev, "fin_env", env=B) else None,
                {"compiler": "succes", "upload": "succes"}, "pause : env 2 compile puis televerse, succes")
        verifie(m.serie.pause_en_cours(), None, "pause : plus de pause apres la reponse")


def test_pause_place():
    """Sans compiler, la pause precede le pio run qui compile et envoie ; une seule pause par env ; temoins."""
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t)
        ev = lance_pause(m, [com(A, PAUSE_PORT), com(B, PAUSE_PORT)], {"upload"})
        verifie(([a["env"] for a in m.appels()], du_type(ev, "attente_carte")[0].get("fait")), ([A], []),
                "pause_place : upload seul -> pause avant le pio run de l'env 2, rien de fait")
        m.serie.reprend(B, "continuer")
        m.attend("fin")
        verifie(m.appels()[-1]["argv"], ["run", "-e", B, "-t", "upload", "--upload-port", PAUSE_PORT],
                "pause_place : compiler non coche -> -t upload normal (il compile)")
        lance_pause(m, [com(A, PAUSE_PORT), com(B, PAUSE_PORT)], {"compiler", "erase_upload"})
        m.serie.reprend(B, "continuer")
        m.attend("fin")
        verifie([a["argv"] for a in m.appels()][-2:],
                [["run", "-e", B], ["run", "-e", B, "-t", "nobuild", "-t", "erase_upload", "--upload-port", PAUSE_PORT]],
                "pause_place : compiler + erase_upload -> compilation, pause, -t nobuild -t erase_upload")
        lance_pause(m, [com(A, PAUSE_PORT), com(B, PAUSE_PORT)], {"buildfs", "uploadfs"})
        verifie([(a["env"], a["cible"]) for a in m.appels()][-3:], [(A, "buildfs"), (A, "uploadfs"), (B, "buildfs")],
                "pause_place : buildfs + uploadfs -> FS de l'env 2 construit avant la pause")
        m.serie.reprend(B, "continuer")
        m.attend("fin")
        ev = lance_pause(m, [com(A, PAUSE_PORT), com(B, PAUSE_PORT)], {"upload", "uploadfs"})
        m.serie.reprend(B, "continuer")
        ev += m.attend("fin")
        verifie(len(du_type(ev, "attente_carte")), 1, "pause_place : upload + uploadfs -> une seule pause par env")
        ev = m.lance([com(A, "COM1"), com(B, "COM2"), ota(C)], {"upload"})
        verifie(du_type(ev, "attente_carte"), [], "pause_place : temoin, ports differents ou OTA -> aucune pause")
        ev = m.lance([com(A, PAUSE_PORT), com(B, PAUSE_PORT)], {"compiler", "buildfs"})
        verifie(du_type(ev, "attente_carte"), [], "pause_place : temoin, sans envoi -> aucune pause")


def test_pause_passer():
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t)
        lance_pause(m, [com(A, PAUSE_PORT), com(B, PAUSE_PORT), com(C, "COM3")], {"compiler", "upload"})
        m.serie.reprend(B, "passer")
        ev = m.attend("fin")
        fe = {e["env"]: (e["resultat"], e["statuts"]) for e in du_type(ev, "fin_env")}
        verifie(fe.get(B), ("passe", {"compiler": "succes", "upload": "annulee"}),
                "pause_passer : env passe, compilation faite, envoi annule")
        verifie((fe.get(C, ("",))[0], [a["env"] for a in m.appels()]), ("succes", [A, B, C]),
                "pause_passer : la serie continue (env 3), l'envoi de l'env 2 n'est pas lance")
        f = du_type(ev, "fin")[0] if du_type(ev, "fin") else {}
        verifie((f.get("succes"), f.get("echecs"), f.get("passes")), ([A, C], [], [B]), "pause_passer : fin cite l'env passe")


def test_pause_port_perdu():
    """Port absent ou tenu apres Continuer : la pause RESTE ouverte avec le message ; reessayer, passer, arreter."""
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t)
        lance_pause(m, [com(A, PAUSE_PORT), com(B, PAUSE_PORT), com(C, "COM3")], {"compiler", "upload"})
        m.ports[PAUSE_PORT] = "absent"                    # carte debranchee et pas rebranchee
        m.serie.reprend(B, "continuer")
        ev = m.attend("attente_carte")
        p = du_type(ev, "attente_carte")
        erreur = p[-1].get("erreur", "") if p else ""
        verifie((PAUSE_PORT in erreur, "absent" in erreur, "rebranchez" in erreur, m.serie.pause_en_cours() is not None),
                (True, True, True, True), f"pause_port_perdu : port absent -> pause rouverte avec le message ({erreur})")
        verifie((du_type(ev, "echec"), du_type(ev, "reprise_carte"), len(m.appels())), ([], [], 2),
                "pause_port_perdu : ni echec ni envoi, la pause continue")
        m.ports[PAUSE_PORT] = "tenu"
        m.serie.reprend(B, "continuer")
        p = du_type(m.attend("attente_carte"), "attente_carte")
        verifie(bool(p) and "tenu par un autre outil" in p[-1].get("erreur", ""), True,
                "pause_port_perdu : port tenu -> message, pause gardee")
        m.ports[PAUSE_PORT] = "libre"                     # carte rebranchee : nouvel essai
        m.serie.reprend(B, "continuer")
        ev = m.attend("fin")
        fe = {e["env"]: (e["resultat"], e["statuts"]) for e in du_type(ev, "fin_env")}
        verifie((fe.get(B), fe.get(C, ("",))[0]), (("succes", {"compiler": "succes", "upload": "succes"}), "succes"),
                "pause_port_perdu : rebranchee puis Continuer -> envoi fait, la serie continue")
        lance_pause(m, [com(A, PAUSE_PORT), com(B, PAUSE_PORT)], {"upload"})
        m.ports[PAUSE_PORT] = "absent"                    # absent apres le lancement (le controle l'aurait refuse avant)
        m.serie.reprend(B, "continuer")
        m.attend("attente_carte")
        m.serie.reprend(B, "passer")
        fe = du_type(m.attend("fin"), "fin_env", env=B)
        verifie(fe[0]["resultat"] if fe else None, "passe", "pause_port_perdu : apres le message, Passer reste possible")
        m.ports[PAUSE_PORT] = "libre"
        lance_pause(m, [com(A, PAUSE_PORT), com(B, PAUSE_PORT)], {"upload"})
        m.ports[PAUSE_PORT] = "absent"
        m.serie.reprend(B, "continuer")
        m.attend("attente_carte")
        m.serie.arrete(False)
        fe = du_type(m.attend("fin", delai=5), "fin_env", env=B)
        verifie(fe[0]["resultat"] if fe else None, "arrete", "pause_port_perdu : apres le message, l'arret marche")


def test_pause_reprend_refus():
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t)

        def refus(env, choix):
            try:
                m.serie.reprend(env, choix)
                return "accepte"
            except RuntimeError:
                return "RuntimeError"
            except ValueError:
                return "ValueError"

        verifie(refus(B, "continuer"), "RuntimeError", "reprend : aucune pause en cours -> refus")
        lance_pause(m, [com(A, PAUSE_PORT), com(B, PAUSE_PORT)], {"upload"})
        verifie((refus(A, "continuer"), refus(B, "rien"), m.serie.pause_en_cours() is not None),
                ("RuntimeError", "ValueError", True), "reprend : autre env ou choix invalide -> refus, pause gardee")
        verifie(refus(B, "continuer"), "accepte", "reprend : temoin, bon env et bon choix")
        m.attend("fin")


def test_pause_arrets():
    """Les deux arrets ne restent pas bloques sur une pause."""
    for immediat in (False, True):
        with tempfile.TemporaryDirectory() as t:
            m = Montage(t)
            lance_pause(m, [com(A, PAUSE_PORT), com(B, PAUSE_PORT), com(C, "COM3")], {"compiler", "upload"})
            debut = time.monotonic()
            m.serie.arrete(immediat)
            ev = m.attend("fin", delai=5)
            nom = "arret immediat" if immediat else "arreter apres cet env"
            verifie(time.monotonic() - debut < 2, True, f"pause_arrets : {nom} pendant la pause -> fin rapide")
            fe = du_type(ev, "fin_env", env=B)
            verifie((fe[0]["resultat"], fe[0]["statuts"]) if fe else None, ("arrete", {"compiler": "succes", "upload": "annulee"}),
                    f"pause_arrets : {nom} -> env 2 arrete, envoi annule")
            f = du_type(ev, "fin")
            verifie((f[0]["resultat"], f[0]["non_lances"], f[0]["echecs"], f[0].get("arretes")) if f else None,
                    ("arrete", [C], [], [B]),
                    f"pause_arrets : {nom} -> serie arretee, env 2 arrete (pas un echec), env 3 non lance")
            verifie((m.serie.en_cours(), [a["env"] for a in m.appels()]), (False, [A, B]),
                    f"pause_arrets : {nom} -> aucun envoi de l'env 2")


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


def test_envoi_en_cours():
    """M7 : envoi_en_cours() vrai pendant un envoi vers une carte seulement (pas pendant la compilation)."""
    import threading
    vus, libere = [], threading.Event()
    with tempfile.TemporaryDirectory() as t:
        ecriture = ["Compiling .pio/build/{env}/src/a.cpp.o", "@pause 0.6", "Linking .pio/build/{env}/firmware.elf",
                    "Uploading .pio/build/{env}/firmware.bin", "Writing at 0x00010000 (10 %)", "@pause 0.6",
                    "[SUCCESS]"]

        def firmware_lent(env, ip, dossier_build, rapporte):
            vus.append(("ota", m.serie.envoi_en_cours()))
            libere.wait(5)

        m = Montage(t, {A: {"upload": {"lignes": ecriture}}}, ota_firmware=firmware_lent)
        m.serie.lance([com(A)], {"upload"})
        m.attend("etape", etape="Compilation")
        vus.append(("compilation", m.serie.envoi_en_cours()))
        m.attend("etape", etape="Téléversement")
        vus.append(("televersement", m.serie.envoi_en_cours()))
        m.attend("fin")
        vus.append(("fin", m.serie.envoi_en_cours()))
        libere.set()
        m.lance([ota(B)], {"upload"})
        verifie(vus, [("compilation", False), ("televersement", True), ("fin", False), ("ota", True)],
                "envoi_en_cours : faux en compilation, vrai en Televersement par cable et pendant l'envoi OTA")


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
        verifie(ref, {A: {"total": 4, "increment": 2}},
                "reference_o_memorisee : 4 .o et increment 2 apres succes ; temoin, rien pour un echec")
        ev = m.lance([com(A)], {"compiler"})
        compiles = [e for e in du_type(ev, "etape", etape="Compilation") if e["detail"].endswith("fichiers")]
        verifie([(e["pourcent"], e["detail"]) for e in compiles], [(50, "1/2 fichiers"), (99, "2/2 fichiers")],
                "reference_o_memorisee : increment relu au lancement suivant (1/2 = 50 %)")
        # Build complet (objets repris du cache) : le total change, l'increment reste celui d'avant
        complet = ["Retrieved `x/c.o' from cache", "Compiling a.o", "[SUCCESS]"]
        m.scenario.write_text(json.dumps({A: {"build": {"lignes": complet, "o": 4}}}), encoding="utf-8")
        m.lance([com(A)], {"compiler"})
        ref = json.loads((m.dossier / "references.json").read_text(encoding="utf-8"))
        verifie(ref[A], {"total": 4, "increment": 2}, "reference_o_memorisee : build complet -> increment garde")
        # Ancien format (un entier) : lu comme le total
        (m.dossier / "references.json").write_text(json.dumps({A: 8}), encoding="utf-8")
        m.scenario.write_text(json.dumps({A: {"build": {"lignes": lignes, "o": 4}}}), encoding="utf-8")
        ev = m.lance([com(A)], {"compiler"})
        compiles = [e for e in du_type(ev, "etape", etape="Compilation") if e["detail"].endswith("fichiers")]
        verifie([e["detail"] for e in compiles], ["1/8 fichiers", "2/8 fichiers"],
                "reference_o_memorisee : ancien format entier = total")


def test_reference_estimee():
    # Env sans reference (premier build par la page) : total emprunte au plus grand env de la meme puce
    with tempfile.TemporaryDirectory() as t:
        lignes = ["Compiling a.o", "Compiling b.o", "[SUCCESS]"]
        m = Montage(t, {B: {"build": {"lignes": lignes, "o": 4}}})

        def details(references):
            (m.dossier / "references.json").write_text(json.dumps(references), encoding="utf-8")
            ev = m.lance([com(B)], {"compiler"})
            return [(e["pourcent"], e["detail"]) for e in du_type(ev, "etape", etape="Compilation")
                    if e["detail"].endswith("fichiers")]

        m.dossier.mkdir(parents=True, exist_ok=True)
        verifie(details({A: {"total": 8, "increment": None}, C: 20, "tasmota32s3-autre": {"total": 100}}),
                [(5, "1/≈20 fichiers"), (10, "2/≈20 fichiers")],
                "reference_estimee : plus grand total de la meme puce (C, ancien format compris), pas le S3")
        ref = json.loads((m.dossier / "references.json").read_text(encoding="utf-8"))
        verifie(ref.get(B), {"total": 4, "increment": 2}, "reference_estimee : vrai total memorise apres succes")
        verifie(details({"tasmota32s3-autre": {"total": 100}}), [(None, "1 fichiers"), (None, "2 fichiers")],
                "reference_estimee : temoin, aucune puce identique -> compte seul")


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


def test_erase_upload_commandes():
    """A10 : erase_upload = un seul `-t erase_upload --upload-port`, a la place de l'upload dans l'ordre."""
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t, {A: {"erase_upload": {"o": 3}}})
        ev = m.lance([com(A)], {"erase_upload"})
        ev2 = m.lance([com(A, "COM7")], {"uploadfs", "buildfs", "erase_upload", "compiler"})
        verifie([a["argv"] for a in m.appels()],
                [["run", "-e", A, "-t", "erase_upload", "--upload-port", "COM12"],
                 ["run", "-e", A, "-t", "erase_upload", "--upload-port", "COM7"],
                 ["run", "-e", A, "-t", "buildfs"], ["run", "-e", A, "-t", "uploadfs", "--upload-port", "COM7"]],
                "erase_upload : -t erase_upload --upload-port, compile compris, a la place de l'upload dans l'ordre")
        verifie((du_type(ev, "fin_env")[0]["statuts"], du_type(ev2, "fin_env")[0]["statuts"]),
                ({"erase_upload": "succes"},
                 {"compiler": "succes", "erase_upload": "succes", "buildfs": "succes", "uploadfs": "succes"}),
                "erase_upload : statuts (compiler couvert par le meme pio run)")
        verifie(bool(du_type(ev, "etape", etape="Effacement de la flash")), True, "erase_upload : etape Effacement de la flash")
        ref = json.loads((m.dossier / "references.json").read_text(encoding="utf-8")) if (m.dossier / "references.json").is_file() else {}
        verifie(ref.get(A, {}).get("total"), 3, "erase_upload : objets de reference memorises (il compile)")


def test_erase_upload_refus():
    """A10 : COM seulement, exclusif avec upload, compte comme un envoi (port tenu, meme port)."""
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t, ports={"COM7": "tenu"})
        motifs = m.serie.controle([com(A)], {"upload", "erase_upload"})
        verifie(any("Effacer puis téléverser" in x and "Téléverser le firmware" in x for x in motifs), True,
                "erase_upload_refus : avec upload -> refus (l'une ou l'autre)")
        verifie(any(A in x and "COM" in x for x in m.serie.controle([ota(A)], {"erase_upload"})), True,
                "erase_upload_refus : ligne OTA refusee (cable seulement)")
        verifie(any("COM7" in x for x in m.serie.controle([com(A, "COM7")], {"erase_upload"})), True,
                "erase_upload_refus : port tenu refuse (c'est un envoi)")
        verifie(any("COM7" in x for x in m.serie.controle([com(A, "COM7"), com(B, "COM7")], {"erase_upload"})), True,
                "erase_upload_refus : port partage et tenu -> refus (l'envoi partage n'echappe pas au controle)")
        verifie(bool(m.serie.controle([com(A, "")], {"erase_upload"})), True, "erase_upload_refus : port vide refuse")
        verifie(m.serie.controle([com(A)], {"compiler", "erase_upload", "buildfs", "uploadfs"}), [],
                "erase_upload_refus : temoin, combinable avec compiler, buildfs, uploadfs")
        try:
            m.serie.lance([ota(A)], {"erase_upload"})
            refuse = False
        except RuntimeError:
            refuse = True
        verifie((refuse, m.appels()), (True, []), "erase_upload_refus : lance refuse en OTA, aucun fils")


def test_erase_upload_envoi_et_echec():
    """A10 : envoi_en_cours vrai des l'effacement (M7) ; echec a l'effacement -> compiler succes, erase_upload echec."""
    lignes = ["Compiling .pio/build/{env}/src/a.cpp.o", "@pause 0.6", "Linking .pio/build/{env}/firmware.elf",
              "Looking for upload port...", "Erasing...", "Erasing flash memory (this may take a while)...", "@pause 0.6",
              "Flash memory erased successfully in 0.6 seconds.", "Uploading .pio/build/{env}/firmware.bin",
              "Writing at 0x00010000 (10 %)", "@pause 0.6", "[SUCCESS]"]
    vus = []
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t, {A: {"erase_upload": {"lignes": lignes}}})
        m.serie.lance([com(A)], {"erase_upload"})
        for etape in ("Compilation", "Effacement de la flash", "Téléversement"):
            m.attend("etape", etape=etape)
            vus.append((etape, m.serie.envoi_en_cours()))
        m.attend("fin")
        verifie(vus, [("Compilation", False), ("Effacement de la flash", True), ("Téléversement", True)],
                "erase_upload_envoi : faux en compilation, vrai pendant l'effacement et le televersement")
        rate = ["Compiling a.o", "Linking firmware.elf", "Looking for upload port...", "Erasing...",
                "A fatal error occurred: Could not open COM12, the port is busy or doesn't exist.",
                "*** [erase_upload] Error 2", "[FAILED] Took 1 seconds"]
        m.scenario.write_text(json.dumps({A: {"erase_upload": {"code": 1, "lignes": rate}},
                                          B: {"erase_upload": {"code": 1, "lignes": ["Compiling a.o", "x.cpp:1: error: y",
                                                                                     "[FAILED]"]}}}), encoding="utf-8")
        ev = m.lance([com(A, "COM1"), com(B, "COM2")], {"compiler", "erase_upload"})
        verifie([x["statuts"] for x in du_type(ev, "fin_env")],
                [{"compiler": "succes", "erase_upload": "echec"}, {"compiler": "echec", "erase_upload": "annulee"}],
                "erase_upload_echec : a l'effacement -> erase_upload echec ; temoin, a la compilation -> annulee")
        e = du_type(ev, "echec", env=A)
        verifie(bool(e) and any("fatal error" in x for x in e[0]["extrait"]), True,
                "erase_upload_echec : message d'esptool dans l'extrait")


def berry_custom(racine, plein):
    """modules.h qui inscrit le module demarrage ; son .h solidifie est vide sauf si `plein`."""
    src = racine / "lib" / "libesp32" / "berry_custom" / "src"
    (src / "solidify").mkdir(parents=True, exist_ok=True)
    (src / "modules.h").write_text("#define CUSTOM_NATIVE_MODULES &be_native_module(demarrage),\n"
                                   "be_extern_native_module(demarrage);", encoding="utf-8")
    (src / "solidify" / "solidified_demarrage.h").write_text(
        '#include "be_constobj.h"\n' + ("be_define_const_native_module(demarrage);\n" if plein else ""),
        encoding="utf-8")


def test_solidification_vide():
    lignes = ["Processing {env} (platform: espressif32)", "Will solidify  demarrage.be", "demarrage is a module",
              "Compiling .pio\\build\\{env}\\src\\a.cpp.o", "@pause 15", "Linking .pio\\build\\{env}\\firmware.elf",
              "[SUCCESS] Took 15.00 seconds"]
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t, {A: {"upload": {"lignes": lignes}}})
        berry_custom(m.racine, plein=False)
        debut = time.monotonic()
        ev = m.lance([com(A, "COM1")], {"upload"})
        duree = time.monotonic() - debut
        statuts = {e["env"]: e["statuts"] for e in du_type(ev, "fin_env")}
        verifie(statuts.get(A), {"upload": "echec"}, "solidification_vide : env en echec")
        e = du_type(ev, "echec", env=A)
        verifie(bool(e) and e[0]["motif"].startswith("solidification vide : demarrage"), True,
                "solidification_vide : motif nomme le module vide")
        verifie(duree < 10, True, f"solidification_vide : pio arrete des la compilation ({duree:.1f} s, pas 15)")
        verifie(len(m.appels("fin")), 0, "solidification_vide : le faux pio a ete tue (pas de ligne fin)")
        verifie(any("solidification vide" in x.get("texte", "") for x in du_type(ev, "ligne", env=A)), True,
                "solidification_vide : la raison apparait dans la sortie de l'env")
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t, {A: {"upload": {"lignes": lignes[:4] + lignes[5:]}}})
        berry_custom(m.racine, plein=True)
        ev = m.lance([com(A, "COM1")], {"upload"})
        verifie({e["env"]: e["statuts"] for e in du_type(ev, "fin_env")}.get(A), {"upload": "succes"},
                "solidification_vide : temoin, .h plein -> upload mene au bout")
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t, {A: {"buildfs": {"lignes": lignes[:4] + lignes[5:]}}})
        berry_custom(m.racine, plein=False)
        ev = m.lance([com(A, "COM1")], {"buildfs"})
        verifie({e["env"]: e["statuts"] for e in du_type(ev, "fin_env")}.get(A), {"buildfs": "succes"},
                "solidification_vide : buildfs (pas d'edition des liens) non controle")


def test_fs_par_firmware():
    """L'envoi serie du firmware d'un env a custom_files_upload ecrit aussi le FS (post_esp32) : buildfs /
    uploadfs coches ne lancent pas de pio run a part et suivent le sort de cet envoi. Temoin : env sans
    fichiers (A), qui garde ses trois pio run."""
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t)
        ev = m.lance([com(D)], {"upload", "buildfs", "uploadfs"})
        ev2 = m.lance([com(D, "COM7")], {"erase_upload", "uploadfs"})
        ev3 = m.lance([com(A)], {"upload", "buildfs", "uploadfs"})
        verifie([a["argv"] for a in m.appels()],
                [["run", "-e", D, "-t", "upload", "--upload-port", "COM12"],
                 ["run", "-e", D, "-t", "erase_upload", "--upload-port", "COM7"],
                 ["run", "-e", A, "-t", "upload", "--upload-port", "COM12"],
                 ["run", "-e", A, "-t", "buildfs"], ["run", "-e", A, "-t", "uploadfs", "--upload-port", "COM12"]],
                "fs_par_firmware : env a fichiers -> un seul pio run (upload ou erase_upload) ; temoin A -> trois")
        verifie((du_type(ev, "fin_env")[0]["statuts"], du_type(ev2, "fin_env")[0]["statuts"]),
                ({"upload": "succes", "buildfs": "succes", "uploadfs": "succes"},
                 {"erase_upload": "succes", "uploadfs": "succes"}),
                "fs_par_firmware : buildfs / uploadfs reussis avec l'envoi du firmware")
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t, {D: {"upload": {"code": 1, "lignes": ["[FAILED] Took 0.20 seconds"]}}})
        ev = m.lance([com(D, "COM1"), com(A, "COM2")], {"upload", "buildfs"})
        statuts = {e["env"]: e["statuts"] for e in du_type(ev, "fin_env")}
        verifie((statuts.get(D), statuts.get(A)),
                ({"upload": "echec", "buildfs": "echec"}, {"upload": "succes", "buildfs": "succes"}),
                "fs_par_firmware : envoi en echec -> FS en echec ; serie mixte, A construit son FS")
        verifie([a["argv"] for a in m.appels()],
                [["run", "-e", D, "-t", "upload", "--upload-port", "COM1"],
                 ["run", "-e", A, "-t", "upload", "--upload-port", "COM2"], ["run", "-e", A, "-t", "buildfs"]],
                "fs_par_firmware : serie mixte, buildfs lance pour A seulement")


def test_data_dir_avant_pio():
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t)
        (m.racine / "platformio_override.ini").write_text("[platformio]\ndata_dir = data/garage/autre\n", encoding="utf-8")
        ev = m.lance([com(A, "COM1"), com(B, "COM2")], {"buildfs"})
        verifie([(a["env"], a["data_dir"]) for a in m.appels()],
                [(A, "data/essai/tasmota32-a"), (B, "data/essai/tasmota32-b")],
                "data_dir_avant_pio : chaque pio lit le dossier de SON env, pas celui du lancement precedent")
        verifie(any("data_dir" in x.get("texte", "") for x in du_type(ev, "ligne", env=A)), True,
                "data_dir_avant_pio : le changement apparait dans la sortie de l'env")
        m.lance([com(B, "COM2")], {"buildfs"})
        verifie(m.appels()[-1]["data_dir"], "data/essai/tasmota32-b", "data_dir_avant_pio : temoin, meme env -> inchange")


def test_uploadfs_ota_identite():
    appels = []

    def faux_ota(env, ip, dossier_fs, sauvegardes, rapporte):
        appels.append(env)

    def persist(hote, topic):
        return json.dumps({"serveur": {"hostname": hote, "mqtt": {"topic": topic}}}).encode("utf-8")

    with tempfile.TemporaryDirectory() as t:
        image = Path(t) / "image.bin"
        fabrique_image(image, dict(FICHIERS_IMAGE, **{"_persist.json": persist("CAPTEURS-CUVE", "jardin/cuve")}))
        m = Montage(t, {"*": {"buildfs": {"image": str(image)}}}, ota_fs=faux_ota)
        depot = m.racine / "data" / "essai" / "tasmota32-a"
        depot.mkdir(parents=True)
        (depot / "_persist.json").write_bytes(persist("SERVEUR-GARAGE", "garage"))
        ev = m.lance([ota(A, "192.168.0.50")], {"uploadfs"})
        e = du_type(ev, "echec", env=A)
        verifie((bool(e) and "CAPTEURS-CUVE" in e[0]["motif"], appels), (True, []),
                "uploadfs_ota_identite : image d'un autre env -> echec qui le dit, rien envoye")
        (depot / "_persist.json").write_bytes(persist("CAPTEURS-CUVE", "jardin/cuve"))
        ev = m.lance([ota(A, "192.168.0.50")], {"uploadfs"})
        verifie((du_type(ev, "fin_env")[0]["statuts"], appels), ({"uploadfs": "succes"}, [A]),
                "uploadfs_ota_identite : temoin, meme identite -> envoyee")
        verifie(any("CAPTEURS-CUVE" in (x.get("detail") or "") for x in du_type(ev, "etape", env=A)), True,
                "uploadfs_ota_identite : l'identite verifiee apparait dans l'etape")


def test_pourcent_global_envoi():
    """A13 : les durees des zones d'un envoi par cable reussi sont memorisees ; l'envoi suivant a un % global."""
    zone = lambda nom, s: [f"Writing 'C:\\x\\.pio\\build\\{{env}}\\{nom}' at 0x00010000...",
                           "Writing at 0x00010000 [=====] 50.0% 8kB/16kB [0s] ",
                           f"Wrote 16384 bytes (8192 compressed) at 0x00010000 in {s} seconds (100.0 kbit/s)."]
    lignes = (["Processing {env} (platform: espressif32)", "Compiling .pio\\build\\{env}\\src\\a.cpp.o",
               "Uploading .pio\\build\\{env}\\firmware.bin"] + zone("bootloader.bin", 1.0) + zone("firmware.bin", 3.0)
              + ["[SUCCESS] Took 5.00 seconds"])
    with tempfile.TemporaryDirectory() as t:
        m = Montage(t, {A: {"upload": {"lignes": lignes, "o": 1}}})
        ev = m.lance([com(A, "COM1")], {"upload"})
        refs = json.loads((m.dossier / "references.json").read_text(encoding="utf-8"))
        verifie(refs.get(A, {}).get("zones"), [["bootloader.bin", 1.0], ["firmware.bin", 3.0]],
                "pourcent_global_envoi : durees des zones memorisees apres l'envoi reussi")
        premier = [e["pourcent"] for e in du_type(ev, "etape", env=A, etape="Téléversement")]
        ev = m.lance([com(A, "COM1")], {"upload"})
        envoi = du_type(ev, "etape", env=A, etape="Téléversement")
        verifie([e["pourcent"] for e in envoi if e["detail"] != "terminé"][-2:], [25, 62],
                f"pourcent_global_envoi : 2e envoi, % de l'envoi entier (bootloader 50 % = 12, firmware 50 % = 62 ; "
                f"1er envoi : {premier})")
        verifie(any("zone 2/2" in e["detail"] for e in envoi), True, "pourcent_global_envoi : « zone k/n » dans le detail")
        verifie(refs[A].get("total"), 1, "pourcent_global_envoi : temoin, le total des .o reste memorise a cote")


def test_garde_build_importable():
    module = bs.garde_build()
    verifie(callable(getattr(module, "builds_en_cours", None)), True,
            "garde_build : builds_en_cours importe sans lancer main()")


def principal():
    garde_fou()
    for test in (test_commandes, test_serie_upload_ota_par_page, test_ota_par_maitre, test_ordre_actions, test_serie_un_par_un,
                 test_serie_continue_apres_echec, test_duree_des_la_fin, test_refus_build_en_cours,
                 test_refus_port_tenu, test_meme_port_accepte, test_refus_ip_vide,
                 test_pause_avant_envoi, test_pause_place, test_pause_passer, test_pause_port_perdu,
                 test_pause_reprend_refus, test_pause_arrets,
                 test_serie_attend_build_externe, test_serie_attend_detection_impossible,
                 test_arret_apres_env, test_arret_immediat, test_upload_reussi_puis_arret_immediat,
                 test_ota_annule_si_arret_immediat, test_fin_avant_liberation, test_envoi_en_cours,
                 test_journal_ecrit, test_reference_o_memorisee, test_reference_estimee, test_rappel_fichiers_modifies,
                 test_refus_double_lancement, test_uploadfs_ota, test_garde_build_importable,
                 test_erase_upload_commandes, test_erase_upload_refus, test_erase_upload_envoi_et_echec,
                 test_solidification_vide, test_fs_par_firmware, test_data_dir_avant_pio,
                 test_uploadfs_ota_identite, test_pourcent_global_envoi):
        test()
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
