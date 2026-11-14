"""Banc des cartes simulees (plan tasks/plans/cartes-simulees.md) : identite reseau fidele au persist, routes Berry reelles, refus.

UTILISATION
    python outils_docs/scripts_python/outils_pc/test_cartes_simulees.py     (code de sortie 0 = vert ; berry.exe requis ; aucun reseau)
Les valeurs attendues sont relues dans le persist par une lecture BRUTE du texte (regex), pas par le code teste.
Temoin negatif : un persist modifie (hote change) doit changer la reponse ; sinon le banc ne prouve rien.
"""
import json
import re
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cartes_simulees as cs  # noqa: E402
import cartes_simulees_reseau as reseau  # noqa: E402

ENV = "tasmota32s3-garage-rideau-garage-modbus"
DOSSIER = cs.RACINE / "data" / "garage" / "tasmota32s3-rideau-garage-modbus"
ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)


def brut(texte, cle):
    """Premiere valeur texte de \"cle\": \"...\" dans le persist, lue sans le JSON."""
    m = re.search(r'"' + cle + r'"\s*:\s*"([^"]*)"', texte)
    return m.group(1) if m else None


def get(port, chemin):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{chemin}", timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def main():
    texte = (DOSSIER / "_persist.json").read_text(encoding="utf-8")
    p = reseau.profil(DOSSIER)
    print("1. Profil reseau = persist")
    verifie(p["hostname"], brut(texte, "hostname"), "nom d'hote")
    verifie(p["ip"], brut(texte, "IPAddress"), "IP du persist (0.0.0.0 = DHCP, signale)")
    verifie(p["dhcp"], True, "IP 0.0.0.0 reconnue comme DHCP")
    verifie(p["passerelle"], brut(texte, "IPGateway"), "passerelle")
    verifie(p["masque"], brut(texte, "Subnet"), "masque")
    verifie(p["dns"], brut(texte, "DNSServer"), "DNS")
    verifie(p["mqtt"]["topic"], brut(texte, "topic"), "topic MQTT")
    verifie(p["mqtt"]["client"], brut(texte, "client"), "client MQTT")
    verifie(p["ip_maitre"], brut(texte, "ipMaitre"), "IP du maitre")
    verifie(p["port_web"], 8080 + int(re.search(r'"rangeExtender".*?"id"\s*:\s*(\d+)', texte, re.S).group(1)) - 1, "port web = 8080 + id - 1")
    s5 = reseau.status5(p)["StatusNET"]
    verifie([s5["Hostname"], s5["Gateway"], s5["Subnetmask"], s5["DNSServer1"]], [p["hostname"], p["passerelle"], p["masque"], p["dns"]], "Status 5")

    print("2. Serveur : memes valeurs par HTTP, routes Berry reelles")
    srv = cs.serveur(ENV, 0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        c, corps = get(port, "/cm?cmnd=Status%205")
        verifie([c, json.loads(corps)["StatusNET"]["Hostname"]], [200, p["hostname"]], "/cm Status 5 : nom d'hote du persist")
        c, corps = get(port, "/cm?cmnd=Status%206")
        verifie(json.loads(corps)["StatusMQT"]["MqttClient"], p["mqtt"]["client"], "/cm Status 6 : client MQTT du persist (non connecte)")
        c, corps = get(port, "/cm?cmnd=Restart%201")
        verifie("Unknown" in corps, True, "/cm Restart : refuse, rien n'est execute")
        c, corps = get(port, "/")
        verifie([c, p["hostname"] in corps, "chevrefeuille" in corps, "CARTE SIMULEE" in corps], [200, True, True, True], "accueil : nom d'hote, decor, bandeau simule")
        c, corps = get(port, "/rideau?f=position&id=1")
        verifie(json.loads(corps).get("ouverture"), 70, "/rideau : curseur du P4 a 30 -> 70 %")
        verifie(get(port, "/sd/../../platformio.ini")[0], 404, "sortie de data/sd refusee")
        verifie(get(port, "/up")[0], 404, "page native du C++ : 404 net")
    finally:
        srv.shutdown()

    print("3. Temoin negatif : un persist modifie change la reponse")
    with tempfile.TemporaryDirectory() as tmp:
        copie = Path(tmp) / "carte"
        copie.mkdir()
        shutil.copy(DOSSIER / "_persist.json", copie / "_persist.json")
        t = (copie / "_persist.json").read_text(encoding="utf-8").replace(p["hostname"], "AUTRE-HOTE", 1)
        (copie / "_persist.json").write_text(t, encoding="utf-8")
        verifie(reseau.profil(copie)["hostname"], "AUTRE-HOTE", "le profil suit le persist (temoin)")
    print("4. Toutes les cartes du parc : identite du persist et accueil generique")
    inv = cs.liste()
    verifie(len(inv) >= 13, True, f"inventaire : {len(inv)} cartes avec persist")
    for c in inv:
        t = (cs.RACINE / c["dossier"] / "_persist.json").read_text(encoding="utf-8")
        pc = cs.profil_reseau(c["env"])
        verifie([pc["hostname"], pc["mqtt"]["topic"]], [brut(t, "hostname"), brut(t, "topic")], f"{c['env']} : hote et topic du persist")
        if not c["berry"]:
            verifie(pc["hostname"] in cs.accueil_generique(c["env"]), True, f"{c['env']} : accueil generique au nom d'hote")
    print("5. Rideau simule : position lue sur le P4 en ligne (faux P4 local, lecture seule)")
    from http.server import BaseHTTPRequestHandler, HTTPServer
    vus = []

    class FauxP4(BaseHTTPRequestHandler):
        def log_message(self, format, *args):  # noqa: A002
            pass

        def do_GET(self):
            vus.append(self.path)
            corps = json.dumps({"StatusSNS": {"Time": "x", "Shutter1": {"Position": 20, "Direction": 0, "Target": 20, "Tilt": 0}}}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(corps)))
            self.end_headers()
            self.wfile.write(corps)
    faux = HTTPServer(("127.0.0.1", 0), FauxP4)
    threading.Thread(target=faux.serve_forever, daemon=True).start()
    cs.SCENARIO["source_p4"] = "reel"
    cs.URL_MAITRE = f"http://127.0.0.1:{faux.server_address[1]}/cm?cmnd=Status%2010"
    srv = cs.serveur(ENV, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        c, corps = get(srv.server_address[1], "/rideau?f=position&id=1")
        verifie([json.loads(corps).get("ouverture"), json.loads(corps).get("muet")], [80, False], "P4 en ligne a 20 -> 80 % d'ouverture")
        verifie(vus, ["/cm?cmnd=Status%2010"], "une seule requete au P4 : Status 10 en lecture")
        faux.shutdown()
        faux.server_close()
        c, corps = get(srv.server_address[1], "/rideau?f=position&id=1")
        verifie(json.loads(corps).get("muet"), True, "P4 injoignable : rideau en mode « maitre muet »")
    finally:
        srv.shutdown()
        cs.SCENARIO["source_p4"] = "simule"
        cs.URL_MAITRE = None
    print("\n" + ("VERT" if not ECHECS else "ROUGE : " + "; ".join(ECHECS)))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
