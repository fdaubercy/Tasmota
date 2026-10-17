"""Groupe « muette » du banc test_testeur_udp.py : carte qui ne repond plus sur son port serie.

Constate le 2026-10-17 sur la cuve (pont CH343, COM12) : plus une ligne de 16:39:11 a 16:47:09, alors que la
carte tournait (ImAlive UDP recu par le maitre a 16:44:26). Le port restait « ouvert » et les essais rendaient
NON EMIS / EMIS NON RECU, comme si l'UDP etait en cause. Fermer puis rouvrir le port n'a rien change ; seul un
reset de la carte l'a retablie. Le testeur doit le DIRE : carte « muette » apres SEUIL_MUETTE s sans reponse a
une commande, et un essai sans aucune ligne de la carte le signale au lieu d'accuser l'emission.
"""

import time

import testeur_udp_carte as tc


class SerieMuette:
    """Port ouvert qui accepte les ecritures et ne rend rien, jusqu'a ce que le test le fasse parler."""

    def __init__(self):
        self.a_dire = []

    def read(self, n):
        if self.a_dire:
            return self.a_dire.pop(0)
        time.sleep(0.02)
        return b""

    def write(self, octets):
        return len(octets)

    def close(self):
        pass


DEMANDE_IMALIVE = {"type": "imalive", "sens": "esclave>maitre", "mode": "MultiCast", "texte": "",
                   "ip_maitre": "192.168.4.1", "ip_esclave": "192.168.4.2", "delai": 1}


def groupe_muette(verifie, attend, monte_testeur):
    seuil_origine = tc.SEUIL_MUETTE
    tc.SEUIL_MUETTE = 0.6
    try:
        _carte(verifie, attend)
        _testeur(verifie, attend, monte_testeur)
    finally:
        tc.SEUIL_MUETTE = seuil_origine


def _carte(verifie, attend):
    notes, etats = [], []
    serie = SerieMuette()
    carte = tc.Carte("esclave", 115200, tc.Masque(), lambda *a: None, lambda *a: None, lambda *a: None,
                     lambda r, t: notes.append(t), lambda n, v: serie)
    carte.sur_etat = lambda: etats.append(carte.muette)
    carte.ouvre("COM_X", 115200)
    time.sleep(tc.SEUIL_MUETTE + 0.4)
    verifie(carte.muette, False, "TEMOIN carte silencieuse SANS commande : pas muette")
    carte.ecrit("Status 5")
    verifie(attend(lambda: carte.muette, 3), True, "commande sans aucune reponse : carte muette")
    verifie(sum(1 for n in notes if "muette" in n.lower()), 1, "carte muette : signalee une fois")
    verifie(True in etats, True, "carte muette : etat pousse a la page")
    carte.ecrit("Status 5")
    time.sleep(tc.SEUIL_MUETTE + 0.3)
    verifie(sum(1 for n in notes if "muette" in n.lower()), 1, "TEMOIN nouvelle commande : pas de 2e signalement")
    serie.a_dire.append(b"12:00:00.000 CMD: Status 5\n")
    verifie(attend(lambda: not carte.muette, 3), True, "une ligne revient : plus muette")
    verifie(any("repond de nouveau" in n for n in notes), True, "retour de la carte signale")
    carte.ecrit("Status 5")
    serie.a_dire.append(b"12:00:01.000 CMD: Status 5\n")
    time.sleep(tc.SEUIL_MUETTE + 0.3)
    verifie(carte.muette, False, "TEMOIN commande suivie d'une reponse : pas muette")
    carte.ecrit("Status 5")
    verifie(attend(lambda: carte.muette, 3), True, "muette de nouveau apres une commande sans reponse")
    carte.ferme()
    verifie(carte.muette, False, "port ferme : l'etat muette est oublie")
    carte.arret = True


def _testeur(verifie, attend, monte_testeur):
    t, sims, reseau, args = monte_testeur()
    t.cartes["maitre"].ouvre("COM_M", 115200)
    t.cartes["esclave"].ouvre("COM_E", 115200)
    attend(lambda: t.infos["esclave"]["ip"] == "192.168.4.2" and t.infos["maitre"]["ip"] != "")
    attend(lambda: t.acquis["esclave"]["mode"] and t.acquis["maitre"]["logs"])
    time.sleep(0.3)
    r = t.lance_essai(dict(DEMANDE_IMALIVE))
    verifie((r["verdict"], any("aucune ligne" in d and "carte esclave" in d for d in r["details"])), ("RECU", False),
            "TEMOIN esclave qui repond : RECU, pas d'alerte de carte muette")
    reveils = sims["COM_E"].reveils
    sims["COM_E"].muette = True
    r = t.lance_essai(dict(DEMANDE_IMALIVE))
    verifie(any("aucune ligne recue de la carte esclave" in d for d in r["details"]), True,
            "esclave muet : l'essai dit qu'aucune ligne n'est venue de la carte")
    verifie(r["details"][0].startswith("aucune ligne recue de la carte esclave"), True,
            "esclave muet : cette alerte vient EN TETE des details")
    verifie(any("aucune ligne recue de la carte maitre" in d for d in r["details"]), False,
            "TEMOIN maitre qui parle : pas d'alerte pour lui")
    verifie(attend(lambda: t.etat()["cartes"]["esclave"]["muette"], 3), True, "esclave muet : etat 'muette' dans /etat")
    verifie(t.etat()["cartes"]["maitre"]["muette"], False, "TEMOIN maitre : pas muet dans /etat")
    verifie(attend(lambda: sims["COM_E"].reveils > reveils, 3), True, "esclave muet : log serie relance (SerialLog)")
    sims["COM_E"].muette = False
    t.envoie_commande("esclave", "Status 5")
    verifie(attend(lambda: not t.etat()["cartes"]["esclave"]["muette"], 3), True, "esclave qui reparle : plus muet")
    # Log serie coupe par Tasmota (SERIALLOG_TIMER) apres un redemarrage sans perte du port : la relance suffit
    def compte(motif):
        return sum(1 for texte in t.notes_esclave() if motif in texte)
    muettes, retours = compte("carte MUETTE"), compte("repond de nouveau")
    sims["COM_E"].serie_coupee = True
    t.envoie_commande("esclave", "Status 5")
    verifie(attend(lambda: compte("carte MUETTE") > muettes, 3), True, "log serie coupe : carte signalee muette")
    verifie(attend(lambda: compte("repond de nouveau") > retours, 3), True,
            "log serie coupe : la relance automatique le retablit")
    verifie((sims["COM_E"].serie_coupee, t.etat()["cartes"]["esclave"]["muette"]), (False, False),
            "log serie coupe : log rouvert, carte plus muette")
    t.arrete()
