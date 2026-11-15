"""Banc de genere_plan_maison.py : derivation des liens, avertissements, page generee. Code de sortie 0 = vert.
Usage : python outils_docs/plan_maison/test_plan_maison.py"""
import contextlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import genere_plan_maison as g  # noqa: E402

ECHECS = []


def verifie(nom, ok):
    print(("OK   " if ok else "ECHEC"), nom)
    if not ok:
        ECHECS.append(nom)


def info(ip="", re_on=False, re_id=None, ip_maitre="", serie=False, udp=False, mb=False, mb_id=None):
    return {"hote": "", "topic": "", "ip": ip, "mb": mb, "mb_id": mb_id, "serie": serie, "udp": udp, "re": re_on,
            "re_id": re_id, "ip_maitre": ip_maitre, "mqtt": True, "mqtt_hote": "1.2.3.4:1883", "persist": True}


def derive(conf, infos):
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        r = g.derive(conf, infos)
    return r, err.getvalue()


M, E1, E2 = "a/m", "a/e1", "a/e2"
infos = {M: info("10.0.0.1", True, 0, serie=True, udp=True, mb=True, mb_id=0),
         E1: info("", True, 1, "10.0.0.1", serie=True, udp=True),
         E2: info("", True, 2, "10.0.0.1", udp=True)}
(liens, maitres, esclaves), av = derive({}, infos)
verifie("un maitre", maitres == {M})
verifie("deux esclaves avec leur id", esclaves == {E1: 1, E2: 2})
verifie("E1 : serie et udp", {(x["type"], x["vers"]) for x in liens} >= {("serie", E1), ("udp", E1)})
verifie("E2 : udp seul, pas de serie (maitre ou esclave sans Serial)", [x["type"] for x in liens if x["vers"] == E2] == ["udp"])
verifie("aucun avertissement sur le cas sain", av == "")

# temoin negatif : IP portee par deux cartes sans arbitrage -> avertissement et pas de lien ; avec ip_cartes -> lien
dbl = {**infos, "a/m2": info("10.0.0.1", True, 0, serie=True, udp=True)}
(l2, _, _), av2 = derive({}, dbl)
verifie("IP double sans arbitrage : avertissement", "IP 10.0.0.1" in av2 and "ambigu" in av2)
verifie("IP double sans arbitrage : aucun lien", l2 == [])
(l3, m3, _), av3 = derive({"ip_cartes": {"10.0.0.1": M}}, dbl)
verifie("IP double arbitree : liens derives", len(l3) == 3 and m3 == {M} and "ambigu" not in av3)

# maitre introuvable
(l4, _, _), av4 = derive({}, {E1: info("", True, 1, "9.9.9.9", serie=True)})
verifie("maitre introuvable : avertissement", "introuvable" in av4 and l4 == [])
# carte qui se designe elle-meme comme maitre : ignoree
(l5, _, e5), _ = derive({}, {M: info("10.0.0.1", True, 0, ip_maitre="10.0.0.1", serie=True)})
verifie("auto-reference ignoree", l5 == [] and e5 == {})
# lien manuel
(l6, m6, e6), _ = derive({"liens_manuels": [{"type": "udp", "de": "x/m", "vers": "x/e"}]}, {})
verifie("lien manuel", len(l6) == 1 and m6 == {"x/m"} and "x/e" in e6)

# Wi-Fi : principal/secours, appareil par SSID, Range Extender par SSID '<hote>-GATEWAY', SSID inconnu ignore, hote ambigu signale
def wi(ssids, hote=""):
    return {**info(), "ssids": ssids, "hote": hote}


cw = {"wifi": {"appareils": {"fb": {"ssid": ["MAISON"]}, "rp": {"ssid": ["REP"]}}}}
winf = {"m": wi(["MAISON", "REP"], "SRV"), "e": wi(["SRV-GATEWAY", "MAISON"], "ESC"), "t": wi(["iPhone", "MAISON"], "TEL")}
err = io.StringIO()
with contextlib.redirect_stderr(err):
    w = g.derive_wifi(cw, winf)
vue = {(x["kind"], x["rang"], x["de"], x["vers"]) for x in w}
verifie("wifi : principal vers l'appareil du SSID", ("ap", 0, "ap:fb", "m") in vue and ("ap", 1, "ap:rp", "m") in vue)
verifie("wifi : esclave sur le Range Extender du maitre, secours sur la box", ("re", 0, "m", "e") in vue and ("ap", 1, "ap:fb", "e") in vue)
verifie("wifi : SSID inconnu (telephone) ignore", not any(x[3] == "t" and x[1] == 0 for x in vue) and ("ap", 1, "ap:fb", "t") in vue)
with contextlib.redirect_stderr(err):
    w2 = g.derive_wifi(cw, {**winf, "m2": wi([], "SRV")})
verifie("wifi : hote ambigu -> avertissement, pas de lien RE", "ambigu" in err.getvalue() and not any(x["kind"] == "re" for x in w2))
with contextlib.redirect_stderr(err):
    w3 = g.derive_wifi({**cw, "wifi": {**cw["wifi"], "re_hotes": {"SRV": "m"}}}, {**winf, "m2": wi([], "SRV")})
verifie("wifi : re_hotes tranche l'ambiguite", any(x["kind"] == "re" and x["de"] == "m" for x in w3))
with contextlib.redirect_stderr(err):
    w4 = g.derive_wifi({**cw, "wifi": {**cw["wifi"], "wifi_manuel": {"t": {"principal": "rp"}}}}, winf)
verifie("wifi : wifi_manuel corrige", ("ap", 0, "ap:rp", "t") in {(x["kind"], x["rang"], x["de"], x["vers"]) for x in w4})

# page reelle : generee sans avertissement, une pastille par carte, chaque lien dans les deux vues coherentes
r = subprocess.run([sys.executable, str(ICI / "genere_plan_maison.py")], capture_output=True, text=True, encoding="utf-8",
                   env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
verifie("generation reelle : code 0", r.returncode == 0)
verifie("generation reelle : aucun avertissement", r.stderr.strip() == "")
page = (ICI / "plan_maison.html").read_text(encoding="utf-8")
m = re.search(r"(\d+) cartes, (\d+) traits de lien", r.stdout)
n_cartes, n_liens = int(m.group(1)), int(m.group(2))
verifie("une pastille par carte dans chaque vue", page.count('class="carte') >= 2 * n_cartes and page.count('data-id="') >= 2 * n_cartes)
verifie("les titres d etage en gras", all(f'class="titreetage"' in page and t in page for t in ("2e étage", "1er étage", "Rez-de-chaussée", "Cave")))
verifie("liens du plan = traits annonces", len(re.findall(r'<g class="lien (?:serie|udp)', page.split('<svg class="reseau"')[0])) == n_liens)
verifie("pas de mot de passe dans la page", not re.search(r"mdp|password|passwd", page, re.I))
verifie("fiches : echappement de </", "</script" not in page.split("const F=")[1].split(",$=")[0])

pl = json.loads((ICI / "placement.json").read_text(encoding="utf-8"))["chauffage"]["departs"]
verifie("chauffage : six debits numerotes 1 a 6", sorted(d["debit"] for d in pl) == [1, 2, 3, 4, 5, 6])
verifie("chauffage : un rond numerote par depart et par piece", page.count('class="dn"') == sum(len(d["pieces"]) for d in pl))

print("\n%d echec(s)" % len(ECHECS))
sys.exit(1 if ECHECS else 0)
