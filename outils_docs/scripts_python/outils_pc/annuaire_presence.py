"""Etat des outils PC pour l'annuaire : fiches de presence, PID vivants, ports qui repondent.

Une fiche (acces_web.dossier_presence()/<port>.json) appartient a un Outil quand fiche["nom"] ==
outil.nom_acces. Une fiche au PID mort est supprimee (outil tue sans passer par atexit).
"""

import ctypes
import json
import os
import socket

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
        for autre_id, info in lances.items():
            if autre_id == outil.id or not pid_vivant(info.get("pid")):
                continue
            if any(str(x) == v for x in (info.get("valeurs") or {}).values()):
                return f"{v} tenu par {reg.par_id(autre_id).nom}"
    return ""


def etat_outils(lances, derniers, hote_client):
    """Une entree par outil du registre (voir la fiche de tache 3 pour le detail des champs)."""
    fiches = lit_fiches()
    resultat = []
    for o in reg.OUTILS:
        fiche = fiches.get(o.nom_acces)
        # Une fiche ne vaut "marche" que si son port repond aussi (PID reutilise, outil en demarrage) ;
        # sinon elle est ignoree ici, mais pas supprimee.
        if fiche and not port_repond(fiche["port"]):
            fiche = None
        e = {"id": o.id, "etat": "arrete", "raison": "", "port": 0, "debut": None, "lien": None,
             "peut_arreter": False, "lance_ailleurs": False, "console": o.id in lances}
        if fiche:
            port = fiche["port"]
            e.update(etat="marche", port=port, debut=fiche.get("debut"),
                     peut_arreter=fiche.get("lance_par") == "annuaire",
                     lance_ailleurs=fiche.get("lance_par") != "annuaire")
            if hote_client is None:
                e["lien"] = f"http://127.0.0.1:{port}/"
            elif fiche.get("jeton"):
                e["lien"] = f"http://{hote_client}:{port}/?jeton={fiche['jeton']}"
        else:
            valeurs = derniers.get(o.id, {})
            port = _port_attendu(o, valeurs)
            e["port"] = port
            if port_repond(port):
                e.update(etat="marche", raison="en marche (sans fiche)", lance_ailleurs=True,
                         lien=f"http://127.0.0.1:{port}/" if hote_client is None else None)
            else:
                raison = _com_tenu(o, valeurs, lances)
                if raison:
                    e.update(etat="bloque", raison=raison)
        resultat.append(e)
    return resultat
