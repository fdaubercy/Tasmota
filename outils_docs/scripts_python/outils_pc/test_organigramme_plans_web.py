"""Banc de la page « Organigramme des plans » : routes, publication refusee sans en-tete (la vraie publication n'est jamais lancee), Host hostile refuse, donnees des plans.

Lancement : python test_organigramme_plans_web.py   (code 0 = vert). Python de PlatformIO non requis.
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import http.client
import re
import socket
import sys
import tempfile
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
        # alerte de retard : la page « en ligne » est simulee (aucun acces reseau), temoin = un plan dont le % change
        import json
        import organigramme_plans as org
        d = org.donnees()
        en_ligne = org.page_html(d)
        import etiquettes_qr_publication as pub
        vrai = (pub._pointe, pub._publies)
        try:
            pub._pointe = lambda racine: "x"
            pub._publies = lambda racine, pointe: {"organigramme.html": en_ligne}
            verifie(org.retard_publication(), {"n": 0, "noms": []}, "retard : page identique -> 0")
            d["plans"][0]["pct"] = (d["plans"][0]["pct"] + 7) % 100
            pub._publies = lambda racine, pointe: {"organigramme.html": org.page_html(d)}
            r = org.retard_publication()
            verifie((r["n"], r["noms"]), (1, [d["plans"][0]["nom"]]), "retard : TEMOIN un plan different -> 1, nomme")
            pub._publies = lambda racine, pointe: {}
            verifie(org.retard_publication(), None, "retard : rien en ligne -> None (pas de bandeau)")
        finally:
            pub._pointe, pub._publies = vrai
        statut, corps = requete(port, "GET", "/retard")
        verifie(statut, 200, "GET /retard : 200")
        json.loads(corps)
        # avancement = celui du parseur des plans : A1b compte, Ameliorations et blocs de code non (ici 60 % si tout est compte)
        with tempfile.TemporaryDirectory() as depot:
            (Path(depot) / "tasks" / "plans").mkdir(parents=True)
            (Path(depot) / "tasks" / "plans" / "essai.md").write_text(
                "---\nstatut: actif\nfamille: build\ncree: 2026-01-01\n---\n# T\n## A1 — a\n- [x] x\n## A1b — b\n- [x] y\n"
                "- [ ] z\n## Améliorations restantes\n- [ ] plus tard\n```\n- [x] exemple\n```\n", encoding="utf-8")
            racine = org.RACINE
            try:
                org.RACINE = depot
                p = org.donnees()["plans"][0]
            finally:
                org.RACINE = racine
            verifie((p["pct"], p["etapes"]), (75, "2/3"), "avancement : meme calcul que le parseur des plans")
        parseur, message = org.PARSEUR, "aucune exception"
        try:
            org.PARSEUR = parseur + ".absent"
            org.avancements(["# T\n"])
        except RuntimeError as e:
            message = str(e)
        finally:
            org.PARSEUR = parseur
        verifie("Cannot find module" in message, True, "parseur absent : erreur levee, cause lisible (pas de calcul de repli)")
    finally:
        serveur.shutdown()
        serveur.server_close()
    print("\n%s" % ("VERT" if not echecs else "ROUGE : " + ", ".join(echecs)))
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
