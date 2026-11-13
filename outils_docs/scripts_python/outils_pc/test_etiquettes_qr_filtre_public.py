"""Banc de etiquettes_qr_filtre_public (plan etiquettes-qrcode A10) : ce qui ne doit jamais paraitre dans une fiche publique.

UTILISATION (Python de PlatformIO)
    python outils_docs/scripts_python/outils_pc/test_etiquettes_qr_filtre_public.py
Code de sortie 0 = vert. Mutants : chaque regle de REGLES est retiree tour a tour ; au moins un cas doit alors changer de
verdict, sinon la regle n'est prouvee par rien.
"""

import sys

import etiquettes_qr_filtre_public as filtre

ECHECS = []

# (valeur, refusee ?) : chaque refus est atteint par UNE regle (son nom en commentaire), pour que les mutants le voient
CAS = [
    # identifiants dans une URL
    ("http://admin:secret@192.168.0.43/", True),                # url_identifiants
    ("mqtt://user:@broker.local", True),                        # url_identifiants (mot de passe vide)
    # parametres secrets, casse indifferente
    ("http://192.168.0.43/cm?token=abc", True),                 # parametre_secret
    ("http://192.168.0.43/?KEY=1", True),
    ("x?apikey=1", True), ("a&password=x", True), ("pass=x", True), ("pwd=x", True), ("secret=x", True),
    ("auth=x", True), ("u?Sig=x", True),
    ("monkey=1", False),                                        # « key= » au milieu d'un mot : pas un parametre
    ("u?access_token=x", True), ("u?api_key=x", True), ("x-api-key=1", True), ("u?passwd=x", True), ("u?pw=x", True),
    # IPv4
    ("8.8.8.8", True), ("IP : 92.184.1.2", True), ("100.64.1.1", True),
    ("192.168.0.43", False), ("192.168.0.51:8081", False), ("10.1.2.3", False), ("172.16.5.4", False),
    ("172.31.255.1", False), ("127.0.0.1", False), ("169.254.1.1", False), ("0.0.0.0", False), ("224.3.0.1", False),
    ("255.255.255.0", False),                                   # masque de sous-reseau (persists), ne revele rien
    ("172.32.0.1", True),                                       # juste hors de 172.16/12
    ("999.1.1.1", False),                                       # pas une adresse
    # IPv6
    ("2a01:cb00:1234::1", True), ("[2001:4860:4860::8888]:80", True),
    ("2a01:cb00::1:", True),                                   # suivie d'un deux-points (fin de phrase)
    ("fe80::1", False), ("fd00::42", False), ("::1", False), ("[fe80::1%eth0]", False),
    ("DC:85:DE:D9:CA:1D", False),                               # adresse MAC, pas une IPv6
    ("12:30:45", False),
    # noms de domaine joignables
    ("broker.hivemq.com", True), ("https://github.com/x", True), ("moi@exemple.fr", True),
    ("serveur-garage.local", False), ("http://cuve.lan/", False), ("box.home.arpa", False), ("SERVEUR-GARAGE", False),
    ("v1.2", False), ("19.5 °C", False), ("mDNS : http://SERVEUR-GARAGE.local", False),
    # chaines a allure de cle
    ("aB3dE5gH7jK9mN1pQ3sT5vX7", True),                         # base64 : majuscules, minuscules, chiffres
    ("Zm9vYmFyYmF6cXV4MTIzNDU2Nzg5MA==", True),
    ("9f86d081884c7d659a2feaa0c55ad015", True),                 # hexadecimal
    ("123e4567-e89b-12d3-a456-426614174000", True),             # UUID
    ("sk-proj-AbCdEf1234567890XyZ", True),                      # cle d'API coupee par des tirets
    ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV", True),   # JWT
    ("123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw", True),     # jeton de bot Telegram
    ("AKIAIOSFODNN7EXAMPLE", True),                             # cle AWS (majuscules seules) : motif
    ("xoxb-1234-5678-abcdefghij", True),                        # jeton Slack : motif
    # mots qui annoncent un secret (ligne libre, libelle)
    ("mot de passe : Tr0ub4dor&3", True), ("mdp soleil", True), ("Password", True), ("Clé WPA : x", True), ("PSK", True),
    ("Passerelle", False), ("Passage", False), ("Topic", False), ("Pin du relais", False),
    ("tasmota32s3-garage-piscine", False), ("SERVEUR-DEBITS-PAC-GATEWAY", False), ("anticonstitutionnellement", False),
    ("garage/rideau-garage-modbus", False), ("tasmota32p4_garage_serveur", False), ("12345678901234567890", False),
    # valeurs ordinaires
    ("CAPTEURS-CUVE", False), ("garage/cuve", False), ("Hostname : CUVE · IP : 192.168.0.43", False), ("", False),
    ("http://192.168.0.43", False), ("Range Extender id 2", False),
]


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)


def verdicts():
    return [filtre.controle_public(v) is not None for v, _ in CAS]


def principal():
    for (valeur, refusee), obtenu in zip(CAS, verdicts()):
        verifie(obtenu, refusee, f"{'refusee ' if refusee else 'acceptee'} : {valeur!r}")
    for valeur, cache in (("http://admin:x@h.local/", "admin"), ("IP 8.8.8.8", "8.8.8.8"), ("2a01:cb00:1234::1", "2a01"),
                          ("maison.duckdns.org", "duckdns")):
        raison = filtre.controle_public(valeur)
        verifie(isinstance(raison, str) and raison != "" and cache not in raison, True,
                f"raison du refus de {valeur!r} : un texte, qui ne recopie pas la valeur")
    verifie(filtre.controle_public(None) is None and filtre.controle_public(42) is None, True,
            "valeur qui n'est pas une chaine : rien a refuser (le texte resolu est toujours une chaine)")

    regles = list(filtre.REGLES)
    for i, (nom, _) in enumerate(regles):
        filtre.REGLES[:] = regles[:i] + regles[i + 1:]
        try:
            verifie(verdicts() != [r for _, r in CAS], True, f"mutant sans la regle {nom!r} : rouge")
        finally:
            filtre.REGLES[:] = regles
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(principal())
