"""Liens web du depot : liste (liens cites + liens ajoutes), ajout, retrait et archivage PDF des fiches.

Logique de la page « Liens web » (liens_web_web.py, port 7905). Les liens cites viennent de genere_liens_web.collecte ;
les liens ajoutes sont dans outils_docs/liens_web/liens_ajoutes.json ; les archives (PDF) dans
outils_docs/liens_web/archives/ (ignore par git : depot public, droits d'auteur, poids) avec leur index.json.

Archivage : une URL qui rend un PDF est copiee telle quelle ; une page HTML est imprimee en PDF par Chrome sans fenetre.
Refus : hote prive ou local (anti-SSRF, redirections comprises), autre schema que http(s), plus de MAX_OCTETS, autre type.
"""
import hashlib
import http.client
import ipaddress
import json
import os
import re
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import genere_liens_web as gen

MAX_OCTETS = 40 * 1024 * 1024
DELAI_RESEAU = 30
DELAI_CHROME = 90
VERROU = threading.Lock()                       # une ecriture ou un archivage a la fois
CATEGORIES = [c[0] for c in gen.CATEGORIES] + ["Autres sites"]


def dossier(racine):
    return Path(racine) / "outils_docs" / "liens_web"


def identifiant(url):
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]


def _lit_json(chemin, defaut):
    try:
        return json.loads(Path(chemin).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defaut


def _ecrit_json(chemin, donnees):
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tmp = chemin.with_suffix(chemin.suffix + ".tmp")
    tmp.write_text(json.dumps(donnees, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, chemin)


def construit(racine):
    """{liens, categories, chrome}. Un lien : id, url, categorie, fichiers, ajoute, titre, note, archive."""
    d = dossier(racine)
    index = _lit_json(d / "archives" / "index.json", {})
    liens = {}
    for u, fichiers in gen.collecte().items():
        liens[u] = {"url": u, "categorie": gen.categorie(u), "fichiers": sorted(fichiers)[:3], "ajoute": False, "titre": "", "note": ""}
    for x in _lit_json(d / "liens_ajoutes.json", []):
        if isinstance(x, dict) and gen.utile(str(x.get("url", ""))):
            liens[x["url"]] = {"url": x["url"], "categorie": x.get("categorie") or "Autres sites", "fichiers": [],
                               "ajoute": True, "titre": x.get("titre", ""), "note": x.get("note", "")}
    sortie = []
    for u in sorted(liens, key=str.lower):
        i = identifiant(u)
        a = index.get(i)
        liens[u]["id"] = i
        ok = a and (d / "archives" / a["fichier"]).is_file()
        liens[u]["archive"] = {"fichier": a["fichier"], "date": a["date"], "taille": a["taille"]} if ok else None
        sortie.append(liens[u])
    return {"liens": sortie, "categories": CATEGORIES, "chrome": trouve_chrome() is not None}


def _texte(valeur, maxi, libelle, obligatoire=False):
    v = str(valeur or "").strip()
    if len(v) > maxi or (obligatoire and not v) or any(ord(c) < 32 for c in v):
        raise ValueError(f"{libelle} : {'obligatoire, ' if obligatoire else ''}{maxi} caracteres au plus, sans caractere de controle")
    return v


def ajoute(racine, d):
    """Ajoute (ou met a jour) un lien saisi a la main. ValueError si invalide."""
    url = _texte(d.get("url"), 500, "adresse", True)
    if not re.match(r"https?://", url) or not gen.utile(url):
        raise ValueError("adresse : http(s) vers un site public attendu (pas d'IP, de nom local ni d'identifiant dans l'URL)")
    categorie = _texte(d.get("categorie"), 80, "categorie") or "Autres sites"
    if categorie not in CATEGORIES:
        raise ValueError("categorie inconnue")
    entree = {"url": url, "titre": _texte(d.get("titre"), 120, "titre"), "categorie": categorie,
              "note": _texte(d.get("note"), 300, "note"), "date": time.strftime("%Y-%m-%d")}
    chemin = dossier(racine) / "liens_ajoutes.json"
    with VERROU:
        liste = [x for x in _lit_json(chemin, []) if isinstance(x, dict) and x.get("url") != url]
        _ecrit_json(chemin, liste + [entree])
    return entree


def retire(racine, identifiant_lien):
    """Retire un lien AJOUTE (un lien cite dans un fichier se corrige dans ce fichier). KeyError s'il n'existe pas."""
    chemin = dossier(racine) / "liens_ajoutes.json"
    with VERROU:
        liste = _lit_json(chemin, [])
        reste = [x for x in liste if identifiant(str(x.get("url"))) != identifiant_lien]
        if len(reste) == len(liste):
            raise KeyError("lien ajoute introuvable (un lien cite dans un fichier ne se retire pas ici)")
        _ecrit_json(chemin, reste)


# ---- archivage -------------------------------------------------------------------------------------------------

def verifie_hote(url):
    """ValueError si l'URL n'est pas http(s) vers un hote public (toutes ses adresses resolues)."""
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
        raise ValueError("adresse http(s) sans identifiant attendue")
    try:
        port = p.port or (443 if p.scheme == "https" else 80)
        adresses = {a[4][0] for a in socket.getaddrinfo(p.hostname, port, proto=socket.IPPROTO_TCP)}
    except (OSError, ValueError) as e:
        raise ValueError(f"hote introuvable : {e}")
    for a in adresses:
        if not ipaddress.ip_address(a.split("%")[0]).is_global:
            raise ValueError("hote local ou prive refuse")


class _Redirection(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        verifie_hote(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def trouve_chrome():
    for var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(var)
        if base:
            c = Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe"
            if c.is_file():
                return str(c)
    return None


def _imprime_pdf(chrome, url, sortie):
    with tempfile.TemporaryDirectory() as profil:
        cmd = [chrome, "--headless=new", "--disable-gpu", f"--user-data-dir={profil}", "--no-pdf-header-footer",
               "--virtual-time-budget=15000", f"--print-to-pdf={sortie}", url]
        p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        try:
            p.wait(DELAI_CHROME)
        except subprocess.TimeoutExpired:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)   # Chrome et ses fils : pas d'orphelin
            raise ValueError("Chrome a depasse le delai")


def nom_fichier(url, i):
    p = urllib.parse.urlsplit(url)
    return re.sub(r"[^a-z0-9]+", "-", (p.hostname + p.path).lower()).strip("-")[:60] + f"-{i}.pdf"


def archive(racine, url):
    """Archive l'URL en PDF dans archives/ ; rend l'entree d'index. ValueError avec un message lisible sinon."""
    verifie_hote(url)
    i = identifiant(url)
    d = dossier(racine) / "archives"
    d.mkdir(parents=True, exist_ok=True)
    nom = nom_fichier(url, i)
    if not VERROU.acquire(blocking=False):
        raise ValueError("une ecriture ou un archivage est deja en cours")
    tmp = d / (nom + ".tmp")
    try:
        ouvre = urllib.request.build_opener(_Redirection)
        try:
            with ouvre.open(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (archivage local)"}), timeout=DELAI_RESEAU) as r:
                type_ = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                if type_ == "application/pdf":
                    lus = 0
                    with open(tmp, "wb") as f:
                        while True:
                            bloc = r.read(65536)
                            if not bloc:
                                break
                            lus += len(bloc)
                            if lus > MAX_OCTETS:
                                raise ValueError("fichier trop gros (40 Mo au plus)")
                            f.write(bloc)
                elif type_ in ("text/html", "application/xhtml+xml"):
                    chrome = trouve_chrome()
                    if not chrome:
                        raise ValueError("Chrome introuvable : une page HTML ne peut pas etre imprimee en PDF")
                    _imprime_pdf(chrome, r.geturl(), str(tmp))
                else:
                    raise ValueError(f"type {type_ or 'inconnu'} non archivable (PDF ou page HTML seulement)")
        except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
            raise ValueError(f"telechargement impossible : {getattr(e, 'reason', e)}")
        if not tmp.is_file() or tmp.stat().st_size < 100 or tmp.read_bytes()[:5] != b"%PDF-":
            raise ValueError("le resultat n'est pas un PDF")
        os.replace(tmp, d / nom)
        entree = {"url": url, "fichier": nom, "date": time.strftime("%Y-%m-%d %H:%M"), "taille": (d / nom).stat().st_size}
        index = _lit_json(d / "index.json", {})
        index[i] = entree
        _ecrit_json(d / "index.json", index)
        return entree
    finally:
        tmp.unlink(missing_ok=True)
        VERROU.release()


def chemin_archive(racine, nom):
    """Chemin d'une archive de l'index, sinon LookupError (jamais un chemin venu tel quel de la requete)."""
    d = dossier(racine) / "archives"
    for e in _lit_json(d / "index.json", {}).values():
        if e.get("fichier") == nom and (d / nom).is_file():
            return d / nom
    raise LookupError("archive inconnue")


def regenere_document(racine):
    """Reecrit outils_docs/LIENS_WEB.md ; rend le nombre de lignes."""
    texte = gen.ecrit()
    gen.SORTIE.write_text(texte, encoding="utf-8", newline="\n")
    return texte.count("\n")
