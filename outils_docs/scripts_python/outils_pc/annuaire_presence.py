"""Etat des outils PC pour l'annuaire : fiches de presence, PID vivants, ports qui repondent.

Une fiche (acces_web.dossier_presence()/<port>.json) appartient a un Outil quand fiche["nom"] ==
outil.nom_acces. Une fiche au PID mort est supprimee (outil tue sans passer par atexit).
"""

import ctypes
import json
import os
import socket
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import acces_web
import annuaire_registre as reg

STILL_ACTIVE = 259
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def pid_vivant(pid):
    """True si le processus existe et n'est pas termine (Windows : OpenProcess + GetExitCodeProcess)."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    k32 = ctypes.windll.kernel32
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid)
    if not h:
        return False
    try:
        code = ctypes.c_uint32()
        if not k32.GetExitCodeProcess(ctypes.c_void_p(h), ctypes.byref(code)):
            return False
        return code.value == STILL_ACTIVE
    finally:
        k32.CloseHandle(h)


def _heure_creation(pid):
    """Heure locale de creation du processus (GetProcessTimes), ou None."""
    k32 = ctypes.windll.kernel32
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    k32.GetProcessTimes.argtypes = [ctypes.c_void_p] + [ctypes.POINTER(ctypes.c_uint64)] * 4
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, int(pid))
    if not h:
        return None
    try:
        t = [ctypes.c_uint64() for _ in range(4)]
        if not k32.GetProcessTimes(ctypes.c_void_p(h), *[ctypes.pointer(x) for x in t]):
            return None
        return datetime.fromtimestamp((t[0].value - 116444736000000000) / 1e7)
    except (OverflowError, OSError, ValueError):
        return None
    finally:
        k32.CloseHandle(h)


def fiche_vivante(fiche):
    """True si le PID de la fiche vit ET que ce processus existait deja a l'ecriture de la fiche.

    La fiche est ecrite apres le bind : processus cree <= fiche["debut"] + 2 s. Un PID reutilise par un
    processus ne date d'apres la fiche n'est pas le notre. Vivante implique que le port est ouvert.
    """
    try:
        if not pid_vivant(fiche["pid"]):
            return False
        debut = datetime.strptime(fiche["debut"], "%Y-%m-%dT%H:%M:%S")
        cree = _heure_creation(fiche["pid"])
    except (KeyError, TypeError, ValueError):
        return False
    return cree is not None and cree <= debut + timedelta(seconds=2)


def port_repond(port, delai=0.3):
    """True si 127.0.0.1:port accepte une connexion TCP."""
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=delai):
            return True
    except (OSError, ValueError, TypeError):
        return False


def lit_fiches():
    """Fiches valides et vivantes, par nom ; supprime celles dont le PID est mort."""
    fiches = {}
    dossier = acces_web.dossier_presence()
    for chemin in sorted(dossier.glob("*.json")):
        try:
            with open(chemin, encoding="utf-8") as f:
                fiche = json.load(f)
            nom, port, pid = fiche["nom"], int(fiche["port"]), int(fiche["pid"])
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if not isinstance(nom, str):
            continue
        if not pid_vivant(pid):
            try:
                os.remove(chemin)
            except OSError:
                pass
            continue
        fiche["port"] = port
        fiches.setdefault(nom, fiche)
    return fiches


def _port_attendu(outil, valeurs):
    try:
        return outil.port_page(valeurs or {})
    except (ValueError, TypeError, KeyError):
        return outil.port_page({})


def _com_tenu(outil, derniers, lances):
    """Raison si un port COM des derniers choix est tenu par un autre outil lance en marche, sinon ''."""
    for p in outil.parametres:
        if p.genre not in ("com", "com_ou_pont"):
            continue
        v = str(derniers.get(p.cle, ""))
        if not v.upper().startswith("COM"):
            continue
        for autre_id, info in list(lances.items()):     # copie : un POST concurrent modifie lances
            if autre_id == outil.id or not pid_vivant(info.get("pid")):
                continue
            if any(str(x) == v for x in (info.get("valeurs") or {}).values()):
                return f"{v} tenu par {reg.par_id(autre_id).nom}"
    return ""


def etat_outils(lances, derniers, hote_client):
    """Une entree par outil du registre (voir la fiche de tache 3 pour le detail des champs).

    peut_arreter : fiche lance_par annuaire, OU outil lance ici (lances) dont le PID vit encore - meme sans
    fiche (demarrage, outil bloque avant son bind). lie : lances[id]["lie"] (breakaway refuse, l'outil hors
    job s'arretera avec l'annuaire) et PID vivant.
    """
    fiches = lit_fiches()
    vivantes = {o.id: fiches.get(o.nom_acces) for o in reg.OUTILS}
    vivantes = {i: f for i, f in vivantes.items() if f and fiche_vivante(f)}
    # Sans fiche vivante : port attendu sonde, en parallele (au plus un delai pour tout l'etat).
    attendus = {o.id: _port_attendu(o, derniers.get(o.id, {})) for o in reg.OUTILS if o.id not in vivantes}
    with ThreadPoolExecutor(max_workers=max(1, len(attendus))) as pool:
        sondes = dict(zip(attendus, pool.map(port_repond, attendus.values())))
    resultat = []
    for o in reg.OUTILS:
        fiche = vivantes.get(o.id)
        connu = lances.get(o.id) or {}
        lance_ici = bool(connu) and pid_vivant(connu.get("pid"))
        e = {"id": o.id, "etat": "arrete", "raison": "", "port": 0, "debut": None, "lien": None,
             "peut_arreter": lance_ici, "lance_ailleurs": False, "console": o.id in lances,
             "lie": lance_ici and bool(connu.get("lie"))}
        if fiche:
            port = fiche["port"]
            e.update(etat="marche", port=port, debut=fiche.get("debut"),
                     peut_arreter=fiche.get("lance_par") == "annuaire" or lance_ici,
                     lance_ailleurs=fiche.get("lance_par") != "annuaire" and not lance_ici)
            if hote_client is None:
                e["lien"] = f"http://127.0.0.1:{port}/"
            elif fiche.get("jeton"):
                e["lien"] = f"http://{hote_client}:{port}/?jeton={fiche['jeton']}"
        else:
            valeurs = derniers.get(o.id, {})
            e["port"] = attendus[o.id]
            if sondes[o.id]:
                e.update(etat="marche", raison="en marche (sans fiche)", lance_ailleurs=not lance_ici,
                         lien=f"http://127.0.0.1:{attendus[o.id]}/" if hote_client is None else None)
            elif lance_ici:
                e.update(raison="lancé d'ici, page pas encore prête (démarrage ou outil bloqué)")
            else:
                raison = _com_tenu(o, valeurs, lances)
                if raison:
                    e.update(etat="bloque", raison=raison)
        resultat.append(e)
    return resultat
