"""Banc du testeur UDP, groupe « pont » : liaison par le VRAI pont_serie.py (lance sur un port TCP libre,
port serie loop://). Appele par test_testeur_udp.py, qui fournit verifie() et attend() (un seul decompte)."""

import os
import sys
import time

import testeur_udp_carte as tc


# ====================================================================== pont serie
def groupe_pont(verifie, attend):
    """Liaison par le VRAI pont_serie.py (port loop:// : ce qui est ecrit revient), sur un port TCP libre."""
    import socket
    import subprocess
    import urllib.request

    def port_libre():
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        p = s.getsockname()[1]
        s.close()
        return p

    absent = port_libre()
    lignes, ouvertures = [], []
    carte = tc.Carte("esclave", 115200, tc.Masque(), lambda r, t, h: lignes.append(t),
                     lambda r, re_: ouvertures.append(re_), lambda r: None, lambda r, t: None)
    ok, message = carte.ouvre(f"pont:{absent}", 115200)
    verifie((ok, "demarrez le script « pont serie »" in message, f"--tcp {absent}" in message), (False, True, True),
            "pont absent : avertissement « demarrez le script pont serie »")
    verifie(tc.message_ouverture_echouee("COM4", OSError("PermissionError(13, 'Acces refuse.')")).count("Pont serie"), 1,
            "port COM occupe : propose le pont serie")

    tcp = port_libre()
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pont_serie.py")
    # --local --sans-navigateur (acces_web) : pas d'onglet ouvert a chaque banc, pont jamais expose au reseau
    pont = subprocess.Popen([sys.executable, script, "--port", "aucun", "--tcp", str(tcp), "--sans-couleurs",
                             "--local", "--sans-navigateur"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        def pret():
            try:
                return tc.etat_pont(tcp, 0.3) is not None
            except tc.PontIndisponible:
                return False
        verifie(attend(pret, 15), True, "pont serie demarre (banc)")
        ok, message = carte.ouvre(f"pont:{tcp}", 115200)
        verifie((ok, "port COM est ferme" in message, "Demarrer" in message), (False, True, True),
                "pont present, port COM ferme : « cliquez Demarrer »")
        sauve = (tc.PONTS_CHERCHES, tc.PONTS_PROPOSES)
        tc.PONTS_CHERCHES, tc.PONTS_PROPOSES = [tcp, absent], (absent,)
        liste = {p["port"]: p["description"] for p in tc.liste_ponts()}
        tc.PONTS_CHERCHES, tc.PONTS_PROPOSES = sauve
        verifie((f"pont:{tcp}" in liste, "port COM ferme" in liste.get(f"pont:{tcp}", ""),
                 "pas demarre" in liste.get(f"pont:{absent}", "")), (True, True, True),
                "liste des ponts : present (port COM ferme) et propose (pas demarre)")

        verifie(tc.demande_ouverture_pont(tcp, "loop://", 115200), True, "le pont ouvre son port sur demande")
        ok, message = carte.ouvre(f"pont:{tcp}", 115200)
        verifie((ok, "connecte au pont serie" in message), (True, True), "connexion par le pont")
        carte.ecrit("TESTPONT-1 aller-retour")
        verifie(attend(lambda: "TESTPONT-1 aller-retour" in lignes), True, "ligne ecrite par le pont, relue par le pont")

        # Bouton Arreter du pont (flash) : la liaison se coupe et le testeur NE redemande PAS le port
        requete = urllib.request.Request(f"http://127.0.0.1:{tcp}/fermer", data=b"", method="POST", headers={"X-Pont": "1"})
        urllib.request.urlopen(requete, timeout=2).close()
        verifie(attend(lambda: not carte.ouvert, 4), True, "Arreter sur le pont : liaison coupee")
        time.sleep(2.5)
        verifie((carte.ouvert, tc.etat_pont(tcp)["ouvert"]), (False, False),
                "TEMOIN apres Arreter : port COM jamais redemande au pont")
        # Carte perdue (redemarrage) annoncee par le pont : le testeur redemande le port, la liaison revient
        n = len(ouvertures)
        carte._annonce_pont("[pont] port loop:// perdu (carte debranchee ?) : port ferme")
        verifie(attend(lambda: carte.ouvert and len(ouvertures) > n, 6), True,
                "carte perdue : port redemande au pont, liaison retablie")
        verifie((ouvertures[-1], carte.pont_relance), (True, None), "reprise signalee comme reouverture, relance soldee")
    finally:
        carte.arrete()
        pont.terminate()
        pont.wait(5)
