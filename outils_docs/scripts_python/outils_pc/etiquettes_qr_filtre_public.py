"""Filtre des valeurs d'une fiche PUBLIQUE (page « Etiquettes QR code », plan etiquettes-qrcode A10).

Une fiche publiee sur GitHub Pages se lit de partout : elle ne doit rien porter qui ouvre une porte vers la maison ou un
compte. Ce filtre s'ajoute a celui de l'A2 (`etiquettes_qr_modele` : cle secrete du persist, valeur qui contient un
secret du meme persist), qui ne voit que les secrets connus ; celui-ci juge la VALEUR seule.

controle_public(valeur) -> raison du refus (texte, sans recopier un identifiant ni une cle), ou None si la valeur peut
paraitre. Refuse : identifiants dans une URL, parametre secret (token=, access_token=, key=...), IPv4 hors reseaux prives,
IPv6 globale, nom de domaine joignable (hors .local, .lan, .home.arpa et noms sans point), chaine a allure de cle (base64,
hexadecimal, morceaux d'un JWT ou d'un jeton a deux-points, cle AWS, jeton Slack), mot qui annonce un secret (mot de passe,
mdp, password, token, WPA, PSK...). La raison ne recopie jamais la valeur trouvee.

Faux positifs assumes (le refus se lit dans l'apercu, la valeur se retire de la fiche) : un numero de version a quatre
nombres (15.1.0.1) ressemble a une IPv4 publique ; un nom de fichier (autoexec.be) a un nom de domaine.
"""

import ipaddress
import re

# Reseaux qui ne revelent rien : prives, boucle, lien local, « pas d'adresse » (0.0.0.0 = DHCP), multicast (224.3.0.1 de
# l'UDP du parc), masques de sous-reseau (255.x).
IPV4_SANS_RISQUE = [ipaddress.ip_network(n) for n in
                    ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8", "169.254.0.0/16", "0.0.0.0/8",
                     "224.0.0.0/4", "255.0.0.0/8")]
SUFFIXES_LOCAUX = (".local", ".lan", ".home.arpa")
PARAMETRES = ("token", "key", "apikey", "password", "passwd", "pass", "pwd", "pw", "secret", "auth", "sig")
MOTS_SECRETS = re.compile(r"\b(?:mot de passe|mdp|pass(?:word|wd)?|pwd|secret|token|wpa|psk|api[ _-]?key)\b", re.IGNORECASE)


def _url_identifiants(v):
    if re.search(r"://[^/\s@:]*:[^/\s@]*@", v):
        return "identifiants (utilisateur:mot de passe) dans une URL"
    return None


def _parametre_secret(v):
    # prefixe termine par _ ou - accepte (access_token=, x-api-key=), pas un mot colle (monkey=)
    m = re.search(r"(?:^|[?&;,\s])(?:[\w-]*[_-])?(" + "|".join(PARAMETRES) + r")=", v, re.IGNORECASE)
    return f"paramètre {m.group(1).lower()}= (secret)" if m else None


def _ipv4_publique(v):
    for s in re.findall(r"(?<![\d.])\d{1,3}(?:\.\d{1,3}){3}(?![\d.])", v):
        try:
            ip = ipaddress.IPv4Address(s)
        except ValueError:
            continue                                   # 999.1.1.1 : pas une adresse
        if not any(ip in n for n in IPV4_SANS_RISQUE):
            return "adresse IPv4 publique"
    return None


def _ipv6_globale(v):
    for s in re.findall(r"[0-9A-Fa-f:]*:[0-9A-Fa-f:]*", v):
        for candidat in {s, s.rstrip(":")}:            # « …::1: » en fin de phrase
            try:
                ip = ipaddress.IPv6Address(candidat)
            except ValueError:
                continue                               # adresse MAC, heure, morceau d'URL
            if ip.is_global:
                return "adresse IPv6 globale"
    return None


def _domaine(v):
    for m in re.finditer(r"(?<![\w.-])((?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63})(?![\w-])", v):
        nom = m.group(1).lower()
        if not nom.endswith(SUFFIXES_LOCAUX):
            return "nom de domaine joignable"
    return None


def _cle(v):
    if re.search(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b", v) or re.search(r"\bxox[abprs]-", v):
        return "chaîne à allure de clé (AWS, Slack)"
    for s in re.findall(r"\S{20,}", v):
        hexa = s.replace("-", "")
        if (re.fullmatch(r"[0-9A-Fa-f-]{20,}", s) and len(hexa) >= 20 and re.search(r"\d", hexa)
                and re.search(r"[A-Fa-f]", hexa)):
            return "chaîne à allure de clé (hexadécimal)"
        # base64, entier ou par morceau entre tirets (cle d'API sk-proj-…) ; les noms d'env, en minuscules ou en
        # majuscules seules, ne melangent jamais les deux casses avec des chiffres
        for morceau in [s] + re.split(r"[^A-Za-z0-9+/_=]", s):    # JWT (.), jeton a deux-points, sk-proj-
            if (len(morceau) >= 16 and re.fullmatch(r"[A-Za-z0-9+/_]+={0,2}", morceau) and re.search(r"[a-z]", morceau)
                    and re.search(r"[A-Z]", morceau) and re.search(r"\d", morceau)):
                return "chaîne à allure de clé (base64)"
    return None


def _mot_secret(v):
    return "mot qui annonce un secret (mot de passe, token, WPA…)" if MOTS_SECRETS.search(v) else None


REGLES = [("url_identifiants", _url_identifiants), ("parametre_secret", _parametre_secret), ("mot_secret", _mot_secret),
          ("ipv4_publique", _ipv4_publique), ("ipv6_globale", _ipv6_globale), ("domaine", _domaine), ("cle", _cle)]


def controle_public(valeur):
    """Raison du refus si `valeur` ne doit pas paraitre dans une fiche publique, None sinon."""
    if not isinstance(valeur, str):
        return None
    for _, regle in REGLES:
        raison = regle(valeur)
        if raison:
            return raison
    return None
