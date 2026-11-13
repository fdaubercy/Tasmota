#!/usr/bin/env python3
"""Banc de l'assistant IA de l'atelier des visuels (atelier_visuels_ia.py, atelier_visuels_ia_config.py) : refus sans
confirmation, cle jamais exposee, SVG hostile nettoye, quota (orange, rouge, 429 sans reessai), consigne longue, image
temporaire supprimee, options en lecture seule de claude_local. AUCUN appel reseau reel ni vrai claude : faux fournisseurs,
faux programme claude (script Python) et faux serveur sur 127.0.0.1. Config et donnees dans un dossier temporaire. Code 0 = vert.

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_atelier_visuels_ia.py
"""
import datetime
import json
import os
import shutil
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TMP = Path(tempfile.mkdtemp(prefix="test_visuels_ia_"))
os.environ["OUTILS_TASMOTA_DOSSIER"] = str(TMP / "donnees")       # reglages_sans_hooks y ecrit : jamais le vrai dossier

import atelier_ecrans_remarques as ear          # noqa: E402
import atelier_visuels_ia as ia                 # noqa: E402
import atelier_visuels_ia_config as cfg         # noqa: E402

ECHECS = []
CLE = "sk-SECRET-0123456789"
PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 20
JOUR = datetime.datetime(2026, 11, 13, 10, 0)
SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="5" height="5" fill="#fff"/></svg>'
HOSTILE = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" onload="alert(1)"><script>alert(1)</script>'
           '<rect width="5" height="5" onclick="x()" fill="url(javascript:1)"/><foreignObject><p>x</p></foreignObject></svg>')


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


class Faux(ia.Fournisseur):
    """Faux fournisseur : compte ses appels, rend `reponse` ou leve `leve`."""

    def __init__(self, id_="faux", externe=True, reponse=SVG, leve=None):
        super().__init__({})
        self.id, self.nom, self.externe, self.reponse, self.leve = id_, "Faux service", externe, reponse, leve
        self.appels, self.chemins = 0, []

    def demande(self, consigne, chemin_image, delai=600):
        self.appels += 1
        self.chemins.append(Path(chemin_image))
        verifie(Path(chemin_image).is_file(), True, "photo presente pendant l'appel")
        if self.leve:
            raise self.leve
        return self.reponse


def nouvelle_config(nom, plafond=None):
    d = TMP / nom
    c = cfg.lit(d / "config.json")
    cfg.regle(c, "faux", cle=CLE, plafond=plafond)
    cfg.ecrit(c)
    return c


def appelle(c, faux, consigne="la maison seule", confirme=True, maintenant=JOUR):
    return ia.demande(TMP, "env", faux.id, consigne, PNG, confirme, c, lambda config, racine: {faux.id: faux}, maintenant)


def lit_texte(c, nom):
    f = Path(c["_chemin"]).parent / nom
    return f.read_text(encoding="utf-8") if f.exists() else ""


def serveur(code, corps, entetes=None):
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            self.send_response(code)
            for k, v in (entetes or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(json.dumps(corps).encode())

        def log_message(self, *a):
            pass
    s = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


def main():
    # 1. confirmation
    c, f = nouvelle_config("a"), Faux()
    r = appelle(c, f, confirme=False)
    verifie((f.appels, "erreur" in r, r["quota"]["envois_jour"]), (0, True, 0), "externe sans confirmation : refus, fournisseur non appele")
    r = appelle(c, Faux("local", externe=False), confirme=False)
    verifie("svg" in r, True, "local sans confirmation : accepte")
    r = appelle(c, f)
    verifie(("svg" in r, f.appels, r["quota"]["envois_jour"]), (True, 1, 1), "externe confirme : appele, envoi compte")

    # 2. cle jamais exposee
    f = Faux(leve=RuntimeError(f"echec avec la cle {CLE}"))
    r = appelle(nouvelle_config("b"), f)
    c = nouvelle_config("b2")
    appelle(c, Faux(leve=RuntimeError(f"echec avec la cle {CLE}")))
    verifie(CLE in json.dumps(r), False, "cle absente de l'erreur renvoyee")
    verifie(CLE in lit_texte(c, "ia.log") + lit_texte(c, "quota.json"), False, "cle absente du journal et des compteurs")
    page = json.dumps(cfg.pour_page(c)) + json.dumps(ia.fournisseurs(c, lambda config, racine: {"faux": f}))
    verifie((CLE in page, cfg.pour_page(c)["faux"]["cle"]), (False, {"presente": True, "fin": "6789"}), "pour_page et fournisseurs sans la cle")
    verifie("_chemin" in json.loads(Path(c["_chemin"]).read_text(encoding="utf-8")), False, "_chemin non ecrit dans la config")
    verifie(cfg.lit(c["_chemin"])["fournisseurs"]["faux"]["cle"], CLE, "config relue")

    # 3. SVG hostile
    r = appelle(nouvelle_config("c"), Faux(reponse="Voici : " + HOSTILE + " voila"))
    svg = r.get("svg", "")
    verifie((bool(svg), "script" in svg, "onload" in svg, "onclick" in svg, "javascript" in svg, "foreignObject" in svg),
            (True, False, False, False, False, False), "SVG hostile nettoye")
    verifie("erreur" in appelle(nouvelle_config("c2"), Faux(reponse="du texte")), True, "reponse ni SVG ni JSON : erreur")
    r = appelle(nouvelle_config("c3"), Faux(reponse='```json\n{"operations": [{"op": "efface"}]}\n```'))
    verifie(r.get("operations"), [{"op": "efface"}], "operations JSON reconnues")

    # 4. 429 : rouge, aucun second appel
    c, f = nouvelle_config("d"), Faux(leve=ia.LimiteAtteinte("dans 30 s"))
    r = appelle(c, f)
    verifie((r["quota"]["etat"], r["quota"]["reprise"], f.appels), ("rouge", "dans 30 s", 1), "429 : quota rouge, reprise notee")
    verifie("trop de requetes" in r["erreur"], True, "429 : message clair")
    r = appelle(c, f)
    verifie((f.appels, "erreur" in r), (1, True), "apres 429 : aucun second appel")
    lendemain = JOUR + datetime.timedelta(days=1)
    verifie(ia.quota(c, "faux", lendemain)["etat"], "ok", "rouge retombe le lendemain")

    # 5. plafond
    c, f = nouvelle_config("e", plafond=10), Faux()
    etats = []
    for _ in range(10):
        etats.append(appelle(c, f)["quota"]["etat"])
    verifie(etats, ["ok"] * 7 + ["orange", "orange", "rouge"], "plafond 10 : orange des 8 envois, rouge au 10e")
    verifie((appelle(c, f).get("erreur") is not None, f.appels), (True, 10), "plafond atteint : plus d'envoi")

    # 6. consigne
    f = Faux()
    verifie((("erreur" in appelle(nouvelle_config("f"), f, consigne="x" * 2001)), f.appels), (True, 0), "consigne de 2001 caracteres refusee")
    verifie(("erreur" in appelle(nouvelle_config("f2"), f, consigne="  ")), True, "consigne vide refusee")

    # 7. image temporaire supprimee, meme apres exception inattendue
    f = Faux(leve=KeyError("bug"))
    try:
        appelle(nouvelle_config("g"), f)
    except KeyError:
        pass
    verifie((len(f.chemins), f.chemins[0].parent.exists()), (1, False), "dossier temporaire supprime apres exception")
    f = Faux()
    appelle(nouvelle_config("g2"), f)
    verifie(f.chemins[0].parent.exists() or f.chemins[0].parent.parent == TMP, False, "dossier temporaire supprime apres succes et hors du dossier de test")

    # 8. claude_local : options en lecture seule
    cl = ia.ClaudeLocal({}, racine=TMP, programme=["faux-claude"])
    cmd = cl.commande(Path("/x/photo.png"))
    reglages = ear.reglages_sans_hooks()
    verifie(cmd, ["faux-claude"] + ear.OPTIONS + ["--settings", str(reglages), "--add-dir", str(Path("/x"))], "claude_local : options exactes")
    verifie(("bypassPermissions" in " ".join(cmd), "dontAsk" in cmd, "Read,Grep,Glob" in cmd, "--strict-mcp-config" in cmd),
            (False, True, True, True), "claude_local : lecture seule, pas de bypassPermissions")
    verifie(json.loads(reglages.read_text(encoding="utf-8")), {"disableAllHooks": True}, "claude_local : --settings sans hooks")
    verifie(cl.externe, True, "claude_local : marque externe")

    # 8 bis. claude_local sur un faux programme (script Python lisant l'entree standard)
    faux = TMP / "faux_claude.py"
    faux.write_text("import json, os, sys\nsys.stdin.read()\nm = os.environ['FAUX_MODE']\n"
                    "if m == 'ok':\n    print(json.dumps({'result': os.environ['FAUX_SVG']}))\n"
                    "else:\n    print(json.dumps({'is_error': True, 'result': 'Claude usage limit reached|resets at 5pm'}))\n"
                    "    sys.exit(1)\n", encoding="utf-8")
    prog = [sys.executable, str(faux)]
    c = nouvelle_config("h")
    fab = lambda config, racine: {"claude_local": ia.ClaudeLocal({}, racine, prog)}
    os.environ["FAUX_MODE"], os.environ["FAUX_SVG"] = "ok", SVG
    r = ia.demande(TMP, "env", "claude_local", "la maison", PNG, True, c, fab, JOUR)
    verifie("svg" in r, True, "claude_local : faux claude, SVG recu")
    os.environ["FAUX_MODE"] = "limite"
    r = ia.demande(TMP, "env", "claude_local", "la maison", PNG, True, c, fab, JOUR)
    verifie((r["quota"]["etat"], r["quota"]["reprise"]), ("rouge", "5pm"), "claude_local : message de limite = rouge, reprise lue")

    # 9. API HTTP : 429 d'un faux serveur local, puis reponse normale
    s = serveur(429, {"error": CLE}, {"Retry-After": "45"})
    c = nouvelle_config("i")
    cfg.regle(c, "api_externe", cle=CLE, url=f"http://127.0.0.1:{s.server_address[1]}/v1", modele="m")
    r = ia.demande(TMP, "env", "api_externe", "la maison", PNG, True, c, None, JOUR)
    s.shutdown()
    verifie((r["quota"]["etat"], r["quota"]["reprise"], CLE in json.dumps(r)), ("rouge", "dans 45 s", False), "API : HTTP 429 = rouge, Retry-After lu")
    s = serveur(200, {"choices": [{"message": {"content": SVG}}]})
    cfg.regle(c, "api_externe", url=f"http://127.0.0.1:{s.server_address[1]}/v1")
    c2 = nouvelle_config("i2")
    c2["fournisseurs"]["api_externe"] = c["fournisseurs"]["api_externe"]
    r = ia.demande(TMP, "env", "api_externe", "la maison", PNG, False, c2, None, JOUR)
    verifie("confirm" in r.get("erreur", ""), True, "API externe sans confirmation : refus")
    r = ia.demande(TMP, "env", "api_externe", "la maison", PNG, True, c2, None, JOUR)
    s.shutdown()
    verifie("svg" in r, True, "API : reponse 200 lue")
    s = serveur(200, {"response": SVG})
    cfg.regle(c2, "ollama", url=f"http://127.0.0.1:{s.server_address[1]}/api/generate")
    r = ia.demande(TMP, "env", "ollama", "la maison", PNG, False, c2, None, JOUR)
    s.shutdown()
    verifie("svg" in r, True, "ollama : local, sans confirmation, reponse lue")
    ids = {x["id"]: x["externe"] for x in ia.fournisseurs(c2)}
    verifie(ids, {"claude_local": True, "ollama": False, "api_externe": True}, "fournisseurs : ids et externe")

    print("VERT" if not ECHECS else f"ROUGE : {ECHECS}")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    try:
        code = main()
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(code)
