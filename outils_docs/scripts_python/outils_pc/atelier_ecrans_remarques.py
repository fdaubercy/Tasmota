"""Remarques de l'atelier des ecrans et leur traitement par Claude (plan atelier-ecrans A7, spec § 5.7).

`outils_docs/atelier_ecrans/cartes/<env>/remarques.json` : liste de remarques
    {"id", "cible": {"page": n} | {"page": n, "objet": id} | {"page": n, "zone": [x, y, l, h]}, "texte", "date",
     "etat": "ouverte" | "proposee" | "appliquee" | "refusee", "proposition"?: {"texte", "operations", "date"},
     "reponses": [{"date", "texte"}]}
La cible porte toujours la page : les id d'objets se repetent d'une page a l'autre.

Traitement : `claude -p` lance dans le depot en LECTURE SEULE (options verifiees le 2026-11-12 avec claude 2.1.319 :
--tools Read,Grep,Glob, --permission-mode dontAsk, --strict-mcp-config ; une demande d'ecrire un fichier temoin a
echoue faute d'outil) et SANS hooks de l'utilisateur (--settings avec disableAllHooks : un hook SessionStart temoin
ecrit son fichier sans ce reglage, plus avec). La consigne passe par l'entree standard (claude.CMD : pas de texte libre dans la ligne de
commande de cmd.exe). Claude rend ses propositions sur la sortie ; c'est CE module qui les valide et les ecrit dans
remarques.json. Controle en plus : aucun fichier du depot ne doit changer pendant le traitement (git status et
empreintes, remarques.json de la carte excepte), sinon le resultat est rejete.
shortcut: les fichiers ignores par git ne sont pas controles ; la lecture seule repose sur les options de claude.
"""
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

import acces_web
import atelier_ecrans_catalogue as cat
import atelier_ecrans_description as aed

DELAI = 600                     # 10 min au plus pour un traitement
VERROU = threading.RLock()      # lectures et ecritures de remarques.json (requetes HTTP et fil du traitement)
TEXTE_MAX = 2000
SKILL = Path.home() / ".claude" / "skills" / "lvgl-haspmota"
OPTIONS = ["-p", "--tools", "Read,Grep,Glob", "--permission-mode", "dontAsk", "--strict-mcp-config",
           "--no-session-persistence", "--disable-slash-commands", "--output-format", "json"]


def maintenant():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _entier(v):
    return isinstance(v, int) and not isinstance(v, bool)


# ---------- fichier des remarques ----------

def chemin(racine, env):
    return Path(racine) / aed.DOSSIER / env / "remarques.json"


def charge(racine, env):
    try:
        with VERROU:
            d = json.loads(chemin(racine, env).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    if not isinstance(d, list) or not all(isinstance(r, dict) for r in d):
        raise ValueError("remarques.json : liste de remarques attendue")
    return d


def enregistre(racine, env, remarques):
    p = chemin(racine, env)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    with VERROU:
        tmp.write_text(json.dumps(remarques, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        for essai in range(10):                  # Windows : remplacement refuse tant qu'un autre processus lit le fichier
            try:
                os.replace(tmp, p)
                return
            except PermissionError:
                if essai == 9:
                    raise
                time.sleep(0.1)


def _objet(desc, page, id_):
    return next((o for o in desc.get("objets", []) if o.get("page") == page and o.get("id") == id_), None)


def _texte(v):
    if not isinstance(v, str) or not v.strip():
        raise ValueError("texte de la remarque vide")
    if len(v) > TEXTE_MAX:
        raise ValueError(f"texte trop long ({len(v)} caracteres, {TEXTE_MAX} au plus)")
    return v.strip()


def _cible(c, desc):
    if not isinstance(c, dict) or not _entier(c.get("page")):
        raise ValueError("cible : page attendue")
    page = c["page"]
    if not any(p.get("n") == page for p in desc.get("pages", [])):
        raise ValueError(f"cible : page {page} inconnue")
    if "objet" in c:
        if not _entier(c["objet"]) or _objet(desc, page, c["objet"]) is None:
            raise ValueError(f"cible : objet {c.get('objet')!r} absent de la page {page}")
        return {"page": page, "objet": c["objet"]}
    if "zone" in c:
        z = c["zone"]
        if not (isinstance(z, list) and len(z) == 4 and all(_entier(v) and v >= 0 for v in z) and z[2] > 0 and z[3] > 0):
            raise ValueError("cible : zone [x, y, l, h] d'entiers positifs attendue")
        return {"page": page, "zone": z}
    return {"page": page}


def _remarque(remarques, id_):
    r = next((r for r in remarques if r.get("id") == id_), None)
    if r is None:
        raise ValueError(f"remarque {id_!r} inconnue")
    return r


def agit(racine, env, demande):
    """Epingler, repondre, refuser (POST /remarques). Rend la liste a jour, ecrite."""
    with VERROU:
        return _agit(racine, env, demande)


def _agit(racine, env, demande):
    remarques, action = charge(racine, env), demande.get("action")
    if action == "epingle":
        desc = demande.get("description")
        desc = desc if isinstance(desc, dict) else (aed.charge(racine, env) or {})
        remarques.append({"id": max([r.get("id", 0) for r in remarques if _entier(r.get("id"))] or [0]) + 1,
                          "cible": _cible(demande.get("cible"), desc), "texte": _texte(demande.get("texte")),
                          "date": maintenant(), "etat": "ouverte", "reponses": []})
    elif action == "repond":
        r = _remarque(remarques, demande.get("id"))
        r.setdefault("reponses", []).append({"date": maintenant(), "texte": _texte(demande.get("texte"))})
        r["etat"] = "ouverte"                  # la reponse relance le traitement de la remarque
    elif action == "refuse":
        _remarque(remarques, demande.get("id"))["etat"] = "refusee"
    else:
        raise ValueError(f"action inconnue : {action!r}")
    enregistre(racine, env, remarques)
    return remarques


# ---------- propositions ----------

def _erreurs(desc, catalogue):
    try:
        return aed.valide(desc, catalogue)
    except (AttributeError, TypeError, KeyError, ValueError) as e:
        return [f"description mal formee : {type(e).__name__} : {e}"]


def applique(desc, proposition, catalogue=None):
    """Nouvelle description, operations de la proposition jouees sur une copie (rien n'est ecrit)."""
    d = copy.deepcopy(desc)
    ops = proposition.get("operations") if isinstance(proposition, dict) else None
    if not isinstance(ops, list):
        raise ValueError("operations : liste attendue")
    for n, op in enumerate(ops, 1):
        if not isinstance(op, dict):
            raise ValueError(f"operation {n} : objet attendu")
        genre = op.get("op")
        if genre == "ajoute":
            o = op.get("objet")
            if not isinstance(o, dict) or not _entier(o.get("page")) or not _entier(o.get("id")):
                raise ValueError(f"operation {n} : objet complet (page, id...) attendu")
            if _objet(d, o["page"], o["id"]) is not None:
                raise ValueError(f"operation {n} : id {o['id']} deja pris sur la page {o['page']}")
            d.setdefault("objets", []).append(copy.deepcopy(o))
        elif genre in ("modifie", "retire"):
            o = _objet(d, op.get("page"), op.get("id"))
            if o is None:
                raise ValueError(f"operation {n} : objet {op.get('id')!r} de la page {op.get('page')!r} inconnu")
            if genre == "retire":
                d["objets"].remove(o)
                continue
            attrs = op.get("attributs", {})
            if not isinstance(attrs, dict):
                raise ValueError(f"operation {n} : attributs : objet attendu")
            for k, v in attrs.items():
                if catalogue is not None and not cat.attribut_connu(catalogue, o.get("type"), k):
                    raise ValueError(f"operation {n} : attribut « {k} » hors catalogue pour {o.get('type')}")
                if v is None:
                    o.setdefault("attributs", {}).pop(k, None)
                else:
                    o.setdefault("attributs", {})[k] = v
            for k in ("x", "y", "l", "h"):
                if k in op:
                    if not _entier(op[k]) or op[k] < 0:
                        raise ValueError(f"operation {n} : {k} entier positif attendu")
                    o[k] = op[k]
        else:
            raise ValueError(f"operation {n} : « op » inconnue : {genre!r}")
    return d


def _json_de(texte):
    """Objet JSON d'un texte : tel quel, dans un bloc ```json, ou du premier { au dernier }."""
    if isinstance(texte, dict):
        return texte
    texte = str(texte or "").strip()
    essais = [texte]
    m = re.search(r"```(?:json)?\s*(.*?)```", texte, re.S)
    if m:
        essais.append(m.group(1))
    if "{" in texte:
        essais.append(texte[texte.index("{"):texte.rindex("}") + 1])
    for e in essais:
        try:
            return json.loads(e)
        except ValueError:
            pass
    raise ValueError("aucun JSON lisible dans la reponse de Claude")


def valide_propositions(sortie, desc, catalogue, remarques):
    """(propositions retenues, erreurs) : remarque ouverte, operations applicables, description toujours valide."""
    try:
        d = _json_de(sortie)
    except ValueError as e:
        return [], [str(e)]
    props = d.get("propositions") if isinstance(d, dict) else None
    if not isinstance(props, list):
        return [], ["« propositions » : liste attendue"]
    ouvertes = {r.get("id") for r in remarques if r.get("etat") == "ouverte"}
    deja, bonnes, erreurs = set(_erreurs(desc, catalogue)), [], []
    for i, p in enumerate(props, 1):
        rid = p.get("remarque") if isinstance(p, dict) else None
        qui = f"proposition {i} (remarque {rid!r})"
        if not _entier(rid) or rid not in ouvertes:
            erreurs.append(f"{qui} : remarque absente ou pas ouverte")
            continue
        if not isinstance(p.get("texte"), str) or not isinstance(p.get("operations", []), list):
            erreurs.append(f"{qui} : « texte » et « operations » attendus")
            continue
        try:
            nouvelle = applique(desc, {"operations": p.get("operations", [])}, catalogue)
        except ValueError as e:
            erreurs.append(f"{qui} : {e}")
            continue
        neuves = [m for m in _erreurs(nouvelle, catalogue) if m not in deja]
        if neuves:
            erreurs.append(f"{qui} : description refusee : " + " ; ".join(neuves[:3]))
            continue
        bonnes.append({"remarque": rid, "texte": p["texte"][:TEXTE_MAX], "operations": p.get("operations", [])})
    return bonnes, erreurs


def applique_remarque(racine, env, id_, desc):
    """POST /remarques/appliquer : description modifiee (rien n'est ecrit hors de l'etat de la remarque)."""
    if not isinstance(desc, dict):
        raise ValueError("description : objet attendu")
    with VERROU:
        return _applique_remarque(racine, env, id_, desc)


def _applique_remarque(racine, env, id_, desc):
    remarques = charge(racine, env)
    r = _remarque(remarques, id_)
    if r.get("etat") != "proposee" or not isinstance(r.get("proposition"), dict):
        raise ValueError(f"remarque {id_} : aucune proposition a appliquer")
    catalogue = cat.charge(racine)
    nouvelle = applique(desc, r["proposition"], catalogue)
    neuves = [m for m in _erreurs(nouvelle, catalogue) if m not in set(_erreurs(desc, catalogue))]
    if neuves:
        return {"description": None, "erreurs": neuves, "remarques": remarques}
    r["etat"] = "appliquee"
    enregistre(racine, env, remarques)
    return {"description": nouvelle, "erreurs": [], "remarques": remarques}


# ---------- traitement par claude -p ----------

def etat_depot(racine, ignore=()):
    """{chemin: empreinte ou None} des fichiers que git voit modifies ou nouveaux (hors `ignore`)."""
    r = subprocess.run(["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=racine,
                       capture_output=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError("controle du depot impossible (git status) : " + r.stderr.decode("utf-8", "replace")[-300:])
    morceaux, etat, i = r.stdout.split(b"\0"), {}, 0
    while i < len(morceaux):
        e = morceaux[i]
        i += 1
        if len(e) < 4:
            continue
        if e[:1] in (b"R", b"C"):
            i += 1                                  # renommage : le chemin d'origine suit
        rel = e[3:].decode("utf-8", "replace")
        if rel in ignore:
            continue
        p = Path(racine) / rel
        etat[rel] = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    return etat


def consigne(env, ouvertes):
    skill = f"- consignes de la skill lvgl-haspmota : {SKILL / 'SKILL.md'} (et ses references si utile) ;\n" if SKILL.is_dir() else ""
    return (
        "Atelier des ecrans : session lancee par la page, en LECTURE SEULE (tu ne peux que lire).\n"
        f"Ecran de la carte {env}. Fichiers, relatifs au depot :\n{skill}"
        f"- description de l'ecran : {aed.DOSSIER}/{env}/ecran.json ;\n"
        f"- catalogue du firmware (objets, attributs, polices et tailles) : {cat.CATALOGUE} ;\n"
        f"- remarques : {aed.DOSSIER}/{env}/remarques.json ; ne traite que les remarques ouvertes : {ouvertes}.\n"
        "Pour chaque remarque ouverte, propose des modifications de la description. Reponds UNIQUEMENT par un objet "
        "JSON, sans texte autour :\n"
        '{"propositions": [{"remarque": <id>, "texte": "<explication courte en francais>", "operations": [...]}]}\n'
        'Operations : {"op": "modifie", "page": n, "id": i, "attributs": {...}, "x"?, "y"?, "l"?, "h"?} (attribut a '
        'null = retire) ; {"op": "ajoute", "objet": {objet complet au format de ecran.json}} ; '
        '{"op": "retire", "page": n, "id": i}.\n'
        "Les id d'objets se repetent d'une page a l'autre : toujours donner la page. N'utilise que des attributs, "
        "polices et tailles du catalogue. Remarque sans modification possible : \"operations\": [] et la raison dans "
        "\"texte\".\n")


def _resultat(stdout):
    """Texte de la reponse dans la sortie --output-format json de claude."""
    try:
        d = json.loads(stdout.decode("utf-8", "replace"))
    except ValueError:
        raise ValueError("sortie de claude illisible (JSON attendu)")
    if not isinstance(d, dict):
        raise ValueError("sortie de claude inattendue")
    if d.get("is_error"):
        raise ValueError("claude a rendu une erreur : " + str(d.get("result") or d.get("subtype"))[:300])
    return d.get("structured_output") or d.get("result") or ""


def reglages_sans_hooks():
    """Fichier --settings de la session : aucun hook de l'utilisateur (reprise apres limite, mods, SessionStart)."""
    d = acces_web.dossier_donnees() / "atelier_ecrans"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "reglages_claude.json"
    f.write_text('{"disableAllHooks": true}\n', encoding="utf-8")
    return f


def _arrete(p):
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
    else:
        p.kill()


class Traitement:
    """Un seul traitement a la fois, dans un fil ; etat lu par GET /remarques/etat."""

    def __init__(self, racine, programme=None, delai=DELAI):
        self.racine, self.programme, self.delai = Path(racine), programme, delai
        self._verrou = threading.Lock()
        self._etat = {"etat": "libre", "env": "", "debut": None, "fin": None, "message": ""}

    def etat(self):
        with self._verrou:
            return dict(self._etat)

    def lance(self, env):
        with self._verrou:
            if self._etat["etat"] == "en_cours":
                raise RuntimeError(f"un traitement est deja en cours ({self._etat['env']})")
            self._etat = {"etat": "en_cours", "env": env, "debut": time.time(), "fin": None, "message": "Claude lit les remarques…"}
        threading.Thread(target=self._travaille, args=(env,), daemon=True).start()

    def _travaille(self, env):
        try:
            etat, message = self._traite(env)
        except Exception as e:                       # le fil ne doit jamais laisser l'etat « en_cours »
            etat, message = "echec", f"erreur inattendue : {type(e).__name__} : {e}"
        with self._verrou:
            self._etat.update(etat=etat, message=message, fin=time.time())
        self._journal(env, f"{etat} : {message}")

    def _journal(self, env, ligne, sortie=None):
        try:
            d = acces_web.dossier_donnees() / "atelier_ecrans"
            d.mkdir(parents=True, exist_ok=True)
            with open(d / "traitements.log", "a", encoding="utf-8") as f:
                f.write(f"{maintenant()} {env} {ligne}\n")
            if sortie is not None:
                (d / f"{time.strftime('%Y%m%d-%H%M%S')}_{env}.txt").write_bytes(sortie)
        except OSError:
            pass

    def _traite(self, env):
        remarques = charge(self.racine, env)
        ouvertes = [r["id"] for r in remarques if r.get("etat") == "ouverte"]
        if not ouvertes:
            return "echec", "aucune remarque ouverte a traiter"
        desc = aed.charge(self.racine, env)
        if desc is None:
            return "echec", "pas encore de description ecrite pour cette carte (ecran.json) : l'ecrire d'abord"
        programme = self.programme or ([shutil.which("claude")] if shutil.which("claude") else None)
        if not programme:
            return "echec", "claude introuvable dans le PATH"
        ignore = {chemin(self.racine, env).relative_to(self.racine).as_posix()}
        avant = etat_depot(self.racine, ignore)
        options = OPTIONS + ["--settings", str(reglages_sans_hooks())] + (["--add-dir", str(SKILL)] if SKILL.is_dir() else [])
        try:
            p = subprocess.Popen(list(programme) + options, cwd=self.racine, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as e:
            return "echec", f"lancement de claude impossible : {e}"
        try:
            sortie, erreur = p.communicate(consigne(env, ouvertes).encode("utf-8"), timeout=self.delai)
        except subprocess.TimeoutExpired:
            _arrete(p)
            try:
                p.communicate(timeout=10)
            except subprocess.TimeoutExpired:     # un petit-fils garde les tubes : ne pas bloquer l'etat
                pass
            return "echec", f"delai de {self.delai} s depasse : traitement abandonne"
        self._journal(env, f"claude fini, code {p.returncode}", sortie + b"\n--- erreurs ---\n" + erreur)
        apres = etat_depot(self.racine, ignore)
        changes = sorted(k for k in set(avant) | set(apres) if avant.get(k) != apres.get(k))
        if changes:
            return "echec", ("resultat rejete : des fichiers du depot ont change pendant le traitement ("
                             + ", ".join(changes[:5]) + ") ; si une autre conversation travaillait, relancer")
        if p.returncode != 0:
            return "echec", f"claude a echoue (code {p.returncode}) : " + erreur.decode("utf-8", "replace")[-300:]
        try:
            texte = _resultat(sortie)
        except ValueError as e:
            return "echec", str(e)
        props, erreurs = valide_propositions(texte, desc, cat.charge(self.racine), remarques)
        with VERROU:
            return self._ecrit(env, props, erreurs)

    def _ecrit(self, env, props, erreurs):
        actuelles, n = charge(self.racine, env), 0     # relues : la page a pu epingler pendant le traitement
        for prop in props:
            r = next((r for r in actuelles if r.get("id") == prop["remarque"] and r.get("etat") == "ouverte"), None)
            if r is not None:
                r["etat"] = "proposee"
                r["proposition"] = {"texte": prop["texte"], "operations": prop["operations"], "date": maintenant()}
                n += 1
        if n:
            enregistre(self.racine, env, actuelles)
        message = f"{n} proposition(s) recue(s)" + (f", {len(erreurs)} rejetee(s) : " + " ; ".join(erreurs[:3]) if erreurs else "")
        return ("fini" if n or not erreurs else "echec"), message
