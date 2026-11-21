"""Banc de sonde_hermetique.py (neutralise la barre commune de acces_web.habille dans une sonde Chrome). Code de sortie 0 = vert.

Faux dossier de donnees (OUTILS_TASMOTA_DOSSIER) avec une fiche de presence vivante (ce processus) qui pointe vers un espion HTTP local :
avant, la barre lit la fiche et interroge l'espion ; apres neutralise_barre(), elle rend [] sans aucune requete ; restaure() remet l'etat.
Temoin : retirer une seule des trois lignes de neutralise_barre() fait passer ce banc au rouge.
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()

import json
import os
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

ECHECS = []


def verifie(obtenu, attendu, libelle):
    if obtenu != attendu:
        ECHECS.append(libelle)
        print(f"  ECHEC {libelle} : obtenu {obtenu!r}, attendu {attendu!r}", flush=True)
    else:
        print(f"  ok {libelle}", flush=True)


class Espion(BaseHTTPRequestHandler):
    vus = []

    def do_GET(self):
        Espion.vus.append(self.path)
        corps = b'{"en_cours": true}'
        self.send_response(200)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def log_message(self, *a):
        pass


def main():
    t = Path(tempfile.mkdtemp(prefix="sonde_hermetique_"))
    os.environ["OUTILS_TASMOTA_DOSSIER"] = str(t)
    serveur = ThreadingHTTPServer(("127.0.0.1", 0), Espion)
    Thread(target=serveur.serve_forever, daemon=True).start()
    try:
        import acces_barre
        import annuaire_registre as reg
        outil = next(o for o in reg.OUTILS if o.route_occupe)
        presence = t / "presence"
        presence.mkdir()
        (presence / "x.json").write_text(json.dumps({"nom": outil.nom_acces, "port": serveur.server_port, "pid": os.getpid()}), encoding="utf-8")

        print("Avant : la barre lit les fiches et interroge l'outil", flush=True)
        verifie([o["id"] for o in acces_barre.outils_vivants()], [outil.id], "avant : la fiche est lue")
        verifie(len(Espion.vus), 1, "avant : une requete vers l'outil")

        import sonde_hermetique
        acces_barre._CACHE["donnees"] = '{"outils": ["perime"]}'
        acces_barre._CACHE["t"] = 10 ** 12   # cache neuf aux yeux de barre_json
        origine = (acces_barre.outils_vivants, acces_barre._occupe, dict(acces_barre._CACHE))
        restaure = sonde_hermetique.neutralise_barre()
        Espion.vus.clear()
        print("Apres neutralise_barre()", flush=True)
        verifie(acces_barre.outils_vivants(), [], "apres : outils_vivants rend []")
        verifie(acces_barre._occupe(serveur.server_port, "/execution"), False, "apres : _occupe rend False")
        verifie(json.loads(acces_barre.barre_json()), {"outils": []}, "apres : /_barre.json vide (cache purge)")
        verifie(Espion.vus, [], "apres : aucune requete reseau")

        print("Apres restaure()", flush=True)
        restaure()
        verifie(acces_barre.outils_vivants is origine[0], True, "restaure : outils_vivants d'origine")
        verifie(acces_barre._occupe is origine[1], True, "restaure : _occupe d'origine")
        verifie(acces_barre._CACHE, origine[2], "restaure : cache d'origine")
        verifie([o["id"] for o in acces_barre.outils_vivants()], [outil.id], "restaure : la fiche est de nouveau lue")
    finally:
        serveur.shutdown()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)", flush=True)
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    _sys.exit(main())
