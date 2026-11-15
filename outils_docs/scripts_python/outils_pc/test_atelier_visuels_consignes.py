#!/usr/bin/env python3
"""Banc des consignes de l'atelier des visuels (atelier_visuels_consignes.py, routes GET /consignes et /consignes/regles, plan atelier-visuels A7).

Verifie : lecture du VRAI fichier des consignes (organes, jour et nuit, commande par clic, organes par type de point chaud), fichier servi
octet pour octet, RELU A CHAQUE REQUETE (une regle ajoutee apparait sans relancer l'outil), organe inconnu ignore, fichier absent = 404,
acces refuse a un hote non local, aucune route d'ecriture, lien et panneau dans la page. Serveur reel sur 127.0.0.1 (port libre), depot temporaire.
Code 0 = vert.

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_atelier_visuels_consignes.py
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import http.client
import json
import sys
import tempfile
from pathlib import Path

import atelier_visuels_consignes as avc
import atelier_visuels_web as avw
from test_atelier_visuels_web import ECHECS, ENT, requete, serveur_sur, verifie

MINI = """# Consignes

## 4. Les organes et leurs règles (décisions de l'utilisateur)

| Organe | Règle |
|---|---|
| Feu orange | Clignote pendant tout mouvement. |
| Caméra | Voyant vert allumé. |

## 5. Commande par clic

- Portail : clic = impulsion.

## 6. Jour et nuit automatiques

- Source : la carte.
  suite de la puce.
"""


def main():
    # 1. Le vrai fichier
    r = avc.regles(avw.DEPOT)
    noms = [o["nom"] for o in r["organes"]]
    verifie(all(n in noms for n in ("Grande porte du garage", "Portail de jardin", "Capteur de fermeture", "Feu orange", "Lampe du garage", "Caméra")), True,
            "vrai fichier : les organes de la section 4 sont lus")
    verifie(all(o["regle"] for o in r["organes"]) and "Organe" not in noms and not any(set(n) <= {"-"} for n in noms), True, "vrai fichier : ni titre ni separateur du tableau parmi les organes")
    verifie((bool(r["jour_nuit"]), bool(r["clic"])), (True, True), "vrai fichier : puces du jour et de la nuit et de la commande par clic")
    verifie(set(r["par_type"]), {"voyant", "valeur", "liaison"}, "par_type : voyant, valeur, liaison")
    manquants = [n for ns in avc.PAR_TYPE.values() for n in ns if n not in noms]
    verifie(manquants, [], "PAR_TYPE : chaque organe cite existe dans le vrai fichier (un organe renomme dans le markdown ne disparait pas en silence)")

    with tempfile.TemporaryDirectory() as t:
        racine = Path(t)
        f = racine / avc.FICHIER
        f.parent.mkdir(parents=True)
        f.write_text(MINI, encoding="utf-8")
        srv, port = serveur_sur(racine)
        try:
            st, corps = requete(port, "GET", "/consignes")
            verifie((st, corps), (200, MINI.encode("utf-8")), "GET /consignes : le fichier, octet pour octet")
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            c.request("GET", "/consignes", headers={"Host": f"127.0.0.1:{port}"})
            rep = c.getresponse()
            verifie((rep.getheader("Content-Type"), rep.getheader("X-Content-Type-Options")), ("text/plain; charset=utf-8", "nosniff"), "GET /consignes : texte brut, nosniff")
            rep.read()
            c.close()
            st, corps = requete(port, "GET", "/consignes/regles")
            d = json.loads(corps)
            verifie((st, [o["nom"] for o in d["organes"]], d["jour_nuit"], d["clic"]), (200, ["Feu orange", "Caméra"], ["Source : la carte. suite de la puce."], ["Portail : clic = impulsion."]),
                    "GET /consignes/regles : organes, puces avec leur suite jointe")
            verifie(d["par_type"], {"voyant": ["Feu orange", "Caméra"], "valeur": [], "liaison": []}, "par_type : un organe absent du fichier est ignore")

            # Une regle ajoutee au fichier apparait a la requete suivante, sans relancer l'outil
            f.write_text(MINI.replace("| Caméra | Voyant vert allumé. |", "| Caméra | Voyant vert allumé. |\n| Capteur de fermeture | Anneau au joint central. |")
                         .replace("- Source : la carte.", "- Fondu de 35 min.\n- Source : la carte."), encoding="utf-8")
            d = json.loads(requete(port, "GET", "/consignes/regles")[1])
            verifie(([o["nom"] for o in d["organes"]], d["par_type"]["valeur"], d["jour_nuit"][0]), (["Feu orange", "Caméra", "Capteur de fermeture"], ["Capteur de fermeture"], "Fondu de 35 min."),
                    "regle ajoutee au fichier : visible sans relancer l'outil")
            verifie(b"Fondu de 35 min." in requete(port, "GET", "/consignes")[1], True, "regle ajoutee : visible aussi dans le fichier servi")

            # Acces et limites
            verifie(requete(port, "GET", "/consignes", hote="evil.example:80")[0], 403, "GET /consignes avec un hote non local : 403")
            verifie(requete(port, "GET", "/consignes/regles", hote="evil.example:80")[0], 403, "GET /consignes/regles avec un hote non local : 403")
            verifie(requete(port, "POST", "/consignes", b"x", ENT)[0] != 200, True, "aucune route d'ecriture : POST /consignes refuse")
            st, corps = requete(port, "GET", "/")
            verifie((st, b'href="/consignes"' in corps or b"href='/consignes'" in corps, b"avc-panel" in corps, b"avc-rappel" in corps), (200, True, True, True), "page : lien « Consignes » et panneau de rappel")
            verifie((corps.count(b"<div"), corps.count(b"</div>")) == (corps.count(b"</div>"),) * 2, True, "page : balises <div et </div> en nombre egal")

            f.unlink()
            verifie(requete(port, "GET", "/consignes")[0], 404, "fichier absent : GET /consignes 404")
            verifie(requete(port, "GET", "/consignes/regles")[0], 404, "fichier absent : GET /consignes/regles 404")
        finally:
            srv.shutdown()
            srv.server_close()
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
