"""Alertes du sniffeur I2C (sniffeur_i2c.py) : ce qui merite d'etre signale dans le fil, en plus des trames.

    NACK repetes   NACK_REPETES transactions de suite non acquittees par la meme adresse (puce absente,
                   adresse fausse, puce occupee) ; un scan de Tasmota (une seule tentative par adresse) n'alerte pas ;
    tronquee       STOP ou START au milieu d'un octet (parasite, maitre redemarre, cable trop long) ;
    trop longue    transaction plus longue que le tampon du firmware : octets comptes mais non montres ;
    pertes         le sniffeur n'a pas pu tout envoyer (bus plus charge que ce que l'USB ecoule) ;
    bus bloque     SDA tenue basse, bus au repos : un esclave garde la ligne (couper son alimentation).
"""

NACK_REPETES = 3


class Alertes:
    def __init__(self):
        self.nack_suite = {}            # adresse -> NACK consecutifs

    def transaction(self, tr):
        """Transaction lue (sniffeur_i2c_protocole.lit_ligne, type X) -> textes d'alerte (souvent aucun)."""
        a, textes = tr["a"], []
        if tr["nack"] is not None:
            self.nack_suite[a] = self.nack_suite.get(a, 0) + 1
            if self.nack_suite[a] == NACK_REPETES:
                textes.append(f"0x{a:02X} : {NACK_REPETES} NACK de suite (puce absente, adresse fausse ou occupee)")
        else:
            self.nack_suite[a] = 0
        if tr["fin"] == "TRONQUE":
            textes.append(f"0x{a:02X} : transaction tronquee (STOP ou START au milieu d'un octet)")
        if tr["trop"]:
            textes.append(f"0x{a:02X} : {tr['trop']} octet(s) au-dela du tampon du sniffeur, non montres")
        return textes

    @staticmethod
    def pertes(n):
        return f"{n} transaction(s) PERDUE(S) par le sniffeur : bus plus charge que ce que l'USB ecoule"

    @staticmethod
    def bloque(ms):
        return f"bus BLOQUE : SDA tenue basse depuis {ms} ms (un esclave garde la ligne : couper son alimentation)"
