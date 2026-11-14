"""Verrou de fichier de la page Build (plan build-reparations A2) : qui tient un fichier, et ne fermer que la liste blanche.

Repérage par le Restart Manager de Windows (RmStartSession, RmRegisterResources, RmGetList) ; nom et parent par Toolhelp32,
ligne de commande par NtQueryInformationProcess (les memes champs que Win32_Process, sans ses 15 a 25 s).
Jamais fermes : la page et ses descendants, la serie en cours et ses descendants, `claude*` (et un `node` lance par claude).
Un pio/scons/python/py d'une autre origine : on attend sa fin, on ne le ferme jamais. Seule la liste blanche est fermee ;
tout autre processus est rendu en `demande` (la page pose la question). Une fermeture qui echoue va dans `refuse`.
Spec : docs/superpowers/specs/2026-11-14-build-reparations-design.md.
"""

import ctypes
import os
import re
import time
from ctypes import wintypes

LISTE_BLANCHE = ("cpptools-srv.exe", "cpptools.exe")
ATTENTE_LIBRE_S = 5
_BUILD = re.compile(r"^(pio|platformio|scons|python[\d.]*w?|pyw?)(\.exe)?$", re.I)


class ErreurVerrou(RuntimeError):
    """Le Restart Manager n'a pas pu dire qui tient le fichier (a ne pas confondre avec « personne »)."""

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_H = wintypes.HANDLE
_k32.CreateFileW.restype = _H
_k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                             wintypes.DWORD, _H]
_k32.OpenProcess.restype = _H
_k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_k32.CloseHandle.argtypes = [_H]
_k32.TerminateProcess.argtypes = [_H, wintypes.UINT]
_k32.QueryFullProcessImageNameW.argtypes = [_H, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
_k32.CreateToolhelp32Snapshot.restype = _H
_k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
_k32.GetProcessTimes.argtypes = [_H] + [ctypes.POINTER(wintypes.FILETIME)] * 4
_INVALIDE = _H(-1).value


class _UNICODE(ctypes.Structure):
    _fields_ = [("Length", ctypes.c_ushort), ("MaximumLength", ctypes.c_ushort), ("Buffer", ctypes.c_void_p)]


class _UNIQUE(ctypes.Structure):
    _fields_ = [("dwProcessId", wintypes.DWORD), ("ProcessStartTime", wintypes.FILETIME)]


class _INFO(ctypes.Structure):
    _fields_ = [("Process", _UNIQUE), ("strAppName", wintypes.WCHAR * 256),
                ("strServiceShortName", wintypes.WCHAR * 64), ("ApplicationType", ctypes.c_int),
                ("AppStatus", wintypes.ULONG), ("TSSessionId", wintypes.DWORD), ("bRestartable", wintypes.BOOL)]


def _filetime(ft):
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime


def _pids_rm(chemin):
    """[(pid, heure de debut)] des processus qui tiennent `chemin`, selon le Restart Manager ; ErreurVerrou sinon."""
    rm = ctypes.WinDLL("rstrtmgr")
    session = wintypes.DWORD()
    cle = ctypes.create_unicode_buffer(33)
    err = rm.RmStartSession(ctypes.byref(session), 0, cle)
    if err:
        raise ErreurVerrou("RmStartSession : code %d" % err)
    try:
        fichiers = (wintypes.LPCWSTR * 1)(os.path.abspath(chemin))
        err = rm.RmRegisterResources(session, 1, fichiers, 0, None, 0, None)
        if err:
            raise ErreurVerrou("RmRegisterResources : code %d" % err)
        besoin, n, raison = wintypes.UINT(0), wintypes.UINT(0), wintypes.DWORD()
        for _ in range(5):  # la liste peut grandir entre deux appels (ERROR_MORE_DATA = 234)
            infos = (_INFO * max(besoin.value, 1))()
            n.value = len(infos)
            err = rm.RmGetList(session, ctypes.byref(besoin), ctypes.byref(n), infos, ctypes.byref(raison))
            if err == 0:
                return [(infos[i].Process.dwProcessId, _filetime(infos[i].Process.ProcessStartTime))
                        for i in range(n.value)]
            if err != 234:
                break
        raise ErreurVerrou("RmGetList : code %d" % err)
    finally:
        rm.RmEndSession(session)


class _ENTREE(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD),
                ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", wintypes.LONG), ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]


_k32.Process32FirstW.argtypes = _k32.Process32NextW.argtypes = [_H, ctypes.POINTER(_ENTREE)]
_nt = ctypes.WinDLL("ntdll")
_nt.NtQueryInformationProcess.argtypes = [_H, ctypes.c_int, ctypes.c_void_p, wintypes.ULONG,
                                          ctypes.POINTER(wintypes.ULONG)]


def _table_processus():
    """{pid: (ppid, nom)} de tous les processus, par un instantane Toolhelp32.

    Win32_Process (Get-CimInstance) donnerait la meme chose mais prend 15 a 25 s sur ce poste (mesure du 2026-11-14)."""
    snap = _k32.CreateToolhelp32Snapshot(2, 0)  # TH32CS_SNAPPROCESS
    if snap in (None, _INVALIDE):
        return {}
    table, e = {}, _ENTREE()
    e.dwSize = ctypes.sizeof(_ENTREE)
    try:
        ok = _k32.Process32FirstW(snap, ctypes.byref(e))
        while ok:
            table[e.th32ProcessID] = (e.th32ParentProcessID, e.szExeFile)
            ok = _k32.Process32NextW(snap, ctypes.byref(e))
    finally:
        _k32.CloseHandle(snap)
    return table


def _ligne_commande(pid):
    """Ligne de commande de `pid` (NtQueryInformationProcess, classe 60), "" si illisible."""
    h = _k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        taille = wintypes.ULONG(0)
        _nt.NtQueryInformationProcess(h, 60, None, 0, ctypes.byref(taille))
        if not taille.value:
            return ""
        tampon = ctypes.create_string_buffer(taille.value)
        if _nt.NtQueryInformationProcess(h, 60, tampon, taille, ctypes.byref(taille)):
            return ""
        chaine = _UNICODE.from_buffer(tampon)  # en tete du tampon ; Buffer pointe plus loin dans ce meme tampon
        return ctypes.wstring_at(chaine.Buffer, chaine.Length // 2) if chaine.Buffer else ""
    finally:
        _k32.CloseHandle(h)


def processus_du_fichier(chemin: str) -> list:
    """Processus qui tiennent `chemin` : [{"pid", "nom", "ligne", "ancetres"}] ; un processus deja mort est omis."""
    pids = _pids_rm(chemin)
    if not pids:
        return []
    table = _table_processus()
    rendu = []
    for pid, debut in pids:
        if pid not in table:
            continue
        ancetres, courant = [], table[pid][0]
        while courant in table and courant not in ancetres and len(ancetres) < 32:
            ancetres.append(courant)
            courant = table[courant][0]
        rendu.append({"pid": pid, "nom": table[pid][1], "ligne": _ligne_commande(pid), "debut": debut,
                      "ancetres": ancetres, "ancetres_noms": [table[a][1] for a in ancetres]})
    return rendu


def classe(proc, pid_serie, liste_blanche) -> str:
    """"jamais" (page, serie, claude), "attend" (autre build), "ferme" (liste blanche) ou "demande" (le reste)."""
    pid, nom = proc.get("pid"), (proc.get("nom") or "").lower()
    if pid == os.getpid() or os.getpid() in proc.get("ancetres", ()) or nom.startswith("claude"):
        return "jamais"
    sous_claude = any(a.lower().startswith("claude") for a in proc.get("ancetres_noms", ()))
    if nom in ("node", "node.exe") and sous_claude:
        return "jamais"
    if pid_serie is not None and (pid == pid_serie or pid_serie in proc.get("ancetres", ())):
        return "jamais"
    if _BUILD.match(nom):
        return "attend"
    if nom in {n.lower() for n in liste_blanche}:
        return "ferme"
    return "demande"


def est_libre(chemin) -> bool:
    """Vrai si `chemin` s'ouvre en partage exclusif (ou n'existe pas)."""
    if not os.path.exists(chemin):
        return True
    h = _k32.CreateFileW(os.path.abspath(chemin), 0x80000000, 0, None, 3, 0x80, None)
    if h in (None, _INVALIDE):
        return False
    _k32.CloseHandle(h)
    return True


def _termine(pid, nom, debut=None) -> bool:
    """Ferme `pid` s'il porte toujours le nom `nom` et, si `debut` est connu, la meme heure de debut (pid reutilise :
    on n'y touche pas). Vrai seulement si TerminateProcess a reussi ; faux si absent, acces refuse ou autre processus."""
    h = _k32.OpenProcess(0x1001, False, pid)  # PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False  # deja mort ou acces refuse
    try:
        tampon, taille = ctypes.create_unicode_buffer(1024), wintypes.DWORD(1024)
        if not _k32.QueryFullProcessImageNameW(h, 0, tampon, ctypes.byref(taille)):
            return False
        if os.path.basename(tampon.value).lower() != (nom or "").lower():
            return False
        if debut:
            t = [wintypes.FILETIME() for _ in range(4)]
            if not _k32.GetProcessTimes(h, *[ctypes.byref(x) for x in t]) or _filetime(t[0]) != debut:
                return False
        return bool(_k32.TerminateProcess(h, 1))
    finally:
        _k32.CloseHandle(h)


def libere(chemin, liste_blanche, pid_serie, demande, *, processus_du_fichier=processus_du_fichier, terminer=None):
    """Ferme les processus de la liste blanche qui tiennent `chemin` (et ceux que `demande(proc)` accepte), attend
    jusqu'a 5 s que le fichier soit libre. Rend {"libre", "ferme", "attend", "demande", "refuse"} (fermeture echouee),
    plus "erreur" si le Restart Manager n'a pas repondu ; "jamais" n'est pas rendu."""
    rendu = {"libre": False, "ferme": [], "attend": [], "demande": [], "refuse": []}
    try:
        procs = processus_du_fichier(chemin)
    except ErreurVerrou as e:
        rendu["erreur"] = str(e)
        return rendu
    for p in procs:
        c = classe(p, pid_serie, liste_blanche)
        if c == "demande" and demande is not None and demande(p):
            c = "ferme"
        if c == "ferme":
            try:
                ok = terminer(p["pid"]) if terminer else _termine(p["pid"], p.get("nom"), p.get("debut"))
            except OSError:
                ok = False  # mort entre le reperage et la fermeture
            c = "ferme" if ok else "refuse"
        if c != "jamais":
            rendu[c].append(p)
    fin = time.monotonic() + (ATTENTE_LIBRE_S if rendu["ferme"] else 0)
    while True:
        rendu["libre"] = est_libre(chemin)
        if rendu["libre"] or time.monotonic() >= fin:
            return rendu
        time.sleep(0.1)
