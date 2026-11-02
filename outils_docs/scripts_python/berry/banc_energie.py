r"""Banc de la page /energie : Berry (banc_energie.be), temoins sur des copies du module, puis rendu dans Chrome.

    python outils_docs/scripts_python/berry/banc_energie.py [--sans-navigateur] [--garde DOSSIER]

Code de sortie 0 si tout est vert. --garde : garde la capture a 340 px (energie_340.png) dans DOSSIER.
Rendu : la page (css, html, js reels) est servie avec les donnees produites par le vrai module Berry ; le banc juge ce que
la page expose (data-valeurs, totaux, tuiles, rappel) et le POST du prix.
Ne teste pas la vraie carte : ni le serveur web de Tasmota, ni la RAM, ni la vraie mesure.
"""
import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from banc_cuve_page import rend, trouve_navigateur, trouve_racine

RACINE = trouve_racine()
BERRY = RACINE / "lib/libesp32/berry/berry.exe"
BANC = "outils_docs/scripts_python/berry/banc_energie.be"
MODULE = RACINE / "data/fs/energieFonctions.be"

# Chaque mutant doit rendre le banc rouge : (nom, texte du module, remplacement)
MUTANTS = [
    ("baisse du compteur comptee", "delta < 0 ||", "false ||"),
    ("compteur retabli compte", "real(delta) > real(energieFonctions.PUISSANCE_MAX_W) * (ecoule + 3600) / 3600", "false"),
    ("purge du plus recent", "archives[i] < archives[ancien]", "archives[i] > archives[ancien]"),
    ("prix futur applique", "p[0] <= jour", "true"),
    ("heure d'ete portee au constat", 'ecoule <= energieFonctions.ECART_CONSECUTIF_S ? etat["l"] : local - 3600', "local - 3600"),
    ("calibrage ecrase", "r.find(cle) != energieFonctions.DEFAUTS_BL0942[cle]", "false"),
    ("import du module oublie (solidifie)", "    import energieFonctions\n    var t = tasmota.time_dump(instant)", "    var t = tasmota.time_dump(instant)"),
    ("points de la coupure gardes", "courbe.set(2 * i, energieFonctions.POINT_VIDE, 2)\n    end\n    return courbe", "end\n    return courbe"),
    ("copie perimee relue", "ecoule >= energieFonctions.NB_POINTS * energieFonctions.PAS_COURBE_S", "false"),
    ("acces non controle", "if (!webserver.check_privileged_access())    return nil    end\n    var f =", "var f ="),
    ("acces au prix non controle", "if (!webserver.check_privileged_access())    return nil    end\n    var erreur =", "var erreur ="),
]


def lance_berry(dossier, module=None):
    args = [str(BERRY), BANC, str(dossier)] + ([str(module)] if module else [])
    r = subprocess.run(args, cwd=RACINE, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    return r.stdout + r.stderr


def partie_berry(tmp):
    d = tmp / "berry"
    d.mkdir()
    sortie = lance_berry(d)
    print("\n".join(l for l in sortie.splitlines() if not l.startswith("  OK")))
    print(f"  ({sum(l.startswith('  OK') for l in sortie.splitlines())} verifications OK)")
    ok = "BANC_ENERGIE: OK" in sortie
    texte = MODULE.read_text(encoding="utf-8")
    print("--- Temoins (chaque mutant doit etre rouge)")
    for i, (nom, avant, apres) in enumerate(MUTANTS):
        if avant not in texte:
            print(f"  ECHEC temoin « {nom} » : texte introuvable dans le module")
            ok = False
            continue
        dm = tmp / f"mutant{i}"
        dm.mkdir()
        copie = dm / "mutant.be"
        copie.write_text(texte.replace(avant, apres), encoding="utf-8")
        rouge = "BANC_ENERGIE: OK" not in lance_berry(dm, copie)
        print(f"  {'OK   ' if rouge else 'ECHEC'} {nom}")
        ok = ok and rouge
    return ok, json.loads((d / "donnees.json").read_text(encoding="utf-8"))


def page_html(js_modifie=None):
    sd = RACINE / "data/sd"
    js = js_modifie if js_modifie is not None else (sd / "js/energie.js").read_text(encoding="utf-8")
    return ("<!doctype html><meta charset='utf-8'><body style='width:320px'><style>" + (sd / "css/energie.css").read_text(encoding="utf-8")
            + "</style>" + (sd / "html/energie.html").read_text(encoding="utf-8") + "<script>" + js + "</script>")


def serveur(page, donnees, direct):
    posts = []

    class Gestion(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def envoie(self, code, mime, corps):
            corps = corps.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)

        def do_GET(self):
            u = urlparse(self.path)
            q = dict(parse_qsl(u.query))
            if u.path == "/capture":
                return self.envoie(200, "text/html; charset=utf-8", "<!doctype html><body style='margin:0'><iframe src='/energie' width='340' height='1300' style='border:0'></iframe>")
            if u.path != "/energie":
                return self.envoie(404, "text/plain", "?")
            if q.get("f") == "donnees":
                return self.envoie(200, "application/json", json.dumps(donnees))
            if q.get("f") == "direct":
                return self.envoie(200, "application/json", json.dumps(direct))
            self.envoie(200, "text/html; charset=utf-8", page)

        def do_POST(self):
            longueur = int(self.headers.get("Content-Length", 0))
            posts.append(dict(parse_qsl(self.rfile.read(longueur).decode("utf-8"))))
            self.envoie(200, "application/json", '{"ok":true}')

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Gestion)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, posts


def attribut(dom, ident, nom):
    m = re.search(r'id="%s"[^>]*\s%s="([^"]*)"' % (ident, nom), dom) or re.search(r'%s="([^"]*)"[^>]*\sid="%s"' % (nom, ident), dom)
    return html.unescape(m.group(1)) if m else None


def texte(dom, ident):
    m = re.search(r'id="%s"[^>]*>([^<]*)<' % ident, dom)
    return html.unescape(m.group(1)) if m else None


def juge(nom, attendu, obtenu):
    ok = attendu == obtenu
    print(f"  {'OK   ' if ok else 'ECHEC'} {nom}" + ("" if ok else f" : attendu {attendu!r}, obtenu {obtenu!r}"))
    return ok


def scenario(nav, tmp, nom, page, donnees, direct):
    srv, posts = serveur(page, donnees, direct)
    dom = rend(nav, f"http://127.0.0.1:{srv.server_address[1]}/energie", str(tmp / f"profil_{nom}"))
    srv.shutdown()
    return re.sub(r"<script\b[^>]*>.*?</script>", "", dom, flags=re.S), posts


def complet(base):
    """Donnees du vrai module, completees pour tracer les trois graphiques."""
    d = json.loads(json.dumps(base))
    e = d["etat"]
    e["h"] = [100 + i for i in range(24)]
    e["he"] = [20 + i for i in range(24)]
    e["d"] = [1000 * (i + 1) for i in range(31)]
    e["de"] = [200 * (i + 1) for i in range(31)]
    e["a"] = [[f"2025-{m:02d}", m * 10000, m * 2000] for m in range(1, 13)] + [["2026-11", 5000, 1000]]
    d["wCourant"] = e["w"]
    d["courbe"] = [None] * 100 + [200 + (i * 37) % 900 for i in range(188)]
    return d


def partie_rendu(nav, tmp, base, garde):
    ok = True
    d = complet(base)
    e = d["etat"]
    direct = {"p": 750, "i": 3.25, "f": 0.87, "hz": 50}
    print("--- Rendu : donnees completes")
    dom, _ = scenario(nav, tmp, "normal", page_html(), d, direct)
    ok &= juge("barres des heures = heures servies", e["h"], json.loads(attribut(dom, "e_h", "data-valeurs") or "null"))
    ok &= juge("novembre : 30 jours", e["d"][:30], json.loads(attribut(dom, "e_d", "data-valeurs") or "null"))
    ok &= juge("12 derniers mois seulement", [m[1] for m in e["a"][-12:]], json.loads(attribut(dom, "e_a", "data-valeurs") or "null"))
    ok &= juge("courbe = points servis", d["courbe"], json.loads(attribut(dom, "e_c", "data-valeurs") or "null"))
    ok &= juge("total du jour (Wh)", str(sum(e["h"])), attribut(dom, "e_totalH", "data-wh"))
    ok &= juge("cout du mois (dix-milliemes)", str(sum(e["de"])), attribut(dom, "e_totalD", "data-euros"))
    ok &= juge("puissance", "750", texte(dom, "e_p"))
    ok &= juge("courant : 3 decimales comme la carte", "3,250", texte(dom, "e_i"))
    ok &= juge("facteur", "0,87", texte(dom, "e_f"))
    ok &= juge("arc du facteur", "87 100", attribut(dom, "e_arc", "stroke-dasharray"))
    ok &= juge("frequence : entiere comme la carte", "50", texte(dom, "e_hz"))
    ok &= juge("prix affiche", "Prix : 0,2000 €/kWh depuis le 2026-11-01", texte(dom, "e_prixActuel"))
    ok &= juge("prix recent : pas de rappel", True, bool(re.search(r'id="e_rappel"[^>]*hidden', dom)))

    print("--- Rendu : petite consommation (Yesterday 0,002 kWh releve sur la carte le 2026-11-02)")
    petit = complet(base)
    petit["etat"]["h"] = [0] * 24
    petit["etat"]["he"] = [0] * 24
    petit["etat"]["h"][7] = 2
    petit["etat"]["he"][7] = 4
    petit["courbe"] = [None] * 287 + [12]
    dom, _ = scenario(nav, tmp, "petit", page_html(), petit, {"p": 0, "i": 0, "f": 0, "hz": 50})
    ok &= juge("total en Wh et euros fins", "2 Wh · 0,0004 €", texte(dom, "e_totalH"))
    ok &= juge("courant nul", "0,000", texte(dom, "e_i"))
    ok &= juge("puissance comme l'accueil", "0", texte(dom, "e_p"))
    ok &= juge("facteur comme l'accueil", "0,00", texte(dom, "e_f"))
    ok &= juge("frequence comme l'accueil", "50", texte(dom, "e_hz"))
    ok &= juge("point isole dessine", True, bool(re.search(r"class=.e_ligne. d=.M320\.0 [0-9.]+h0", dom)))

    print("--- Rendu : heure en cours ajoutee, comme « Energie aujourd'hui » de l'accueil")
    cours = complet(base)
    c = cours["etat"]
    c["h"], c["he"], c["d"], c["de"] = [0] * 24, [0] * 24, [0] * 31, [0] * 31
    c["a"] = [["2026-11", 0, 0]]
    c["h"][10] = 300
    c["d"][1] = 300
    c["l"] = 1793577600 + 11 * 3600          # note de 11 h, le 2 novembre 2026 en heure locale
    c["j"] = "2026-11-02"
    cours["wCourant"] = c["w"] + 150
    dom, _ = scenario(nav, tmp, "cours", page_html(), cours, direct)
    ok &= juge("barre de l'heure en cours", 150, (json.loads(attribut(dom, "e_h", "data-valeurs") or "[0]*24") + [0] * 24)[11])
    ok &= juge("total du jour = Today", "450", attribut(dom, "e_totalH", "data-wh"))
    ok &= juge("total du mois", "450", attribut(dom, "e_totalD", "data-wh"))
    cours["wCourant"] = c["w"] - 5
    dom, _ = scenario(nav, tmp, "cours2", page_html(), cours, direct)
    ok &= juge("compteur en baisse : rien ajoute", "300", attribut(dom, "e_totalH", "data-wh"))

    print("--- Rendu : prix de plus de 6 mois")
    vieux = complet(base)
    vieux["prix"] = [["2026-01-01", 1500]]
    dom, _ = scenario(nav, tmp, "vieux", page_html(), vieux, direct)
    ok &= juge("rappel", "Le prix a plus de 6 mois : vérifiez votre tarif.", texte(dom, "e_rappel"))
    ok &= juge("rappel visible", False, bool(re.search(r'id="e_rappel"[^>]*hidden', dom)))

    print("--- Rendu : carte neuve")
    neuf = {"aujourdhui": base["aujourdhui"], "etat": None, "prix": [], "courbe": [None] * 288}
    dom, _ = scenario(nav, tmp, "neuf", page_html(), neuf, {"p": None, "i": None, "f": None, "hz": None})
    ok &= juge("message", True, "Aucun relevé" in (texte(dom, "e_msg") or ""))
    ok &= juge("sans prix", "Aucun prix saisi : les coûts ne sont pas calculés.", texte(dom, "e_prixActuel"))
    ok &= juge("mesure absente", "--", texte(dom, "e_p"))

    print("--- Rendu : saisie d'un prix")
    envoi = "<script>setTimeout(function(){e_montant.value='0.2316';e_date.value='2026-12-01';e_form.dispatchEvent(new Event('submit',{cancelable:true}));},500);</script>"
    _, posts = scenario(nav, tmp, "post", page_html() + envoi, d, direct)
    ok &= juge("POST du prix", [{"jour": "2026-12-01", "prix": "0.2316"}], posts)

    print("--- Temoin du rendu (doit etre rouge)")
    js = (RACINE / "data/sd/js/energie.js").read_text(encoding="utf-8")
    assert "barres('e_h', e.h," in js
    dom, _ = scenario(nav, tmp, "temoin", page_html(js.replace("barres('e_h', e.h,", "barres('e_h', e.he,")), d, direct)
    rouge = json.loads(attribut(dom, "e_h", "data-valeurs") or "null") != e["h"]
    print(f"  {'OK   ' if rouge else 'ECHEC'} barres des euros au lieu des kWh")
    ok &= rouge

    if garde:
        Path(garde).mkdir(parents=True, exist_ok=True)
        srv, _ = serveur(page_html(), d, direct)
        cible = Path(garde) / "energie_340.png"
        subprocess.run([nav, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={tmp / 'profil_capture'}",
                        "--virtual-time-budget=3000", "--window-size=560,1320", f"--screenshot={cible}",
                        f"http://127.0.0.1:{srv.server_address[1]}/capture"], capture_output=True, timeout=60)
        srv.shutdown()
        print(f"  capture : {cible}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sans-navigateur", action="store_true")
    ap.add_argument("--garde")
    args = ap.parse_args()
    tmp = Path(tempfile.mkdtemp(prefix="banc_energie_"))
    try:
        ok, donnees = partie_berry(tmp)
        if not args.sans_navigateur:
            nav = trouve_navigateur()
            if nav is None:
                print("ECHEC : aucun navigateur, rendu non verifie")
                ok = False
            else:
                ok = partie_rendu(nav, tmp, donnees, args.garde) and ok
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("BANC_ENERGIE_COMPLET: " + ("OK" if ok else "ECHEC"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
