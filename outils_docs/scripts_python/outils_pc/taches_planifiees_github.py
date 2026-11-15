"""Voie GitHub de la page « Taches planifiees » : lecture par la CLI `gh` (LECTURE SEULE) et controle de sante du workflow Build_custom.

Constat du 2026-11-15 : GitHub desactive les workflows d'un fork inactif et l'endpoint `actions/permissions` repond quand meme
`enabled: true`. Trois controles donc : permissions, etat du workflow (`gh workflow list --all`), anciennete du dernier run PLANIFIE.
`gh` absent, non connecte ou hors ligne est un resultat (jamais une exception) : `sante()` rend toujours un dict.
Un seul point d'appel a gh (`gh`) : remplace par un faux dans le banc test_taches_planifiees_github.py.
"""

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

DEPOT = "fdaubercy/Tasmota"
WORKFLOW = "Build_custom"
SEUIL_PLANIFIE_H = 36
DELAI = 12


def gh(args, delai=DELAI):
    """Rend (code, sortie). 127 = gh absent, 124 = delai depasse."""
    try:
        r = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=delai,
                           stdin=subprocess.DEVNULL)
    except FileNotFoundError:
        return 127, "gh introuvable"
    except subprocess.TimeoutExpired:
        return 124, "delai depasse"
    except OSError as e:
        return 127, str(e)
    return r.returncode, (r.stdout or "") if r.returncode == 0 else (r.stderr or r.stdout or "")


def panne(code, sortie):
    """Phrase courte pour un echec de gh."""
    s = (sortie or "").lower()
    if code == 127:
        return "la CLI gh est absente de ce PC"
    if code == 124 or any(m in s for m in ("timeout", "dial tcp", "no such host", "could not resolve", "handshake", "connection", "network")):
        return "GitHub injoignable (hors ligne ou trop lent)"
    if any(m in s for m in ("auth login", "not logged", "authentication", "gh_token", "401", "bad credentials")):
        return "gh n'est pas connecte (gh auth login)"
    return "gh a echoue : " + (sortie or "").strip()[:160]


def _json(code, sortie):
    if code != 0:
        return None, panne(code, sortie)
    try:
        return json.loads(sortie), None
    except ValueError:
        return None, "reponse de gh illisible"


def _age_heures(iso, maintenant):
    try:
        t = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return round((maintenant - t).total_seconds() / 3600, 1)
    except (ValueError, TypeError):
        return None


def sante(executeur=gh, maintenant=None):
    """{ok, pannes, alertes, runs, echecs, workflow, permissions, age_planifie_h}. `alertes` = problemes prouves, `pannes` = non verifie."""
    maintenant = maintenant or datetime.now(timezone.utc)
    taches = {
        "runs": ["run", "list", "-R", DEPOT, "--workflow", WORKFLOW, "-L", "30", "--json", "databaseId,status,conclusion,event,createdAt,url"],
        "workflows": ["workflow", "list", "-R", DEPOT, "--all", "--json", "name,state"],
        "permissions": ["api", f"repos/{DEPOT}/actions/permissions"],
    }
    with ThreadPoolExecutor(3) as pool:
        futurs = {k: pool.submit(executeur, a) for k, a in taches.items()}
        brut = {k: _json(*f.result()) for k, f in futurs.items()}
    r = {"ok": True, "pannes": [], "alertes": [], "runs": [], "echecs": [], "workflow": None, "permissions": None, "age_planifie_h": None}
    for cle, (_, erreur) in brut.items():
        if erreur:
            r["pannes"].append(f"{cle} : {erreur}")
    if all(e for _, e in brut.values()):
        r["ok"] = False                                              # rien n'a pu etre lu
    perm, _ = brut["permissions"]
    if isinstance(perm, dict):
        r["permissions"] = perm.get("enabled")
        if perm.get("enabled") is False:
            r["alertes"].append("Les Actions sont desactivees sur le fork (reglages du depot).")
    wfs, _ = brut["workflows"]
    if isinstance(wfs, list):
        wf = next((w for w in wfs if isinstance(w, dict) and w.get("name") == WORKFLOW), None)
        if wf is None:
            r["pannes"].append(f"workflow {WORKFLOW} introuvable")
        else:
            r["workflow"] = wf.get("state")
            if wf.get("state") != "active":
                r["alertes"].append(f"Le workflow {WORKFLOW} est desactive par GitHub ({wf.get('state')}) : reactiver dans l'onglet Actions.")
    runs, _ = brut["runs"]
    if isinstance(runs, list):
        runs = [x for x in runs if isinstance(x, dict)]
        r["runs"] = [{k: x.get(k) for k in ("databaseId", "status", "conclusion", "event", "createdAt", "url")} for x in runs[:10]]
        plan = next((x for x in runs if x.get("event") == "schedule"), None)
        if plan is None:
            r["alertes"].append("Aucun run planifie (schedule) parmi les 30 derniers : le cron GitHub ne tourne pas.")
        else:
            r["age_planifie_h"] = _age_heures(plan.get("createdAt"), maintenant)
            if r["age_planifie_h"] is None or r["age_planifie_h"] > SEUIL_PLANIFIE_H:
                r["alertes"].append(f"Le dernier run planifie date de {r['age_planifie_h']} h (seuil {SEUIL_PLANIFIE_H} h).")
        if runs:
            r["echecs"] = jobs_en_echec(runs[0].get("databaseId"), executeur)
    return r


def jobs_en_echec(ident, executeur=gh):
    if not isinstance(ident, int):
        return []
    donnees, _ = _json(*executeur(["run", "view", str(ident), "-R", DEPOT, "--json", "jobs"]))
    jobs = donnees.get("jobs", []) if isinstance(donnees, dict) else []
    return [{"nom": str(j.get("name")), "url": j.get("url")} for j in jobs if isinstance(j, dict) and j.get("conclusion") == "failure"]
