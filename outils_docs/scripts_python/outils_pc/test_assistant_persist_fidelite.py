"""Banc de la fidelite du modele (A6) : fusion automatique des cles nouvelles et bouton « Mettre a jour le modele ».

Code de sortie 0 = vert. Tout se joue dans un depot d'essai (copie des persists, du modele, des .ini) dans un dossier
temporaire, OUTILS_TASMOTA_DOSSIER pointe dans ce dossier : le VRAI modele_persist.json n'est JAMAIS fusionne ni
ecrit (Ruling 3), seulement lu. Aucune valeur de mot de passe n'est imprimee ; la cle secrete d'essai porte une
valeur-temoin qui ne doit apparaitre ni dans le modele, ni dans /modele/etat, ni dans le diff.
Lancer : "%USERPROFILE%\\.platformio\\penv\\Scripts\\python.exe" -u outils_docs/scripts_python/outils_pc/test_assistant_persist_fidelite.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import assistant_persist_modele as apm
import assistant_persist_web as apw
import fichiers_berry_sauvegarde as fbs
import test_assistant_persist_creation as tac
import test_assistant_persist_modele as tam
import test_assistant_persist_web as taw

ECHECS = []
TEMOIN_SECRET = "valeur-temoin-secret-A6"
PREFIXES = {"tasmota32": "ESP32", "tasmota32s3": "ESP32S3", "tasmota32p4": "ESP32P4"}


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def pose(racine, rel, chemin, valeur):
    """Ajoute `valeur` a `chemin` (pointe) dans un persist du depot d'essai."""
    f = Path(racine) / rel
    donnees = json.loads(f.read_text(encoding="utf-8-sig"))
    d = donnees
    cles = chemin.split(".")
    for cle in cles[:-1]:
        d = d.setdefault(cle, {})
    d[cles[-1]] = valeur
    f.write_text(json.dumps(donnees, indent="\t", ensure_ascii=False), encoding="utf-8")


def persists(racine):
    return [rel for rel, d, _ in apm.persists_du_depot(racine) if d is not None]


def deux_puces(racine):
    """Deux persists de puces differentes (la cle n'est alors pas propre a une puce)."""
    vus = {}
    for rel in persists(racine):
        vus.setdefault(PREFIXES[Path(rel).parent.name.split("-")[0]], rel)
    return list(vus.values())[:2]


def octets_modele(racine):
    return (Path(racine) / apm.FICHIER_MODELE).read_bytes()


def sauvegardes(nature):
    d = fbs.dossier_sauvegardes()
    return sorted(x.name for x in d.iterdir() if x.name.endswith("-" + nature)) if d.is_dir() else []


def depot(t):
    os.environ["OUTILS_TASMOTA_DOSSIER"] = os.path.join(t, "outils")
    return tac.depot(t)


# ---- fusion_cle_nouvelle ------------------------------------------------------------------------------------
def test_fusion_cle_nouvelle(t):
    racine = depot(t)
    modele = apm.charge_modele(racine)
    a, b = deux_puces(racine)
    for rel in (a, b):
        pose(racine, rel, "serveur.udp.essai", 7)
    avant = apm.ecarts(racine, modele)["nouvelles"]
    verifie(sorted(avant), ["serveur.udp.essai"], "fusion_cle_nouvelle : la cle est nouvelle pour le parc (2 persists)")
    fusionne, ajouts = apm.fusionne_nouvelles(racine, modele)
    verifie(ajouts, ["serveur.udp.essai"], "fusion_cle_nouvelle : ajouts = la cle")
    verifie(fusionne["socle"]["serveur"]["udp"].get("essai"), 7, "fusion_cle_nouvelle : au socle, valeur 7")
    verifie("serveur.udp.essai" in apm.a_completer(fusionne), True, "fusion_cle_nouvelle : presente dans a_completer")
    verifie("essai" in modele["socle"]["serveur"]["udp"], False, "fusion_cle_nouvelle : le modele passe n'est pas modifie")
    verifie(apm.ecarts(racine, fusionne)["nouvelles"], {}, "fusion_cle_nouvelle : plus aucune cle nouvelle apres fusion")
    texte0 = octets_modele(racine)
    apm.ecrit_modele(racine, fusionne, apm.NATURE_AUTO)
    verifie(octets_modele(racine) != texte0, True, "fusion_cle_nouvelle : modele ecrit")
    verifie(apm.charge_modele(racine), fusionne, "fusion_cle_nouvelle : le fichier relu = le modele fusionne")
    verifie(octets_modele(racine), json.dumps(fusionne, indent="\t", ensure_ascii=False).encode("utf-8") + b"\n",
            "fusion_cle_nouvelle : JSON indente par tabulation, fins de ligne du depot")
    verifie(len(sauvegardes(apm.NATURE_AUTO)), 1, "fusion_cle_nouvelle : sauvegarde creee")
    copie = fbs.dossier_sauvegardes() / sauvegardes(apm.NATURE_AUTO)[0] / apm.FICHIER_MODELE
    verifie(copie.read_bytes(), texte0, "fusion_cle_nouvelle : la sauvegarde porte la version d'origine")
    verifie(apm.a_completer(apm.charge_modele(racine)) != [], True, "fusion_cle_nouvelle : a_completer survit a l'ecriture")


def test_fusion_demarrage(t):
    """demarre_modele (appelee par principal) fait la meme chose, une fois, puis plus rien."""
    racine = depot(t)
    a, b = deux_puces(racine)
    for rel in (a, b):
        pose(racine, rel, "serveur.udp.essai", 7)
    ajouts = apw.demarre_modele(racine, lambda: [])
    verifie(ajouts, ["serveur.udp.essai"], "demarrage : cle ajoutee d'office")
    etat = apw.etat_modele(racine, ajouts)
    verifie((etat["ajouts"], etat["a_completer"], etat["erreur"]), (["serveur.udp.essai"], ["serveur.udp.essai"], ""),
            "demarrage : /modele/etat porte ajouts et a_completer")
    verifie(apw.demarre_modele(racine, lambda: []), [], "demarrage : relance -> rien a ajouter")
    avant = octets_modele(racine)
    verifie(apw.demarre_modele(racine, lambda: ["pio run"]), [], "demarrage : build en cours -> fusion reportee")
    verifie(octets_modele(racine), avant, "demarrage : rien ecrit pendant un build")


def test_fusion_valeur_frequente(t):
    racine = depot(t)
    rels = persists(racine)
    verifie(len(rels) >= 3, True, "fusion_frequente : au moins 3 persists dans le depot d'essai")
    pose(racine, rels[0], "serveur.udp.essaiA", 9)
    pose(racine, rels[1], "serveur.udp.essaiA", 7)
    pose(racine, rels[2], "serveur.udp.essaiA", 7)
    pose(racine, rels[0], "serveur.udp.essaiB", 1)
    pose(racine, rels[1], "serveur.udp.essaiB", 2)               # egalite : premiere carte par ordre de chemin
    modele, ajouts = apm.fusionne_nouvelles(racine, apm.charge_modele(racine))
    verifie(sorted(ajouts), ["serveur.udp.essaiA", "serveur.udp.essaiB"], "fusion_frequente : 2 cles")
    def valeur(chemin):                                  # au socle, ou chez la seule puce qui la porte
        v = tam._valeur(modele["socle"], chemin)
        return v if v is not None else next((p["ajouts"][chemin] for p in modele["puces"].values() if chemin in p.get("ajouts", {})), None)
    verifie((valeur("serveur.udp.essaiA"), valeur("serveur.udp.essaiB")), (7, 1),
            "fusion_frequente : valeur la plus frequente ; egalite -> premiere carte")


def test_fusion_puce_unique(t):
    racine = depot(t)
    rel = deux_puces(racine)[0]
    puce = PREFIXES[Path(rel).parent.name.split("-")[0]]
    pose(racine, rel, "serveur.udp.essai", 7)
    modele, ajouts = apm.fusionne_nouvelles(racine, apm.charge_modele(racine))
    verifie(ajouts, ["serveur.udp.essai"], "puce_unique : cle ajoutee")
    verifie(modele["puces"][puce]["ajouts"].get("serveur.udp.essai"), 7, "puce_unique : sous puces.<p>.ajouts")
    verifie("essai" in modele["socle"]["serveur"]["udp"], False, "puce_unique : pas au socle")
    verifie(apm.ecarts(racine, modele)["nouvelles"], {}, "puce_unique : couverte apres fusion")


# ---- fusion_secret -------------------------------------------------------------------------------------------
def test_fusion_secret(t):
    racine = depot(t)
    for rel in deux_puces(racine):
        pose(racine, rel, "serveur.mqtt.mdpSecours", TEMOIN_SECRET)
    modele = apm.charge_modele(racine)
    fusionne, ajouts = apm.fusionne_nouvelles(racine, modele)
    verifie(ajouts, ["serveur.mqtt.mdpSecours"], "fusion_secret : cle ajoutee")
    verifie(fusionne["socle"]["serveur"]["mqtt"].get("mdpSecours"), "@secret:serveur.mqtt.mdpSecours", "fusion_secret : @secret:<chemin>")
    apm.ecrit_modele(racine, fusionne, apm.NATURE_AUTO)
    verifie(TEMOIN_SECRET.encode() in octets_modele(racine), False, "fusion_secret : aucune valeur dans le modele ecrit")
    etat = json.dumps(apw.etat_modele(racine, ajouts))
    verifie(TEMOIN_SECRET in etat, False, "fusion_secret : aucune valeur dans /modele/etat")
    p = apm.propose_mise_a_jour(racine, apm.charge_modele(racine))
    verifie(TEMOIN_SECRET in json.dumps(p), False, "fusion_secret : aucune valeur dans la proposition de mise a jour")
    sauv = fbs.dossier_sauvegardes()
    fuite = [x for x in sauv.rglob("*") if x.is_file() and TEMOIN_SECRET.encode() in x.read_bytes()] if sauv.is_dir() else []
    verifie([x.name for x in fuite], [], "fusion_secret : aucune valeur dans les sauvegardes du modele")


# ---- fusion_rien ---------------------------------------------------------------------------------------------
def test_fusion_rien(t):
    racine = depot(t)
    modele = apm.charge_modele(racine)
    avant, mtime = octets_modele(racine), (Path(racine) / apm.FICHIER_MODELE).stat().st_mtime_ns
    fusionne, ajouts = apm.fusionne_nouvelles(racine, modele)
    verifie((ajouts, fusionne is modele), ([], True), "fusion_rien : aucun ajout, modele rendu tel quel")
    verifie(apw.demarre_modele(racine, lambda: []), [], "fusion_rien : demarre_modele -> []")
    verifie(((Path(racine) / apm.FICHIER_MODELE).stat().st_mtime_ns, octets_modele(racine)), (mtime, avant),
            "fusion_rien : modele intact (date de modification inchangee)")
    verifie(sauvegardes(apm.NATURE_AUTO), [], "fusion_rien : aucune sauvegarde creee")


# ---- bouton_retrait ------------------------------------------------------------------------------------------
def test_bouton_retrait(t):
    racine = depot(t)
    modele = apm.charge_modele(racine)
    modele["socle"]["serveur"]["udp"]["fantome"] = 1                  # absente du parc : a retirer
    modele["socle"]["serveur"]["udp"]["aligne"] = 6                   # le parc dit 5 : a aligner
    modele["a_completer"] = ["serveur.udp.garde"]                     # doit rester tel quel
    apm.ecrit_modele(racine, modele, "essai")
    for rel in persists(racine):
        pose(racine, rel, "serveur.udp.aligne", 5)
    pose(racine, persists(racine)[0], "serveur.udp.nouveau_ignore", 3)  # nouvelle : ne regarde pas le bouton
    modele = apm.charge_modele(racine)
    p = apm.propose_mise_a_jour(racine, modele)
    verifie("serveur.udp.fantome" in p["retraits"], True, "bouton_retrait : la cle absente du parc est proposee au retrait")
    verifie([a for a in p["alignements"] if a["chemin"] == "serveur.udp.aligne"], [{"chemin": "serveur.udp.aligne", "modele": 6, "parc": 5}],
            "bouton_retrait : le defaut divergent est propose a l'alignement")
    verifie(("fantome" in p["diff"], "aligne" in p["diff"], bool(p["empreinte"])), (True, True, True), "bouton_retrait : diff et empreinte")
    verifie(octets_modele(racine) == json.dumps(modele, indent="\t", ensure_ascii=False).encode("utf-8") + b"\n", True,
            "bouton_retrait : proposer n'ecrit rien")
    avant = octets_modele(racine)
    try:
        apm.applique_mise_a_jour(racine, "0" * 64)
        verifie("accepte", "RuntimeError", "bouton_retrait : mauvaise empreinte refusee")
    except RuntimeError:
        verifie(octets_modele(racine), avant, "bouton_retrait : mauvaise empreinte -> refus, modele intact")
    r = apm.applique_mise_a_jour(racine, p["empreinte"])
    neuf = apm.charge_modele(racine)
    udp = neuf["socle"]["serveur"]["udp"]
    verifie(("fantome" in udp, udp.get("aligne")), (False, 5), "bouton_retrait : retrait et alignement appliques")
    verifie(r["applique"] and "serveur.udp.fantome" in r["retraits"], True, "bouton_retrait : compte rendu")
    verifie(neuf["a_completer"], ["serveur.udp.garde"], "bouton_retrait : a_completer inchange")
    verifie(len(sauvegardes(apm.NATURE_MAJ)), 1, "bouton_retrait : sauvegarde de la mise a jour")
    try:
        apm.applique_mise_a_jour(racine, p["empreinte"])
        verifie("accepte", "RuntimeError", "bouton_retrait : empreinte rejouee refusee")
    except RuntimeError:
        verifie(True, True, "bouton_retrait : empreinte rejouee refusee (le modele a change)")


def test_bouton_http(t):
    """Les routes : /modele/etat, /modele/prepare, /modele/applique (empreinte, build en cours)."""
    racine_a_modifier = depot(t)
    modele = apm.charge_modele(racine_a_modifier)
    modele["socle"]["serveur"]["udp"]["fantome"] = 1
    apm.ecrit_modele(racine_a_modifier, modele, "essai")
    b = taw.Banc(t, racine=racine_a_modifier)
    try:
        verifie(b.racine, racine_a_modifier, "http : meme depot d'essai")
        _, etat = b.requete("GET", "/modele/etat")
        verifie("serveur.udp.fantome" in etat["disparues"], True, "http : /modele/etat liste la disparue")
        statut, p = b.requete("POST", "/modele/prepare", {})
        verifie((statut, "serveur.udp.fantome" in p["retraits"], bool(p["empreinte"])), (200, True, True), "http : /modele/prepare")
        verifie(b.requete("POST", "/modele/applique", {})[0], 400, "http : applique sans empreinte -> 400")
        verifie(b.requete("POST", "/modele/applique", {"empreinte": "0" * 64})[0], 409, "http : mauvaise empreinte -> 409")
        b.builds = ["pio run"]
        verifie(b.requete("POST", "/modele/applique", {"empreinte": p["empreinte"]})[0], 409, "http : pendant un build -> 409")
        b.builds = []
        verifie(b.requete("POST", "/modele/prepare", {}, entetes={})[0], 403, "http : /modele/prepare sans en-tete -> 403")
        statut, r = b.requete("POST", "/modele/applique", {"empreinte": p["empreinte"]})
        verifie((statut, r.get("applique")), (200, True), "http : applique avec la bonne empreinte")
        _, etat = b.requete("GET", "/modele/etat")
        verifie("serveur.udp.fantome" in etat["disparues"], False, "http : plus de disparue apres application")
        verifie(b.requete("POST", "/modele/applique", {"empreinte": p["empreinte"]})[0], 409, "http : rien a faire / perime -> 409")
    finally:
        b.ferme()


# ---- modele_illisible (point 2) -------------------------------------------------------------------------------
def test_modele_illisible(t):
    racine = depot(t)
    casse = b'{\n\t"version": 1,\n\t"socle": {\n\t\t"diverses": oups\n\t}\n}\n'
    (Path(racine) / apm.FICHIER_MODELE).write_bytes(casse)
    for rel in deux_puces(racine):
        pose(racine, rel, "serveur.udp.essai", 7)                  # il y aurait de quoi fusionner
    ajouts = apw.demarre_modele(racine, lambda: [])
    verifie(ajouts, [], "modele_illisible : le demarrage ne fusionne rien et ne plante pas")
    verifie(octets_modele(racine), casse, "modele_illisible : fichier intact (pas de reecriture)")
    verifie(sauvegardes(apm.NATURE_AUTO), [], "modele_illisible : aucune sauvegarde ni ecriture")
    b = taw.Banc(t, ajouts, racine)
    try:
        (Path(b.racine) / apm.FICHIER_MODELE).write_bytes(casse)
        statut, etat = b.requete("GET", "/modele/etat")
        verifie((statut, "ligne 4" in etat["erreur"], etat["ajouts"], etat["a_completer"]), (200, True, [], []),
                "modele_illisible : /modele/etat.erreur nomme la ligne")
        statut, p = b.requete("GET", "/parc")
        verifie((statut, "ligne 4" in p["erreur_modele"]), (200, True), "modele_illisible : la page s'ouvre, /parc.erreur_modele")
        verifie(b.requete("POST", "/modele/prepare", {})[0], 400, "modele_illisible : /modele/prepare refuse")
        verifie(b.requete("POST", "/modele/applique", {"empreinte": "0" * 64})[0] in (400, 409), True, "modele_illisible : /modele/applique refuse")
        statut, c = b.requete("POST", "/prepare", {"reponses": taw.reponses()})
        refuse = statut != 200 or bool(c.get("refus")) or not c.get("empreinte")
        verifie(refuse, True, "modele_illisible : creation refusee (pas d'empreinte exploitable)")
        verifie(b.requete("POST", "/creation", {"reponses": taw.reponses(), "empreinte": "0" * 64})[0] in (400, 409), True,
                "modele_illisible : /creation refusee")
        verifie(octets_modele(b.racine), casse, "modele_illisible : fichier toujours intact apres toutes les routes")
    finally:
        b.ferme()


# ---- banc_couverture_signale ----------------------------------------------------------------------------------
def test_couverture_signale(t):
    """Ruling 3 : apres fusion, a_completer n'est plus vide -> la regle de rien_a_completer (banc A1) echoue.
    Appliquee au modele fusionne du depot d'essai, JAMAIS au vrai modele (qui reste a_completer == [])."""
    racine = depot(t)
    for rel in deux_puces(racine):
        pose(racine, rel, "serveur.udp.essai", 7)
    fusionne, _ = apm.fusionne_nouvelles(racine, apm.charge_modele(racine))
    ECHECS_AVANT = list(tam.ECHECS)
    sortie = sys.stdout
    try:
        sys.stdout = open(os.devnull, "w")
        tam.test_rien_a_completer(fusionne)                        # le test de A1, sur le modele fusionne
    finally:
        sys.stdout.close()
        sys.stdout = sortie
    echoue = tam.ECHECS[len(ECHECS_AVANT):] == ["rien_a_completer"]
    del tam.ECHECS[len(ECHECS_AVANT):]
    verifie(echoue, True, "banc_couverture_signale : rien_a_completer echoue sur le modele fusionne (a relire)")
    vrai = apm.charge_modele(tac.RACINE)
    verifie(apm.a_completer(vrai), [], "banc_couverture_signale : le VRAI modele n'a rien a completer (jamais fusionne par ce banc)")


def principal():
    vrai = (tac.RACINE / apm.FICHIER_MODELE).read_bytes()
    for test in (test_fusion_cle_nouvelle, test_fusion_demarrage, test_fusion_valeur_frequente, test_fusion_puce_unique,
                 test_fusion_secret, test_fusion_rien, test_bouton_retrait, test_bouton_http, test_modele_illisible,
                 test_couverture_signale):
        with tempfile.TemporaryDirectory() as t:
            try:
                test(t)
            except Exception as exc:
                verifie(repr(exc), "pas d'exception", test.__name__)
    verifie((tac.RACINE / apm.FICHIER_MODELE).read_bytes() == vrai, True, "le VRAI modele_persist.json n'a pas ete touche")
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
