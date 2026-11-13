"""Assistant IA facultatif de l'atelier des visuels (plan atelier-visuels A9, spec § 2.10) : fournisseurs, envoi, quota.

Trois fournisseurs : `claude_local` (`claude -p` en lecture seule, options reprises de `atelier_ecrans_remarques`), `ollama`
(modele local, rien ne sort du PC), `api_externe` (API compatible « chat completions » : url, modele et cle de l'utilisateur).
Garde-fous de `demande` : un fournisseur EXTERNE n'est appele qu'avec `confirme` vrai (la photo part alors chez un tiers, meme
via l'abonnement Claude) ; la photo n'existe que dans un dossier temporaire hors depot, supprime apres ; le SVG rendu passe
par `atelier_visuels_fond.nettoie_svg` ; une reponse « trop de requetes » passe le quota a rouge et n'est JAMAIS retentee ;
la cle n'apparait ni dans les erreurs ni dans le journal (`ia.log`, a cote de la config).
Compteurs : `quota.json` a cote de la config. shortcut: un « rouge » dure jusqu'a minuit (jour local), meme si une heure de
reprise est notee ; l'utilisateur releve le plafond ou attend, a ameliorer si la reprise exacte est fiable.
"""
import base64
import datetime
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import atelier_ecrans_remarques as ear
import atelier_visuels_fond as avf
import atelier_visuels_ia_config as cfg

CONSIGNE_MAX = 2000
IMAGE_MAX = 10 * 1024 * 1024
DELAI = 600
VERROU = threading.Lock()
LIMITE = re.compile(r"rate.?limit|usage limit|limit reached|too many requests", re.I)
REPRISE = re.compile(r"(?:resets?|retry|try again)(?: after| at| in)?[ :]+([^.\n\"]{2,40})", re.I)
FORMATS = ((b"\x89PNG", "png", "image/png"), (b"\xff\xd8\xff", "jpg", "image/jpeg"), (b"RIFF", "webp", "image/webp"))
CADRE = ("Reponds UNIQUEMENT par un document SVG (xmlns SVG, viewBox, formes a plat : rect, path, polygon, circle, ellipse, "
         "g ; ni script, ni image, ni texte, ni style) qui redessine l'image, ou par un JSON "
         '{"operations": [...]} si la consigne demande de modifier des formes existantes.')


class LimiteAtteinte(Exception):
    """Le service refuse parce que trop de requetes ont ete faites ; `reprise` = heure ou delai si le service le dit."""

    def __init__(self, reprise=None):
        super().__init__("limite atteinte")
        self.reprise = reprise


def _reprise(texte):
    m = REPRISE.search(texte or "")
    return m.group(1).strip() if m else None


def _post(url, corps, entetes, delai):
    req = urllib.request.Request(url, json.dumps(corps).encode("utf-8"), {"Content-Type": "application/json", **entetes})
    try:
        with urllib.request.urlopen(req, timeout=delai) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:          # le corps n'est pas relu : il pourrait citer la cle
        if e.code == 429:
            attente = e.headers.get("Retry-After")
            raise LimiteAtteinte(f"dans {attente} s" if attente else None) from None
        raise RuntimeError(f"le service a repondu HTTP {e.code}") from None
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise RuntimeError(f"connexion ou reponse impossible ({type(e).__name__})") from None


def _image(chemin):
    octets = Path(chemin).read_bytes()
    mime = next((m for t, _, m in FORMATS if octets.startswith(t)), "image/png")
    return base64.b64encode(octets).decode("ascii"), mime


class Fournisseur:
    id, nom, externe, cle_requise, gratuit = "", "", True, False, ""

    def __init__(self, reglages=None):
        self.reglages = reglages or {}

    def disponible(self):
        return True

    def demande(self, consigne, chemin_image, delai=DELAI):
        """Texte rendu par l'IA (SVG ou JSON d'operations). LimiteAtteinte ou RuntimeError en cas d'echec."""
        raise NotImplementedError


class ClaudeLocal(Fournisseur):
    id, nom, externe, gratuit = "claude_local", "Claude Code local (abonnement)", True, "inclus dans l'abonnement, selon ses limites"

    def __init__(self, reglages=None, racine=".", programme=None):
        super().__init__(reglages)
        self.racine, self.programme = Path(racine), programme

    def disponible(self):
        return bool(self.programme or shutil.which("claude"))

    def commande(self, chemin_image):
        prog = self.programme or [shutil.which("claude")]
        return list(prog) + ear.OPTIONS + ["--settings", str(ear.reglages_sans_hooks()), "--add-dir", str(Path(chemin_image).parent)]

    def demande(self, consigne, chemin_image, delai=DELAI):
        if not self.disponible():
            raise RuntimeError("claude introuvable dans le PATH")
        texte = f"Lis l'image {chemin_image} avec ton outil de lecture. {consigne}\n{CADRE}\n"
        try:
            p = subprocess.Popen(self.commande(chemin_image), cwd=self.racine, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as e:
            raise RuntimeError(f"lancement de claude impossible : {e}") from None
        try:
            sortie, erreur = p.communicate(texte.encode("utf-8"), timeout=delai)
        except subprocess.TimeoutExpired:
            ear._arrete(p)
            try:
                p.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                pass
            raise RuntimeError(f"delai de {delai} s depasse") from None
        message, resultat = "", ""
        try:
            resultat = ear._resultat(sortie)
        except ValueError as e:
            message = str(e)
        if p.returncode != 0 or message:
            bruit = (sortie + b"\n" + erreur).decode("utf-8", "replace")
            if LIMITE.search(bruit):
                raise LimiteAtteinte(_reprise(bruit))
            raise RuntimeError(message or f"claude a echoue (code {p.returncode}) : {erreur.decode('utf-8', 'replace')[-200:]}")
        return resultat if isinstance(resultat, str) else json.dumps(resultat)


class Ollama(Fournisseur):
    id, nom, externe, gratuit = "ollama", "Ollama (modele local)", False, "gratuit, tourne sur ce PC"

    def demande(self, consigne, chemin_image, delai=DELAI):
        b64, _ = _image(chemin_image)
        r = _post(self.reglages.get("url") or "http://127.0.0.1:11434/api/generate",
                  {"model": self.reglages.get("modele") or "llava", "prompt": f"{consigne}\n{CADRE}", "images": [b64],
                   "stream": False}, {}, delai)
        return str(r.get("response", "")) if isinstance(r, dict) else ""


class ApiExterne(Fournisseur):
    id, nom, externe, cle_requise, gratuit = "api_externe", "API externe (cle personnelle)", True, True, "selon l'offre du service"

    def disponible(self):
        return bool(self.reglages.get("url") and self.reglages.get("cle") and self.reglages.get("modele"))

    def demande(self, consigne, chemin_image, delai=DELAI):
        if not self.disponible():
            raise RuntimeError("API externe non configuree (url, modele et cle)")
        b64, mime = _image(chemin_image)
        r = _post(self.reglages["url"], {"model": self.reglages["modele"], "messages": [{"role": "user", "content": [
            {"type": "text", "text": f"{consigne}\n{CADRE}"},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}]}]},
            {"Authorization": "Bearer " + self.reglages["cle"]}, delai)
        try:
            return str(r["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError):
            raise RuntimeError("reponse du service inattendue") from None


def fabrique_defaut(config, racine="."):
    f = config.get("fournisseurs", {})
    return {c.id: c for c in (ClaudeLocal(f.get("claude_local"), racine), Ollama(f.get("ollama")), ApiExterne(f.get("api_externe")))}


def fournisseurs(config, fabrique=None, racine="."):
    return [{"id": f.id, "nom": f.nom, "externe": f.externe, "cle_requise": f.cle_requise, "gratuit": f.gratuit,
             "disponible": f.disponible()} for f in (fabrique or fabrique_defaut)(config, racine).values()]


# ---------- quota ----------

def _dossier(config):
    return Path(config.get("_chemin") or cfg.chemin()).parent


def _lit_compteurs(config):
    try:
        d = json.loads((_dossier(config) / "quota.json").read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _note(config, fournisseur_id, maintenant, envoi=False, rouge=False, reprise=None):
    """Met a jour le compteur du jour (atomique)."""
    with VERROU:
        d, jour = _lit_compteurs(config), maintenant.date().isoformat()
        e = d.get(fournisseur_id)
        e = e if isinstance(e, dict) and e.get("jour") == jour else {"jour": jour}
        e["envois"] = e.get("envois", 0) + (1 if envoi else 0)
        if rouge:
            e["rouge"], e["reprise"] = True, reprise
        d[fournisseur_id] = e
        f = _dossier(config) / "quota.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_name("quota.json.tmp")
        tmp.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
        os.replace(tmp, f)


def quota(config, fournisseur_id, maintenant=None):
    """{"envois_jour", "plafond", "etat": ok|orange|rouge, "reprise"} ; rouge des que le plafond est atteint ou qu'un 429 est tombe."""
    maintenant = maintenant or datetime.datetime.now()
    e = _lit_compteurs(config).get(fournisseur_id)
    e = e if isinstance(e, dict) and e.get("jour") == maintenant.date().isoformat() else {}
    n, plafond = e.get("envois", 0), (config.get("fournisseurs", {}).get(fournisseur_id) or {}).get("plafond")
    plafond = plafond if type(plafond) is int and plafond > 0 else None
    etat = "rouge" if e.get("rouge") or (plafond and n >= plafond) else "orange" if plafond and n >= 0.8 * plafond else "ok"
    return {"envois_jour": n, "plafond": plafond, "etat": etat, "reprise": e.get("reprise")}


# ---------- demande ----------

def _journal(config, ligne):
    try:
        with open(_dossier(config) / "ia.log", "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {ligne}\n")
    except OSError:
        pass


def _sans_cle(texte, config):
    for f in config.get("fournisseurs", {}).values():
        if isinstance(f, dict) and f.get("cle"):
            texte = texte.replace(f["cle"], "***")
    return texte


def _resultat(texte):
    bas = texte.lower()
    if "<svg" in bas and "</svg>" in bas:
        return {"svg": avf.nettoie_svg(texte[bas.index("<svg"):bas.rindex("</svg>") + 6])}
    d = ear._json_de(texte)
    if not isinstance(d, dict) or not isinstance(d.get("operations"), list):
        raise ValueError("la reponse n'est ni un SVG ni une liste d'operations")
    return {"operations": d["operations"]}


def demande(racine, env, fournisseur_id, consigne, image_octets, confirme, config, fournisseurs_fabrique=None, maintenant=None):
    """Envoie photo et consigne ; {"svg"|"operations"|"erreur", "quota"}. Refus = aucun envoi, aucun compteur."""
    maintenant = maintenant or datetime.datetime.now()

    def fin(erreur):
        return {"erreur": erreur, "quota": quota(config, fournisseur_id, maintenant)}

    f = (fournisseurs_fabrique or fabrique_defaut)(config, racine).get(fournisseur_id)
    if f is None:
        return fin(f"fournisseur inconnu : {fournisseur_id!r}")
    if not isinstance(consigne, str) or not consigne.strip():
        return fin("consigne vide")
    if len(consigne) > CONSIGNE_MAX:
        return fin(f"consigne trop longue ({len(consigne)} caracteres, {CONSIGNE_MAX} au plus)")
    if f.externe and confirme is not True:
        return fin(f"envoi refuse : la photo irait chez un service externe ({f.nom}), il faut le confirmer")
    q = quota(config, fournisseur_id, maintenant)
    if q["etat"] == "rouge":
        return fin("quota atteint ou service sature" + (f", reprise : {q['reprise']}" if q["reprise"] else "") + " : aucun envoi")
    if not isinstance(image_octets, bytes) or not 0 < len(image_octets) <= IMAGE_MAX:
        return fin("image absente ou trop lourde (10 Mo au plus)")
    ext = next((e for t, e, _ in FORMATS if image_octets.startswith(t)), None)
    if ext is None:
        return fin("image PNG, JPEG ou WebP attendue")
    dossier = tempfile.mkdtemp(prefix="atelier_visuels_ia_")      # hors depot ; supprime quoi qu'il arrive
    try:
        chemin_image = Path(dossier) / f"photo.{ext}"
        chemin_image.write_bytes(image_octets)
        _note(config, fournisseur_id, maintenant, envoi=True)
        try:
            r = _resultat(f.demande(consigne.strip(), chemin_image, DELAI))
        except LimiteAtteinte as e:
            _note(config, fournisseur_id, maintenant, rouge=True, reprise=e.reprise)
            _journal(config, f"{env} {fournisseur_id} limite atteinte, reprise {e.reprise}")
            return fin("trop de requetes : le service demande d'attendre" + (f" ({e.reprise})" if e.reprise else "")
                       + " ; aucun nouvel essai automatique")
        except (RuntimeError, ValueError) as e:
            msg = _sans_cle(str(e), config)
            _journal(config, f"{env} {fournisseur_id} erreur : {msg}")
            return fin(msg)
        _journal(config, f"{env} {fournisseur_id} ok ({'svg' if 'svg' in r else 'operations'})")
        return {**r, "quota": quota(config, fournisseur_id, maintenant)}
    finally:
        shutil.rmtree(dossier, ignore_errors=True)
