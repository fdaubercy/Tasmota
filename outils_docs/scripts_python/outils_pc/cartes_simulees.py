r"""Cartes simulees hors ligne (plan tasks/plans/cartes-simulees.md, A1 a A3) : une carte du parc rejouee par ses VRAIS modules Berry.

UTILISATION
    python outils_docs/scripts_python/outils_pc/cartes_simulees.py --liste
    python outils_docs/scripts_python/outils_pc/cartes_simulees.py tasmota32s3-garage-rideau-garage-modbus [--port 7940]
Sert http://127.0.0.1:<port>/ : accueil imite de Tasmota + ajout Berry reel de la carte, /sd/* depuis data/sd, routes Berry.
Panneau de scenario : /__sim (position du P4, fins de course). Rien n'est ecrit dans le depot, aucune requete vers une vraie carte.

Toute carte du parc qui a un _persist.json est simulable (identite reseau, /sd, /cm Status 5 et 6). Les modules Berry rejoues par
berry.exe (accueil et routes de la carte) sont declares dans MODULES_BERRY : pour l'instant le rideau du garage seulement.
CE QU'IL NE SIMULE PAS : les pages natives du C++ de Tasmota (Configuration, Console), /cm hors cas prevus.
"""
import argparse
import html
import json
import subprocess
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cartes_simulees_reseau as reseau  # noqa: E402  (module voisin : identite reseau lue dans le persist)
import build_envs  # noqa: E402  (module voisin : liste des envs et leur adresse)
import fichiers_berry_etat  # noqa: E402  (module voisin : dossier data/ d'un env)

RACINE = next(p for p in Path(__file__).resolve().parents if (p / ".git").exists())
BERRY = RACINE / "lib" / "libesp32" / "berry" / "berry.exe"
SCRIPTS = RACINE / "outils_docs" / "scripts_python" / "berry"
# env -> script Berry qui rejoue UNE requete avec les vrais modules de la carte ; routes = chemins servis par ces modules
MODULES_BERRY = {"tasmota32s3-garage-rideau-garage-modbus": {"script": "simule_carte_rideau.be", "routes": ["/rideau"]}}
SCENARIO = {"maitre": {"code": 200, "position": 30}, "interrupteurs": {"1": "OFF", "2": "OFF"}, "source_p4": "simule"}
URL_MAITRE = None          # test : adresse d'un faux P4 ; None = http://<ipMaitre du persist>/cm?cmnd=Status%2010
VERROU = threading.Lock()

TETE = ("<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'/>"
        "<title>{titre} (simule)</title><style>:root{{--c_bg:#252525;--c_txt:#eaeaea;--c_btn:#1fa3ec;--c_btntxt:#faffff}}"
        "body{{text-align:center;font-family:verdana,sans-serif;background:var(--c_bg);color:var(--c_txt)}}"
        "button{{border:0;border-radius:.3rem;background:var(--c_btn);color:var(--c_btntxt);line-height:2.4rem;font-size:1.2rem;width:100%}}"
        ".sim{{background:#7a4b00;color:#fff;padding:4px;font-size:.8rem}}</style></head><body>"
        "<div class='sim'>CARTE SIMULEE : les valeurs ne viennent pas de la vraie carte. <a href='/__sim' style='color:#fff'>scenario</a></div>"
        "<div style='display:inline-block;min-width:340px;text-align:left'><div style='text-align:center'><h3>{hote}</h3><h2>{titre}</h2></div>")
PIED = "<p></p><button>Configuration</button></div></body></html>"


_INVENTAIRE = {}


def inventaire():
    """{env: {"env", "dossier", "adresse", "berry"}} des cartes du parc (famille « cartes ») dont le dossier porte un _persist.json."""
    if not _INVENTAIRE:
        for e in build_envs.liste_envs(RACINE):
            if e.famille != "cartes":
                continue
            try:
                d = fichiers_berry_etat.dossier_carte(e.nom)
            except ValueError:
                continue
            if d and (RACINE / d / "_persist.json").is_file():
                _INVENTAIRE[e.nom] = {"env": e.nom, "dossier": d, "adresse": e.ip or "", "berry": e.nom in MODULES_BERRY}
    return _INVENTAIRE


def liste():
    """Envs simulables, tries : nom, dossier de donnees, adresse du parc (IP ou IP:port), modules Berry rejoues ou non."""
    return sorted(inventaire().values(), key=lambda c: (not c["berry"], c["env"]))      # cartes aux modules Berry rejoues d'abord


def lit_p4(env):
    """Reponse REELLE du P4 en ligne a Status 10 (un GET en lecture seule, 3 s), ou None s'il ne repond pas."""
    url = URL_MAITRE or f"http://{profil_reseau(env)['ip_maitre']}/cm?cmnd=Status%2010"
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return r.read().decode("utf-8", "replace")
    except (OSError, ValueError):
        return None


def requete_berry(env, *args):
    """Une requete rejouee par berry.exe (cwd = racine) ; rend {"code", "mime", "corps", "fichiers"}. Exception si Berry echoue."""
    if not BERRY.exists():
        raise RuntimeError(f"berry.exe introuvable : {BERRY}")
    dossier = str(fichiers_berry_etat.dossier_carte(env))
    with VERROU:
        scenario = RACINE / ".pio" / "cartes_simulees_scenario.json"
        scenario.parent.mkdir(parents=True, exist_ok=True)
        sc = dict(SCENARIO)
        if sc.get("source_p4") == "reel":       # le rideau simule lit la vraie position du P4, comme la vraie carte
            brut = lit_p4(env)
            sc["maitre"] = {"code": 200, "brut": brut} if brut else {"code": -1}
        scenario.write_text(json.dumps(sc), encoding="utf-8")
        r = subprocess.run([str(BERRY), str(SCRIPTS / MODULES_BERRY[env]["script"]), dossier, str(scenario), *args], cwd=str(RACINE),
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    for ligne in reversed((r.stdout or "").splitlines()):
        if ligne.startswith("SIMULE:"):
            return json.loads(ligne[7:])
    raise RuntimeError("Berry n'a rendu aucune reponse : " + ((r.stdout or "") + (r.stderr or ""))[-400:])


def fichier_sd(chemin):
    """Fichier de data/sd, ou None (jamais hors du dossier : '..' refuse)."""
    base = (RACINE / "data" / "sd").resolve()
    f = (base / chemin.lstrip("/")).resolve()
    return f if base in f.parents and f.is_file() else None


def profil_reseau(env):
    p = reseau.profil(RACINE / inventaire()[env]["dossier"])
    p["adresse"] = inventaire()[env]["adresse"]          # adresse connue du parc (WIFI_IP_ADDRESS ou maitre:port), peut differer du persist
    return p


def commande(env, cmnd):
    """/cm?cmnd= : seules les commandes de lecture de l'identite reseau sont simulees (valeurs du persist), le reste est refuse."""
    p = profil_reseau(env)
    c = " ".join(cmnd.split()).lower()
    if c == "status 5":
        return reseau.status5(p)
    if c == "status 6":
        return reseau.statut_mqtt(p)
    return {"Command": "Unknown", "Simule": "commande non simulee : " + cmnd}


def accueil_generique(env):
    """Carte dont les modules Berry ne sont pas encore rejoues : identite reseau du persist et liste honnete de ce qui manque."""
    p = profil_reseau(env)
    lignes = "".join(f"<li>{html.escape(x)}</li>" for x in reseau.resume(p))
    return (TETE.format(titre=html.escape(p["nom"] or env), hote=html.escape(p["hostname"])) + "<ul style='font-size:.85rem'>" + lignes + "</ul>"
            "<p style='font-size:.85rem'>Modules Berry de cette carte non rejoues : seule l'identite reseau est simulee.</p>" + PIED)


def accueil(env):
    if env not in MODULES_BERRY:
        return accueil_generique(env)
    r = requete_berry(env, "accueil")
    corps = r["corps"]
    for chemin in r["fichiers"]:        # le module envoie le fichier /sd/... a la ligne : on l'insere comme la carte
        f = fichier_sd(chemin.removeprefix("/sd"))
        corps = corps.replace("<script></script>", "<script>" + (f.read_text(encoding="utf-8") if f else "") + "</script>", 1)
    return TETE.format(titre=html.escape(profil_reseau(env)["nom"] or env), hote=html.escape(profil_reseau(env)["hostname"])) + corps + PIED


PANNEAU = """<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'><title>Scenario</title></head>
<body style='font-family:sans-serif;max-width:30rem;margin:1rem auto'><h3>Scenario du rideau simule</h3>
<label>Position du P4 <select id='src'><option value='simule'>simulee (ci-dessous)</option><option value='reel'>lue sur le vrai P4 en ligne</option></select></label><br>
<label>P4 muet (simule) <input id='muet' type='checkbox'></label><br><label>Curseur du P4 (0..100) <input id='pos' type='number' value='30'></label><br>
<label>Fin de course ouverture <select id='i2'><option>OFF</option><option>ON</option></select></label><br>
<label>Fin de course fermeture <select id='i1'><option>OFF</option><option>ON</option></select></label><br>
<button onclick='go()'>Appliquer</button> <a href='/'>accueil</a><pre id='r'></pre><script>
function go(){fetch('/__sim',{method:'POST',headers:{'X-Sim':'1'},body:JSON.stringify({source_p4:document.getElementById('src').value,maitre:document.getElementById('muet').checked?{code:-1}:
{code:200,position:+document.getElementById('pos').value},interrupteurs:{1:document.getElementById('i1').value,2:document.getElementById('i2').value}})})
.then(r=>r.text()).then(t=>document.getElementById('r').textContent=t)}</script></body></html>"""


def serveur(env, port):
    class H(BaseHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A002 : silence
            pass

        def envoie(self, code, mime, corps):
            b = corps if isinstance(corps, bytes) else corps.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            u = urlparse(self.path)
            try:
                if u.path == "/":
                    return self.envoie(200, "text/html", accueil(env))
                if u.path == "/__sim":
                    return self.envoie(200, "text/html", PANNEAU.replace("<pre id='r'>", "<pre id='r'>" + html.escape("\n".join(reseau.resume(profil_reseau(env))))))
                if u.path == "/cm":
                    return self.envoie(200, "application/json", json.dumps(commande(env, dict(parse_qsl(u.query)).get("cmnd", ""))))
                if u.path in MODULES_BERRY.get(env, {}).get("routes", []):
                    q = dict(parse_qsl(u.query))
                    r = requete_berry(env, "route", u.path, q.get("id", "1"))
                    return self.envoie(r["code"], r["mime"], r["corps"])
                f = fichier_sd(u.path.removeprefix("/sd")) if u.path.startswith("/sd/") else None
                if f:
                    return self.envoie(200, "application/octet-stream", f.read_bytes())
                self.envoie(404, "text/plain", "Non simule : page native de Tasmota (C++) ou route inconnue : " + u.path)
            except Exception as e:  # noqa: BLE001 : une erreur de Berry ne tue pas le serveur
                self.envoie(500, "text/plain", f"Erreur de simulation : {e}")

        def do_POST(self):
            if self.path != "/__sim" or self.headers.get("X-Sim") != "1":      # anti-CSRF : en-tete propre a la page
                return self.envoie(403, "text/plain", "refuse")
            try:
                n = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                SCENARIO["maitre"] = n["maitre"]
                SCENARIO["source_p4"] = "reel" if n.get("source_p4") == "reel" else "simule"
                SCENARIO["interrupteurs"] = {k: ("ON" if v == "ON" else "OFF") for k, v in n["interrupteurs"].items()}
                self.envoie(200, "text/plain", "scenario applique : " + json.dumps(SCENARIO))
            except (ValueError, KeyError, TypeError):
                self.envoie(400, "text/plain", "scenario illisible")
    return ThreadingHTTPServer(("127.0.0.1", port), H)


def main():
    ap = argparse.ArgumentParser(description="Cartes simulees hors ligne")
    ap.add_argument("env", nargs="?")
    ap.add_argument("--liste", action="store_true")
    ap.add_argument("--port", type=int, help="defaut : le port web de la vraie carte d'apres son persist (8080 + id - 1 derriere un maitre)")
    a = ap.parse_args()
    if a.liste or not a.env:
        for c in liste():
            print(f"{c['env']}  {c['adresse'] or '(pas d adresse)'}  {'modules Berry rejoues' if c['berry'] else 'identite reseau seule'}")
        return 0
    if a.env not in inventaire():
        print(f"ERREUR : {a.env} n'est pas une carte simulable ; voir --liste", file=sys.stderr)
        return 2
    p = profil_reseau(a.env)
    port = a.port or p["port_web"]
    s = serveur(a.env, port)
    print("Identite reseau lue dans le persist :\n  " + "\n  ".join(reseau.resume(p)), flush=True)
    print(f"Carte simulee : http://127.0.0.1:{port}/  (adresse reelle : voir plan A5, IP sous garde ; Ctrl+C pour arreter)", flush=True)
    try:
        s.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
