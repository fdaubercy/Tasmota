"""Protocole serie du sniffeur I2C (v=1), commun au firmware ESP32-S3 et, plus tard, au Pico.

Reference : docs/superpowers/specs/2026-10-31-sniffeur-i2c-design.md §5 ; emetteur :
outils_docs/firmware_sniffeur_i2c/src/main.cpp. Une ligne texte par message, un champ cle=valeur par mot :
    I v=1 puce=esp32s3 sda=4 scl=5 mode=ecoute ech=<MHz>      identite (au demarrage et sur « ? »)
    X t=<us> a=<hex2> rw=R|W d=<hexa|-> nack=<i|-> fin=STOP|RESTART|TRONQUE f=<kHz> [trop=<k>]
    P n=<transactions perdues>     B sda=bas ms=<duree>     M ok=1 d=<hexa|->  |  M ok=0 err=<raison>
nack : 0 = adresse non acquittee, k = k-ieme octet ECRIT non acquitte (le NACK final d'une lecture est normal).
Ordres du PC : ?   MW a=<hex2> d=<hexa>   MR a=<hex2> n=<octets>   MWR a=<hex2> d=<hexa> n=<octets>
"""

VERSION = 1
VIDS_SNIFFEUR = (0x303A, 0x2E8A)           # USB : Espressif (USB natif de l'S3), Raspberry Pi (Pico, voie 2)
FINS = ("STOP", "RESTART", "TRONQUE")
ADRESSE_MIN, ADRESSE_MAX = 0x03, 0x77      # hors adresses reservees de la norme
OCTETS_MAX = 32                            # tampon Wire du firmware


def _champs(mots):
    champs = {}
    for mot in mots:
        cle, egal, valeur = mot.partition("=")
        if not cle or not egal:
            raise ValueError(mot)
        champs[cle] = valeur
    return champs


def _hexa(texte):
    return b"" if texte == "-" else bytes.fromhex(texte)


def lit_ligne(texte):
    """Une ligne du sniffeur -> dict (cle 'type' = I, X, P, B ou M), ou None si illisible. Jamais d'exception."""
    try:
        mots = str(texte).strip().split()
        if not mots or mots[0] not in ("I", "X", "P", "B", "M"):
            return None
        genre, c = mots[0], _champs(mots[1:])
        if genre == "X":
            a = int(c["a"], 16)
            if not 0 <= a <= 0x7F or c["rw"] not in ("R", "W") or c["fin"] not in FINS:
                return None
            return {"type": "X", "t": int(c["t"]), "a": a, "rw": c["rw"], "d": _hexa(c["d"]),
                    "nack": None if c["nack"] == "-" else int(c["nack"]), "fin": c["fin"],
                    "f": float(c["f"]), "trop": int(c.get("trop", "0"))}
        if genre == "P":
            return {"type": "P", "n": int(c["n"])}
        if genre == "B":
            return {"type": "B", "ms": int(c["ms"])}
        if genre == "M":
            ok = c["ok"] == "1"
            return {"type": "M", "ok": ok, "d": _hexa(c.get("d", "-")) if ok else b"", "err": c.get("err", "")}
        return {"type": "I", "v": int(c["v"]), "puce": c["puce"], "sda": int(c["sda"]), "scl": int(c["scl"]),
                "mode": c.get("mode", ""), "ech": int(c.get("ech", "0"))}
    except (KeyError, ValueError):
        return None


def ordre(nom, a=0, d=b"", n=0):
    """Ordre du PC vers le sniffeur -> octets a ecrire ; ValueError si hors bornes (rien n'est envoye)."""
    if nom == "?":
        return b"?\n"
    if nom not in ("MW", "MR", "MWR"):
        raise ValueError(f"ordre inconnu : {nom}")
    if not ADRESSE_MIN <= a <= ADRESSE_MAX:
        raise ValueError(f"adresse 0x{a:02X} hors 0x{ADRESSE_MIN:02X}..0x{ADRESSE_MAX:02X}")
    texte = f"{nom} a={a:02X}"
    if nom in ("MW", "MWR"):
        if not 1 <= len(d) <= OCTETS_MAX:
            raise ValueError(f"1 a {OCTETS_MAX} octets a ecrire")
        texte += " d=" + bytes(d).hex().upper()
    if nom in ("MR", "MWR"):
        if not 1 <= n <= OCTETS_MAX:
            raise ValueError(f"1 a {OCTETS_MAX} octets a lire")
        texte += f" n={n}"
    return (texte + "\n").encode("ascii")


class Lignes:
    """Recoupe en lignes des morceaux lus sur le port (une ligne peut arriver en plusieurs lectures)."""
    LONGUEUR_MAX = 4096                    # au-dela sans fin de ligne : flux corrompu, on jette

    def __init__(self):
        self.reste = b""

    def ajoute(self, morceau):
        self.reste += morceau
        *lignes, self.reste = self.reste.split(b"\n")
        if len(self.reste) > self.LONGUEUR_MAX:
            self.reste = b""
        return [ligne.decode("ascii", "replace").strip() for ligne in lignes if ligne.strip()]
