"""Banc du lanceur de l'annuaire (annuaire_lanceur.py) : lancement, console, arret de l'arbre, Job Object.

Code de sortie 0 = vert. Les faux outils sont de petits scripts ecrits dans un dossier temporaire, qui
dorment 60 s. Chaque processus cree par le banc est suivi par un HANDLE ouvert des que son PID est connu :
tant que le handle reste ouvert, Windows ne recycle pas le PID, et le nettoyage (TerminateProcess par
handle) ne peut pas toucher un autre processus (le build de l'utilisateur lance beaucoup de python.exe).
"""

import ctypes
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ICI = os.path.dirname(os.path.abspath(__file__))
DOSSIER = tempfile.mkdtemp(prefix="banc_lanceur_")
os.environ["OUTILS_TASMOTA_DOSSIER"] = DOSSIER          # avant tout import d'acces_web

import annuaire_lanceur as al          # noqa: E402
import annuaire_presence as pre        # noqa: E402
import annuaire_registre as reg        # noqa: E402

ECHECS = []
RACINE = Path(DOSSIER) / "racine"
CREATE_NO_WINDOW = 0x08000000

FAUX_OUTIL = r'''
import ctypes, os, sys, time
fichier = sys.argv[1]
liste = (ctypes.c_uint32 * 64)()
n = ctypes.windll.kernel32.GetConsoleProcessList(liste, 64)       # 0 = pas de console
with open(fichier + ".console", "w") as f:
    f.write(" ".join(str(liste[i]) for i in range(min(n, 64))))
nb = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 0
for i in range(nb):
    print(f"ligne {i}")
print(f"faux outil pret pid={os.getpid()} lance_par={os.environ.get('OUTILS_TASMOTA_LANCE_PAR')} "
      f"utf8={os.environ.get('PYTHONUTF8')} cwd={os.getcwd()} args={sys.argv[1:]}", flush=True)
with open(fichier + ".tmp", "w") as f:
    f.write(str(os.getpid()))
os.replace(fichier + ".tmp", fichier)
time.sleep(60)
'''

FAUX_PARENT = r'''
import os, subprocess, sys, time
fichier = sys.argv[1]
outil = os.path.join(os.path.dirname(os.path.abspath(__file__)), "faux_outil.py")
enfant = subprocess.Popen([sys.executable, outil, fichier + ".enfant"])
with open(fichier + ".tmp", "w") as f:
    f.write(f"{os.getpid()} {enfant.pid}")
os.replace(fichier + ".tmp", fichier)
time.sleep(60)
'''

# argv : dossier outils_pc, racine, python des outils, mode (job | sans | refus | ancien), fichier de sortie
# ancien = job, mais drapeaux hors job d'avant le correctif (sans CREATE_NO_WINDOW) : temoin console
MINI_ANNUAIRE = r'''
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import annuaire_lanceur as al
import annuaire_registre as reg
racine, python, mode, sortie = Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]
ok = None
if mode in ("job", "ancien"):
    ok = al.rattache_au_job()
if mode == "ancien":
    al.DRAPEAUX_HORS_JOB = al.CREATE_BREAKAWAY_FROM_JOB | al.CREATE_NEW_PROCESS_GROUP
elif mode == "refus":
    ok = al._rattache(al.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)     # job SANS breakaway autorise
def outil(id, dans_job):
    return reg.Outil(id, id, id, reg.GROUPES[0], "i", "a", "faux_outil.py", [], "", "j", dans_job=dans_job)
lanceur = al.Lanceur(racine, python=python)
prefixe = sortie[:-len(".json")]
p_job = None if mode == "refus" else lanceur.lance(outil("faux_job", True), [prefixe + "_job.pid"])
p_hors = lanceur.lance(outil("faux_hors", False), [prefixe + "_hors.pid"])
lie = {id: info.get("lie") for id, info in lanceur.lances.items()}
with open(sortie + ".tmp", "w") as f:
    json.dump({"ok": ok, "moi": os.getpid(), "p_job": p_job, "p_hors": p_hors, "lie": lie}, f)
os.replace(sortie + ".tmp", sortie)
time.sleep(60)
'''


# --- suivi des processus du banc, par handle --------------------------------------------------------

K32 = ctypes.WinDLL("kernel32", use_last_error=True)
K32.OpenProcess.restype = ctypes.c_void_p
K32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
K32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
K32.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
K32.CloseHandle.argtypes = [ctypes.c_void_p]
SUIVIS = {}         # pid -> handle


def garde(pid):
    """Ouvre (une fois) un handle sur un processus du banc ; le PID ne peut plus etre recycle."""
    pid = int(pid)
    if pid not in SUIVIS:
        h = K32.OpenProcess(0x1000 | 0x0001 | 0x00100000, 0, pid)    # query limited | terminate | synchronize
        if not h:
            raise OSError(f"OpenProcess({pid}) : erreur {ctypes.get_last_error()}")
        SUIVIS[pid] = h
    return pid


def vivant(pid):
    code = ctypes.c_uint32()
    h = SUIVIS.get(int(pid))
    if h is None:
        return pre.pid_vivant(pid)
    return bool(K32.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == 259


def termine(pid):
    """Tue UN processus du banc par son handle (pas l'arbre)."""
    K32.TerminateProcess(SUIVIS[int(pid)], 1)


def nettoie():
    for pid in list(SUIVIS):
        if vivant(pid):
            termine(pid)
    time.sleep(0.5)
    restants = [pid for pid in SUIVIS if vivant(pid)]
    return restants


def attend(condition, delai=10.0):
    fin = time.monotonic() + delai
    while time.monotonic() < fin:
        if condition():
            return True
        time.sleep(0.1)
    return condition()


def lit_pids(chemin, delai=15.0):
    """Entiers ecrits par un faux outil dans son fichier ; None si le fichier n'arrive pas."""
    if not attend(lambda: os.path.exists(chemin), delai):
        return None
    with open(chemin) as f:
        pids = [int(x) for x in f.read().split()]
    for p in pids:
        garde(p)
    return pids


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def outil(id, script="faux_outil.py", dans_job=True):
    return reg.Outil(id, id, id, reg.GROUPES[0], "i", "a", script, [], "", "j", dans_job=dans_job)


def prepare():
    RACINE.mkdir(parents=True, exist_ok=True)
    (RACINE / "faux_outil.py").write_text(FAUX_OUTIL, encoding="utf-8")
    (RACINE / "faux_parent.py").write_text(FAUX_PARENT, encoding="utf-8")
    (RACINE / "mini_annuaire.py").write_text(MINI_ANNUAIRE, encoding="utf-8")


# --- sections ---------------------------------------------------------------------------------------

def section_lance_et_console():
    print("== lance_et_console ==")
    lanceur = al.Lanceur(RACINE)
    faux = outil("faux")
    fichier = str(RACINE / "lance.pid")
    pid = garde(lanceur.lance(faux, [fichier, "250"], valeurs={"port": "COM9"}))
    reel = lit_pids(fichier)
    verifie(reel is not None, True, "lance_et_console : le faux outil a demarre")
    verifie(vivant(pid), True, "lance_et_console : PID rendu vivant")
    verifie(lanceur.lances.get("faux"), {"pid": pid, "valeurs": {"port": "COM9"}, "lie": False},
            "lances[id] = pid + valeurs, lie False")
    verifie(lanceur.derniers().get("faux"), {"port": "COM9"}, "lance(valeurs=...) memorise les derniers choix")
    attend(lambda: any("faux outil pret" in l for l in lanceur.console("faux")), 5)
    lignes = lanceur.console("faux")
    verifie(len(lignes), 200, "console : 200 dernieres lignes par defaut")
    pret = [l for l in lignes if "faux outil pret" in l]
    verifie(len(pret), 1, "lance_et_console : ligne du faux outil dans console(id)")
    ligne = pret[0] if pret else ""
    verifie("lance_par=annuaire" in ligne, True, "env : OUTILS_TASMOTA_LANCE_PAR=annuaire")
    verifie("utf8=1" in ligne, True, "env : PYTHONUTF8=1")
    verifie(f"cwd={RACINE}" in ligne, True, "cwd = racine")
    verifie(ligne.endswith(f"args={[fichier, '250', '--sans-navigateur']!r}"), True,
            "args puis --sans-navigateur")
    verifie(len(lanceur.console("faux", lignes=5)), 5, "console(id, lignes=5)")
    verifie(lanceur.console("inconnu"), [], "TEMOIN console : outil jamais lance -> []")
    verifie(lanceur.console("../derniers"), [], "console : id hors motif refuse")
    tete = (Path(DOSSIER) / "consoles" / "faux.log").read_text(encoding="utf-8").splitlines()[0]
    verifie(tete.startswith("[annuaire] lance "), True, "console : premiere ligne [annuaire] lance <date>")

    verifie(lanceur.arrete(faux, pid), True, "arrete d'un outil vivant -> True")
    verifie(attend(lambda: not vivant(pid) and not vivant(reel[0]), 5), True, "arrete : lanceur et python reel morts")
    verifie("faux" in lanceur.lances, False, "arrete : lances[id] retire")

    pid2 = garde(lanceur.lance(faux, [str(RACINE / "lance2.pid")]))
    lit_pids(str(RACINE / "lance2.pid"))
    attend(lambda: any("faux outil pret" in l for l in lanceur.console("faux")), 5)
    texte = (Path(DOSSIER) / "consoles" / "faux.log").read_text(encoding="utf-8")
    verifie((texte.count("[annuaire] lance "), texte.count("ligne 249")), (1, 0),
            "relance : console tronquee (une console par lancement)")
    verifie(lanceur.lances["faux"], {"pid": pid2, "valeurs": {}, "lie": False}, "lance sans valeurs : valeurs = {}")
    verifie(lanceur.arrete(faux, pid2), True, "relance : arrete -> True")
    verifie(lanceur.arrete(faux, pid2), True, "arrete d'un PID deja mort : True, sans exception")


def section_arrete_echoue():
    print("== arrete_echoue ==")
    lanceur = al.Lanceur(RACINE)
    faux = outil("faux_tenace")
    pid = garde(lanceur.lance(faux, [str(RACINE / "tenace.pid")]))
    reel = lit_pids(str(RACINE / "tenace.pid"))
    lanceur._tue_arbre = lambda p: None          # taskkill sans effet : le processus survit
    ancien_delai, al.DELAI_ARRET = al.DELAI_ARRET, 1.0
    try:
        verifie(lanceur.arrete(faux, pid), False, "arrete sans effet -> False")
        verifie(lanceur.lances.get("faux_tenace", {}).get("pid"), pid, "arrete sans effet : lances[id] garde")
        verifie(vivant(pid) and vivant(reel[0]), True, "arrete sans effet : l'outil vit encore")
    finally:
        al.DELAI_ARRET = ancien_delai
        del lanceur._tue_arbre
    verifie(lanceur.arrete(faux, pid), True, "TEMOIN vrai taskkill : arrete -> True")
    verifie("faux_tenace" in lanceur.lances, False, "TEMOIN vrai taskkill : lances[id] retire")
    verifie(attend(lambda: not vivant(reel[0]), 3), True, "TEMOIN vrai taskkill : python reel mort")


def section_arrete_arbre():
    print("== arrete_arbre ==")
    lanceur = al.Lanceur(RACINE)
    parent = outil("faux_parent", "faux_parent.py")

    # Temoin : tuer le seul python du parent laisse l'enfant vivre.
    lanceur.lance(parent, [str(RACINE / "temoin.pid")])
    pids = lit_pids(str(RACINE / "temoin.pid"))
    reel_enfant = lit_pids(str(RACINE / "temoin.pid.enfant"))
    termine(pids[0])
    attend(lambda: not vivant(pids[0]), 3)
    time.sleep(1.5)
    verifie((vivant(pids[0]), vivant(reel_enfant[0])), (False, True),
            "TEMOIN arrete_arbre : tuer le seul parent laisse l'enfant vivant")
    nettoie()

    pid = garde(lanceur.lance(parent, [str(RACINE / "arbre.pid")]))
    pids = lit_pids(str(RACINE / "arbre.pid"))           # python reel du parent, lanceur de l'enfant
    reel_enfant = lit_pids(str(RACINE / "arbre.pid.enfant"))
    tous = [pid] + pids + reel_enfant
    verifie(all(vivant(p) for p in tous), True, "arrete_arbre : 4 processus vivants (2 lanceurs, 2 python)")
    verifie(lanceur.arrete(parent, pid), True, "arrete_arbre : arrete -> True")
    verifie(attend(lambda: not any(vivant(p) for p in tous), 5), True, "arrete_arbre : les deux PID (et lanceurs) morts")


def mini_annuaire(mode, via_lanceur):
    """Lance le mini-annuaire ; rend (pid du processus lance, sortie, prefixe des fichiers de PID).

    via_lanceur : par le python.exe du penv (lanceur + python reel), sinon par le python de base.
    """
    prefixe = str(RACINE / f"mini_{mode}_{int(via_lanceur)}")
    sortie = prefixe + ".json"
    python = sys.executable if via_lanceur else getattr(sys, "_base_executable", sys.executable)
    p = subprocess.Popen([python, str(RACINE / "mini_annuaire.py"), ICI, str(RACINE), sys.executable, mode, sortie],
                         creationflags=CREATE_NO_WINDOW)
    garde(p.pid)
    if not attend(lambda: os.path.exists(sortie), 20):
        return p.pid, None, prefixe
    with open(sortie) as f:
        info = json.load(f)
    for cle in ("moi", "p_job", "p_hors"):
        if info.get(cle):
            garde(info[cle])
    return p.pid, info, prefixe


def taskkill_f(pid):
    subprocess.run(["taskkill", "/F", "/PID", str(pid)], creationflags=CREATE_NO_WINDOW,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def un_cas(mode, via_lanceur, libelle):
    """Mini-annuaire en mode donne, tue par taskkill /F ; rend (job mort sous 3 s, hors encore vivant)."""
    top, info, prefixe = mini_annuaire(mode, via_lanceur)
    if not verifie(info is not None, True, f"{libelle} : mini-annuaire demarre"):
        return None, None
    reel_job = lit_pids(prefixe + "_job.pid")
    reel_hors = lit_pids(prefixe + "_hors.pid")
    job = [info["p_job"], reel_job[0]]
    hors = [info["p_hors"], reel_hors[0]]
    verifie(all(vivant(p) for p in job + hors + [info["moi"]]), True, f"{libelle} : tout vit avant le kill")
    if mode == "job":
        verifie(info["ok"], True, f"{libelle} : rattache_au_job() -> True")
        console_hors = al.Lanceur(RACINE).console("faux_hors")
        verifie(any("synchro liee" in l for l in console_hors), False,
                f"{libelle} : breakaway accepte (pas de repli)")
        verifie(info["lie"], {"faux_job": False, "faux_hors": False}, f"{libelle} : breakaway accepte -> lie False")
    # Mini via le lanceur : on tue ce que voit VS Code (le lanceur, sans /T) ; sinon le python qui tient le job.
    taskkill_f(top if via_lanceur else info["moi"])
    job_mort = attend(lambda: not any(vivant(p) for p in job), 3)
    time.sleep(0.5)
    hors_vit = all(vivant(p) for p in hors)
    nettoie()
    return job_mort, hors_vit


def section_taskkill_annuaire():
    print("== taskkill_annuaire ==")
    job_mort, hors_vit = un_cas("job", False, "taskkill_annuaire")
    verifie(job_mort, True, "taskkill_annuaire : outil dans_job mort sous 3 s")
    verifie(hors_vit, True, "taskkill_annuaire : outil hors job (synchro) encore vivant")

    job_mort, hors_vit = un_cas("sans", False, "TEMOIN sans job")
    verifie(job_mort, False, "TEMOIN sans rattache_au_job() : l'outil dans_job survit")

    job_mort, hors_vit = un_cas("job", True, "via lanceur penv")
    verifie((job_mort, hors_vit), (True, True), "via lanceur penv (kill du lanceur seul) : dans_job mort, hors vit")


def section_breakaway_refuse():
    print("== breakaway_refuse ==")
    top, info, prefixe = mini_annuaire("refus", False)
    if not verifie(info is not None, True, "breakaway_refuse : mini-annuaire demarre"):
        return
    verifie(info["ok"], True, "breakaway_refuse : job sans breakaway pose")
    reel = lit_pids(prefixe + "_hors.pid")
    verifie(reel is not None and vivant(reel[0]), True, "breakaway_refuse : outil relance sans le drapeau")
    tete = (Path(DOSSIER) / "consoles" / "faux_hors.log").read_text(encoding="utf-8").splitlines()[:2]
    verifie(any(l.startswith("[annuaire] synchro liee a l'annuaire") for l in tete), True,
            "breakaway_refuse : '[annuaire] synchro liee a l'annuaire' en tete de console")
    verifie(info["lie"], {"faux_hors": True}, "breakaway_refuse : lances[id][\"lie\"] = True")
    with open(prefixe + "_hors.pid.console") as f:
        liste = [int(x) for x in f.read().split()]
    verifie(bool(liste) and info["moi"] not in liste, True, "breakaway_refuse : repli garde sa console a lui")
    taskkill_f(info["moi"])
    verifie(attend(lambda: not vivant(info["p_hors"]) and not vivant(reel[0]), 3), True,
            "breakaway_refuse : repli = outil lie a l'annuaire (meurt avec lui)")
    nettoie()


def consoles(mode):
    """Mini-annuaire (python de base) ; rend (pid du mini, PIDs console outil dans_job, outil hors job)."""
    top, info, prefixe = mini_annuaire(mode, False)
    if info is None:
        return None, None, None
    listes = []
    for nom in ("_job.pid", "_hors.pid"):
        lit_pids(prefixe + nom)
        with open(prefixe + nom + ".console") as f:
            listes.append([int(x) for x in f.read().split()])
    nettoie()
    return info["moi"], listes[0], listes[1]


def section_console_detachee():
    print("== console_detachee ==")
    moi, job, hors = consoles("job")
    verifie(moi in (job or []), True, "TEMOIN outil dans_job : partage la console du mini-annuaire")
    verifie(moi is not None and moi not in hors, True, "hors job : PID du mini-annuaire absent de sa console")
    verifie(bool(hors), True, "hors job : a une console a lui (cachee)")
    moi, job, hors = consoles("ancien")
    verifie(moi is not None and moi in hors, True,
            "TEMOIN anciens drapeaux (sans CREATE_NO_WINDOW) : console du mini-annuaire partagee")


def section_repli_seulement_erreur_5():
    """Popen remplace (aucun processus) : seul OSError winerror 5 declenche le relancement sans breakaway."""
    print("== repli_seulement_erreur_5 ==")
    appels = []

    class FauxProcessus:
        pid = 999999

    def popen_qui(erreur):
        def faux(*a, **kw):
            appels.append(kw.get("creationflags", 0))
            if erreur is not None and len(appels) == 1:
                raise erreur
            return FauxProcessus()
        return faux

    vrai = al.subprocess.Popen
    hors = outil("faux_repli", dans_job=False)
    try:
        al.subprocess.Popen = popen_qui(FileNotFoundError(2, "python introuvable"))
        lanceur = al.Lanceur(RACINE)
        try:
            lanceur.lance(hors, [])
            leve = None
        except OSError as e:
            leve = type(e).__name__
        verifie((leve, len(appels)), ("FileNotFoundError", 1), "FileNotFoundError : remonte, pas de relance")
        verifie("faux_repli" in lanceur.lances, False, "FileNotFoundError : rien dans lances")
        del appels[:]
        al.subprocess.Popen = popen_qui(OSError(None, "Acces refuse", None, 5))
        lanceur = al.Lanceur(RACINE)
        lanceur.lance(hors, [])
        verifie(len(appels), 2, "TEMOIN winerror 5 : relance une fois")
        verifie((bool(appels[0] & al.CREATE_BREAKAWAY_FROM_JOB), bool(appels[1] & al.CREATE_BREAKAWAY_FROM_JOB)),
                (True, False), "winerror 5 : relance sans CREATE_BREAKAWAY_FROM_JOB")
        verifie(lanceur.lances["faux_repli"]["lie"], True, "winerror 5 : lie True")
        del appels[:]
        al.subprocess.Popen = popen_qui(None)
        lanceur = al.Lanceur(RACINE)
        lanceur.lance(hors, [])
        verifie((len(appels), lanceur.lances["faux_repli"]["lie"]), (1, False), "TEMOIN sans erreur : un appel, lie False")
    finally:
        al.subprocess.Popen = vrai


def section_derniers():
    print("== derniers_memorises ==")
    al.Lanceur(RACINE).memorise("pont_serie", {"port": "COM3"})
    verifie(al.Lanceur(RACINE).derniers().get("pont_serie", {}).get("port"), "COM3", "derniers_memorises")
    al.Lanceur(RACINE).memorise("syslog", {"http": "7201"})
    d = al.Lanceur(RACINE).derniers()
    verifie((d["pont_serie"]["port"], d["syslog"]["http"]), ("COM3", "7201"), "memorise : les autres ids gardes")
    (Path(DOSSIER) / "derniers.json").write_text("{pas du json", encoding="utf-8")
    verifie(al.Lanceur(RACINE).derniers(), {}, "derniers.json illisible -> {}")


def principal():
    prepare()
    try:
        for section in (section_lance_et_console, section_arrete_echoue, section_arrete_arbre,
                        section_taskkill_annuaire, section_console_detachee, section_breakaway_refuse,
                        section_repli_seulement_erreur_5, section_derniers):
            try:
                section()
            except Exception as e:          # une section cassee ne doit pas empecher le nettoyage
                verifie(repr(e), "", f"{section.__name__} : exception")
            print()
    finally:
        restants = nettoie()
        verifie(restants, [], f"nettoyage : aucun processus de test restant ({len(SUIVIS)} suivis)")
        print("PID suivis :", sorted(SUIVIS))
        for h in SUIVIS.values():
            K32.CloseHandle(h)
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(principal())
