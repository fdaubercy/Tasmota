"""Banc de etiquettes_qr_suivi (plan etiquettes-qrcode A7) : etats d'une etiquette et de la page de la carte. Code 0 = vert.

Copie temporaire du depot (test_etiquettes_qr_ecriture.copie) : le vrai depot n'est jamais ecrit. La carte est simulee par
`get` (fonction rendue par le banc) ; la carte muette est un vrai socket qui accepte sans jamais repondre.
"""

import dataclasses
import json
import socket
import sys
import tempfile
import time
from pathlib import Path

import build_envs
import etiquettes_qr_ecriture as eqe
import etiquettes_qr_suivi as suivi
import fichiers_berry_etat as fbe
import test_etiquettes_qr_ecriture as tqe

CUVE = tqe.CUVE
ECHECS = []
REGLAGE = {"lignes": [{"source": "standard", "cle": "hostname", "libelle": "Hostname"}], "entre_lignes": " · "}


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def change_persist(racine, cle, valeur):
    chemin = racine / fbe.dossier_carte(CUVE) / "_persist.json"
    p = json.loads(chemin.read_text(encoding="utf-8"))
    bloc = p["serveur"]
    for c in cle[:-1]:
        bloc = bloc.setdefault(c, {})
    bloc[cle[-1]] = valeur
    chemin.write_text(json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")


def carte_qui_rend(octets, code=200):
    vus = []

    def get(url, entetes, delai):
        vus.append((url, entetes.get("Referer"), delai))
        return code, octets
    return get, vus


def principal():
    with tempfile.TemporaryDirectory(prefix="banc_qr_suivi_") as t:
        racine = tqe.copie(t)
        tqe.fichiers_page(racine)
        envs = build_envs.liste_envs(racine)
        ip = next(e for e in envs if e.nom == CUVE).ip

        e = suivi.etats(racine, CUVE, envs=envs, get=carte_qui_rend(b"")[0])
        verifie((e["a_reimprimer"], e["a_regenerer"], e["carte"]), (False, False, "sans_page"),
                "sans page ni impression : rien a refaire, carte non interrogee")

        # reglage complet (gabarit fusionne), comme la page l'envoie apres GET /reglage
        tqe.ecrit(racine, CUVE, suivi.modele.fusionne(suivi.modele.charge_gabarit(racine), REGLAGE), True)
        depot = (racine / fbe.dossier_carte(CUVE) / eqe.FICHIER_CARTE).read_bytes()
        texte = json.loads(depot)["texte"]
        eqe.note_impression(racine, {CUVE: texte}, 25)
        get, vus = carte_qui_rend(depot)
        e = suivi.etats(racine, CUVE, envs=envs, get=get)
        verifie((e["a_reimprimer"], e["a_regenerer"], e["carte"]), (False, False, "a_jour"),
                "page ecrite, imprimee, carte qui rend le meme qrcode.json : a jour")
        verifie(vus[0], (f"http://{ip}/qrcode?f=reglage", f"http://{ip}/", 2),
                "carte lue sur /qrcode?f=reglage, Referer de la carte (acces privilegie), delai 2 s")

        get, vus = carte_qui_rend(depot)
        e = suivi.etats(racine, CUVE, envs=envs, get=get, interroger=False)
        verifie((e["carte"], vus), (None, []), "interroger=False (badges de la liste) : carte non interrogee")
        e = suivi.etats(racine, CUVE, envs=envs, get=carte_qui_rend(depot.replace(b"version", b"versioN"))[0])
        verifie(e["carte"], "a_mettre_a_jour", "carte qui rend un autre qrcode.json : a mettre a jour")
        e = suivi.etats(racine, CUVE, envs=envs, get=carte_qui_rend(b"absent", 404)[0])
        verifie(e["carte"], "a_mettre_a_jour", "carte sans la page (404) : a mettre a jour")

        change_persist(racine, ("mqtt", "topic"), "autre-topic")
        e = suivi.etats(racine, CUVE, envs=envs, get=carte_qui_rend(depot)[0])
        verifie((e["a_reimprimer"], e["a_regenerer"]), (False, False), "topic change, absent du reglage : rien a refaire")

        change_persist(racine, ("hostname",), "CUVE-NEUVE")
        e = suivi.etats(racine, CUVE, envs=envs, get=carte_qui_rend(depot)[0])
        verifie((e["a_reimprimer"], e["a_regenerer"], e["carte"]), (True, True, "a_jour"),
                "hostname change : etiquette a reimprimer, qrcode.json a regenerer (la carte a encore l'ancien, a jour du depot)")

        s = socket.socket()                                  # carte muette : accepte la connexion, ne repond jamais
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        muette = [dataclasses.replace(x, ip=f"127.0.0.1:{s.getsockname()[1]}") if x.nom == CUVE else x for x in envs]
        debut = time.monotonic()
        e = suivi.etats(racine, CUVE, envs=muette)
        duree = time.monotonic() - debut
        s.close()
        verifie((e["carte"], duree < 3), ("inconnu", True), f"carte muette : inconnu en {duree:.1f} s (moins de 3 s)")
        sans_ip = [dataclasses.replace(x, ip="") if x.nom == CUVE else x for x in envs]
        verifie(suivi.etats(racine, CUVE, envs=sans_ip)["carte"], "inconnu", "carte sans adresse connue : inconnu")

        verifie(suivi.lien_si_regle(racine, CUVE), f"http://127.0.0.1:7970/?env={CUVE}", "lien vers la page 7970 d'un env regle")
        verifie(suivi.lien_si_regle(racine, tqe.TV), None, "env jamais regle : pas de lien")
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
