"""Banc de etiquettes_qr_modele (fusion, champs, secrets, texte lu, image). Code de sortie 0 = vert.

Lecture seule du vrai depot (persist des cartes, gabarit) ; les images sont ecrites dans un dossier temporaire.
Temoin des secrets sur le vrai depot : motif INDEPENDANT de celui du module (filtre des sorties de ce depot).
Mutants : filtre par cle retire -> test_secret_par_cle rouge ; filtre par valeur retire -> test_secret_par_valeur rouge.
"""

import json
import os
import re
import sys
import tempfile
from pathlib import Path

import build_envs
import etiquettes_qr_modele as m
import fichiers_berry_etat

ECHECS = []
RACINE = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))
TEMOIN = re.compile(r"pass|pwd|mdp|key|token|secret|psk", re.I)

PERSIST = {
    "serveur": {"hostname": "CUVE", "wifi": {"ssid": "Maison", "mdp": "Sup3rSecret"},
                "mqtt": {"host": "192.168.0.2", "password": "motdepasse9", "topic": "cuve"}},
    "modules": {"x": {"url": "http://u:motdepasse9@h/", "nom": "cuve", "actif": "ON", "id": 2, "note": "a\nb"}},
    "liste": [{"pwd": "abcd1234", "v": 1}, {"v": True}],
}


def verifie(obtenu, attendu, libelle):
    if obtenu != attendu:
        ECHECS.append(libelle)
        print(f"ECHEC {libelle} : obtenu {obtenu!r}, attendu {attendu!r}")


def test_fusion():
    g = {"lignes": [{"source": "standard", "cle": "hostname"}], "separateur": " : ",
         "style": {"points": "rounded", "couleur": "#000000"}, "taille_mm": 25}
    r = m.fusionne(g, {"lignes": [{"source": "libre", "texte": "x"}], "style": {"couleur": "#ff0000"}})
    verifie(r["lignes"], [{"source": "libre", "texte": "x"}], "surcharge de lignes : liste remplacee")
    verifie(r["style"], {"points": "rounded", "couleur": "#ff0000"}, "surcharge de style : cle par cle")
    verifie(g["style"]["couleur"], "#000000", "gabarit non modifie")


def test_secret_par_cle():
    chemins = {f["chemin"] for f in m.arbre_persist(PERSIST)}
    for c in ("serveur.wifi.mdp", "serveur.mqtt.password", "liste.0.pwd"):
        verifie(c in chemins, False, f"{c} absent de l'arbre")
    for c in ("serveur.wifi.ssid", "modules.x.nom", "modules.x.id", "liste.0.v", "liste.1.v"):
        verifie(c in chemins, True, f"{c} propose")
    verifie(m.valeur_persist(PERSIST, "serveur.wifi.mdp"), (None, "clé sensible refusée"), "lecture d'une cle secrete refusee")
    verifie("clé sensible refusée" in " ".join(m.valide_reglage(
        {"lignes": [{"source": "persist", "chemin": "serveur.wifi.mdp"}]})), True, "reglage designant un secret refuse")


def test_secret_par_valeur():
    chemins = {f["chemin"] for f in m.arbre_persist(PERSIST)}
    verifie("modules.x.url" in chemins, False, "url contenant un mot de passe absente de l'arbre")
    verifie(m.valeur_persist(PERSIST, "modules.x.url"), (None, "valeur sensible refusée"), "lecture de l'url refusee")
    valeurs = " ".join(str(f["valeur"]) for f in m.arbre_persist(PERSIST))
    for s in ("Sup3rSecret", "motdepasse9", "abcd1234"):
        verifie(s in valeurs, False, f"secret {s[:3]}... absent des valeurs proposees")


def test_texte():
    champs = m.champs_de("tasmota32s3-garage-cuve", PERSIST["serveur"], "")
    verifie((champs["hostname"], champs["ip"], champs["topic"], champs["lieu"], champs["puce"]),
            ("CUVE", None, "cuve", "Garage", "ESP32-S3"), "champs standards")
    reglage = {"separateur": " : ", "lignes": [
        {"source": "standard", "cle": "hostname", "libelle": "Hostname"},
        {"source": "standard", "cle": "ip", "libelle": "IP"},
        {"source": "persist", "chemin": "modules.x.id", "libelle": "ModBus"},
        {"source": "persist", "chemin": "serveur.mqtt.password", "libelle": "Mdp"},
        {"source": "persist", "chemin": "modules.x.note", "libelle": "Note"},
        {"source": "persist", "chemin": "liste.1.v", "libelle": "Actif"},
        {"source": "libre", "texte": "Tableau", "libelle": ""}]}
    r = m.resout_avec(reglage, champs, PERSIST)
    verifie(r["texte"], "Hostname : CUVE\nModBus : 2\nNote : a b\nActif : oui\nTableau", "texte lu (saut de ligne par defaut)")
    verifie(m.resout_avec({**reglage, "entre_lignes": " · "}, champs, PERSIST)["texte"],
            "Hostname : CUVE · ModBus : 2 · Note : a b · Actif : oui · Tableau", "texte lu sur une ligne")
    verifie("entre les lignes" in " ".join(m.valide_reglage({**m.charge_gabarit(RACINE), "entre_lignes": "\t"})), True,
            "separateur de lignes inconnu refuse")
    verifie([l["etat"] for l in r["lignes"]], ["ok", "introuvable", "ok", "refuse", "ok", "ok", "ok"], "etats des lignes")
    verifie(len(r["avertissements"]), 2, "IP introuvable et mot de passe refuse signales")
    verifie("motdepasse9" in json.dumps(r), False, "aucun secret dans le resultat")
    f = m.fichier_carte(RACINE, {"style": {"points": "rounded", "image": None}}, r)
    verifie((f["ip_inscrite"], f["correction"], f["image"]), (None, "M", None), "fichier de carte sans IP ni image")


def test_esclave():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "_persist.json"
        p.write_text(json.dumps({"serveur": {"rangeExtender": {"activation": "ON", "id": 2, "ipMaitre": "192.168.0.51"}}}))
        ip = build_envs.adresse_par_maitre(p)
    verifie(ip, "192.168.0.51:8081", "esclave : adresse par le maitre")
    r = m.resout_avec({"lignes": [{"source": "standard", "cle": "ip", "libelle": "IP"}]}, m.champs_de("tasmota32-cave-x", {}, ip), {})
    verifie(r["texte"], "IP : 192.168.0.51:8081", "IP d'esclave dans le texte")


def test_config_decodee():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "config_decodee.json"
        p.write_text(json.dumps({"hostname": "TV", "mqtt_topic": "salon/tv", "sta_pwd": ["Sup3rSecret", ""],
                                 "mqtt_pwd": "motdepasse9", "friendlyname": ["TV"]}), encoding="utf-8")
        s = m.serveur_de_config(p)
        verifie(m.champs_de("tasmota-rdc-tv-salon", s, "192.168.0.70")["hostname"], "TV", "hostname d'une config decodee")
        verifie(m.champs_de("tasmota-rdc-tv-salon", s, "")["topic"], "salon/tv", "topic d'une config decodee")
        verifie("Sup3rSecret" in json.dumps(s) or "motdepasse9" in json.dumps(s), False, "aucun mot de passe lu")
        verifie(m.serveur_de_config(Path(d) / "absent.json"), {}, "config absente -> {}")


def test_image():
    with tempfile.TemporaryDirectory() as d:
        im = Path(d) / m.DOSSIER / "images"
        im.mkdir(parents=True)
        (im / "ok.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0h1"/></svg>')
        (im / "lourde.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 9000)
        (im / "faux.png").write_text("<html><body>x</body></html>")
        (im / "script.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>')
        (im / "onload.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" onload="x()"></svg>')
        verifie(m.image_data_uri(d, "ok.svg").startswith("data:image/svg+xml;base64,"), True, "svg simple accepte")
        for nom, mot in (("lourde.png", "trop lourde"), ("faux.png", "refusée"), ("script.svg", "refusée"),
                         ("onload.svg", "refusée"), ("../x.png", "refusée"), ("x.html", "refusée"), ("absente.png", "introuvable")):
            try:
                m.image_data_uri(d, nom)
                verifie("accepte", mot, f"image {nom} refusee")
            except ValueError as e:
                verifie(mot in str(e), True, f"image {nom} : message « {mot} »")


def test_validation():
    g = m.charge_gabarit(RACINE)
    verifie(m.valide_reglage(g, RACINE), [], "gabarit du depot valide")
    for cle, valeur, mot in (("taille_mm", 5, "taille"), ("separateur", "------", "séparateur"),
                             ("lignes", [], "lignes"), ("lignes", [{"source": "standard", "cle": "mac"}], "inconnu")):
        verifie(mot in " ".join(m.valide_reglage({**g, cle: valeur})), True, f"refus {cle}={valeur!r}")
    verifie("points" in " ".join(m.valide_reglage({**g, "style": {"points": "zigzag"}})), True, "forme de points inconnue")
    verifie("couleur" in " ".join(m.valide_reglage({**g, "style": {"couleur": "red"}})), True, "couleur invalide")
    try:
        m.chemin_surcharge(RACINE, "../../etc")
        verifie("accepte", "refus", "env avec ../ refuse")
    except ValueError:
        pass


def test_depot_reel():
    envs = build_envs.liste_envs(RACINE)
    cartes = [e.nom for e in envs if e.famille == "cartes"]
    avec_hote = avec_persist = nb_secrets = 0
    for env in cartes:
        persist = m.persist_de(RACINE, env)
        secrets = set()

        def collecte(o, sous=False):
            if isinstance(o, dict):
                for k, v in o.items():
                    collecte(v, sous or bool(TEMOIN.search(str(k))))
            elif isinstance(o, list):
                for v in o:
                    collecte(v, sous)
            elif sous and o is not None and len(str(o)) >= 4:
                secrets.add(str(o))

        collecte(persist)
        nb_secrets += len(secrets)
        fuites = [f["chemin"] for f in m.arbre_persist(persist) if any(s in str(f["valeur"]) for s in secrets)]
        verifie(fuites, [], f"{env} : aucune valeur secrete proposee (temoin independant)")
        hote = m.champs_standards(RACINE, env, envs)["hostname"]
        config = (RACINE / fichiers_berry_etat.dossier_carte(env) / "config_decodee.json").is_file()
        verifie(hote is not None, bool(persist) or config, f"{env} : hostname lu si la carte a un persist ou une config décodée")
        avec_hote += hote is not None
        avec_persist += bool(persist)
        verifie(m.valide_reglage(m.charge_reglage(RACINE, env), RACINE), [], f"{env} : reglage par defaut valide")
    print(f"depot reel : {len(cartes)} cartes, {avec_persist} avec persist, {avec_hote} avec hostname, {nb_secrets} valeurs secretes surveillees")
    verifie(nb_secrets > 0, True, "le temoin a trouve des secrets a surveiller")
    verifie(avec_persist >= 10, True, "au moins 10 cartes avec persist (temoin que la lecture marche)")


TESTS = [test_fusion, test_secret_par_cle, test_secret_par_valeur, test_texte, test_esclave, test_config_decodee, test_image,
         test_validation, test_depot_reel]


def mutant(nom, applique, retablit, test):
    global ECHECS
    garde, ECHECS = ECHECS, []
    sortie = sys.stdout
    sys.stdout = open(os.devnull, "w")              # les ECHEC attendus du mutant ne polluent pas la sortie
    try:
        applique()
        test()
    finally:
        retablit()
        sys.stdout.close()
        sys.stdout = sortie
        rouge, ECHECS = len(ECHECS), garde
    print(f"mutant {nom} : {f'rouge ({rouge} echecs)' if rouge else 'VERT (non detecte)'}")
    verifie(bool(rouge), True, f"mutant {nom} detecte")


if __name__ == "__main__":
    for t in TESTS:
        t()
    secret, sensible = m.SECRET, m._sensible
    mutant("filtre par cle retire", lambda: setattr(m, "SECRET", re.compile(r"(?!x)x")),
           lambda: setattr(m, "SECRET", secret), test_secret_par_cle)
    mutant("filtre par valeur retire", lambda: setattr(m, "_sensible", lambda v, s: str(v).startswith("@secret:")),
           lambda: setattr(m, "_sensible", sensible), test_secret_par_valeur)
    print("BANC_ETIQUETTES_QR_MODELE:", "ECHEC " + str(len(ECHECS)) if ECHECS else "OK")
    sys.exit(1 if ECHECS else 0)
