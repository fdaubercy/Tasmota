"""Banc de la page « Organigramme des plans » : routes, publication refusee sans en-tete (la vraie publication n'est jamais lancee), Host hostile refuse, donnees des plans.

Lancement : python test_organigramme_plans_web.py   (code 0 = vert). Python de PlatformIO non requis.
"""
import http.client
import re
import socket
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import acces_web
import organigramme_plans_web as ow

echecs = []


def verifie(obtenu, attendu, nom):
    if obtenu != attendu:
        echecs.append(nom)
    print(("OK    " if obtenu == attendu else "ECHEC ") + nom + ("" if obtenu == attendu else f" : {obtenu!r} != {attendu!r}"))


def port_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def requete(port, methode, chemin, hote=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
    c.putrequest(methode, chemin, skip_host=True)
    c.putheader("Host", hote or f"127.0.0.1:{port}")
    c.putheader("Content-Length", "0")
    c.endheaders()
    r = c.getresponse()
    corps = r.read().decode("utf-8")
    c.close()
    return r.status, corps


def main():
    port = port_libre()
    acces = acces_web.Acces(port, True, "Organigramme des plans")
    serveur = ThreadingHTTPServer(("127.0.0.1", port), ow.fabrique_gestionnaire(acces))
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    try:
        statut, page = requete(port, "GET", "/")
        verifie(statut, 200, "GET / : 200")
        verifie("Organigramme des plans" in page, True, "GET / : titre")
        d = ow.org.donnees()
        verifie(len(d["plans"]) >= 40, True, "donnees : au moins 40 plans")
        verifie(all(p["famille"] in d["familles"] for p in d["plans"]), True, "donnees : toutes les familles connues")
        noms = {p["nom"] for p in d["plans"]}
        verifie([p["nom"] for p in d["plans"] if p["parent"] and p["parent"] not in noms], [], "donnees : parents existants")
        verifie([p["nom"] for p in d["plans"] if any(q not in noms for q in p["liens"])], [], "donnees : liens existants")
        verifie(all(re.match(r"\d{4}-\d\d-\d\d$", p["cree"]) and p["maj"] >= p["cree"] for p in d["plans"]), True, "donnees : dates")
        verifie(requete(port, "GET", "/autre")[0], 404, "GET /autre : 404")
        verifie(requete(port, "GET", "/", hote="evil.example")[0], 403, "Host hostile : 403")
        verifie("id='pub'" in page, True, "GET / : bouton de publication")
        verifie(requete(port, "POST", "/")[0], 403, "POST / : refuse")
        verifie(requete(port, "POST", "/publier")[0], 403, "POST /publier sans en-tete : refuse (rien publie)")
        verifie(requete(port, "POST", "/publier", hote="evil.example")[0], 403, "POST /publier, Host hostile : refuse")
    finally:
        serveur.shutdown()
        serveur.server_close()
    print("\n%s" % ("VERT" if not echecs else "ROUGE : " + ", ".join(echecs)))
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
