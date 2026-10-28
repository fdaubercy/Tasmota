"""Banc de assistant_persist_generation (persist, autoexec, listes du cenv, coherence, squelettes).

Code de sortie 0 = vert. Lecture seule du vrai depot (modele, persists, cenv) ; les cas d'echec (persist
illisible, mot de passe ambigu) se jouent dans une COPIE (depot_essai) dans un dossier temporaire. Aucune valeur de
mot de passe n'est imprimee : les secrets se comparent par egalite, un ecart n'affiche que son CHEMIN.
A lancer avec le Python du penv (ProjectConfig) :
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" -u outils_docs/scripts_python/outils_pc/test_assistant_persist_generation.py
    ... --temoin <modele.json>   rejeu seul sur un modele mute (temoin) : cartes en ecart, code 1 si ecart

REJEU DU PARC (Ruling 8 du controleur, 2026-10-27)
--------------------------------------------------
Pour chaque carte au format actuel, les reponses sont deduites de son persist, le persist est regenere avec les
vrais mots de passe, puis compare au vrai :
  (a) PRESENCE de chaque chemin du modele (chemins_modele) : genere et reel portent les memes ;
  (b) VALEURS des chemins poses par une reponse : gabarits {{...}} et secrets du socle, chemins des roles et des
      ajouts de puce, actif/inactif des blocs, cles `activation` des blocs (au plus 3 niveaux), gabarits metier.
Les ecarts restants sont des reglages faits a la main hors questions : ils sont toleres par la liste NOMMEE
TOLERANCES ci-dessous (motif de chemin precis, cartes, raison), jamais par un joker global. Une entree qui ne couvre
plus aucun ecart est signalee : la liste reste exacte.
"""

import copy
import fnmatch
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import assistant_persist_generation as gen
import assistant_persist_modele as apm
import assistant_persist_parc as parc
from assistant_persist_generation import Reponses
from test_fichiers_berry_creation import RACINE, depot_essai

ECHECS = []
CUVE = "data/garage/tasmota32s3-capteurs-cuve-modbus"
RIDEAU = "data/garage/tasmota32s3-rideau-garage-modbus"
# Cartes hors rejeu, avec leur raison
EXCLUES = {
    "data/garage/tasmota32s3-serveur-modbus": "ancien maitre S3 du garage : id 0, Range Extender ON, ipMaitre renseigne et "
                                             "NAPT OFF, aucun role ne le decrit (Ruling 9)",
}

# (motif fnmatch du chemin reduit, cartes (noms de dossier) ou None = toutes, raison). Ruling 8 : familles 2 a 5.
DIFF, CAVE1, CAVE3, GRENIER, P4, CUVE_, RIDEAU_ = ("tasmota32-interrupteur-differentiel", "tasmota32-serveur-rly",
                                                 "tasmota32s3-serveur-rly", "tasmota32s3-grenier",
                                                 "tasmota32p4-serveur-modbus", "tasmota32s3-capteurs-cuve-modbus",
                                                 "tasmota32s3-rideau-garage-modbus")
TOLERANCES = [
    # -- famille 3 : bloc metier ecrit a la main
    ("modules.*.name", None, "nom du bloc metier : texte libre de chaque carte (gabarit = nom du module)"),
    ("modules.*.logs", (DIFF, CAVE1, CAVE3, GRENIER),
     "journal metier : absent (differentiel, cave S3, grenier) ou nomme a la main (cave ESP32 : pompe-vide-cave.log)"),
    # -- famille 2 : contenu des elements des drivers, propre a chaque carte
    ("drivers.leds.environnement.leds.led#.pin", (DIFF, CAVE1, CAVE3, GRENIER), "broche de la LED de la carte"),
    ("drivers.leds.environnement.leds.ledLink.pin", (DIFF, CAVE1, CAVE3), "broche de la LED de liaison de la carte"),
    ("drivers.ModBus.environnement.pinsModBus.*", (DIFF,),
     "broches serie du differentiel (ModBus OFF ; autre nom, broche et type que le socle)"),
    ("drivers.I2C.environnement.pinsI2Cs.pinsI2C#.activation", (CAVE1, CAVE3, GRENIER),
     "broches I2C a OFF quand I2C est OFF (le bloc i2c inactif ne pose que drivers.I2C.activation)"),
    # -- famille 4 : reglages propres a une carte
    ("diverses.historique.grafana", (CAVE3, GRENIER, RIDEAU_), "cle absente de ces S3 (ajoutee au parc apres eux)"),
    ("serveur.rangeExtender.AP.routeNAPT", (CAVE3, GRENIER), "le role maitre ne tranche pas : cave S3 et grenier a OFF, P4 a ON"),
    # -- famille 5 : blocs absents d'un vieux persist
    ("drivers.I2S.*", (DIFF,), "bloc absent du vieux persist du differentiel (OFF sur une carte generee)"),
    ("drivers.Ethernet.*", (DIFF,), "bloc absent du vieux persist du differentiel (OFF sur une carte generee)"),
    ("drivers.voletRoulants.*", (DIFF,), "bloc absent du vieux persist du differentiel (OFF sur une carte generee)"),
]


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def _env(dossier):
    """data/<lieu>/<prefixe>-<nom> -> <prefixe>-<lieu>-<nom> (inverse de transform_name)."""
    _, lieu, carte = dossier.split("/")
    prefixe, _, nom = carte.partition("-")
    return f"{prefixe}-{lieu}-{nom}"


def _pilotes(modele):
    """Chemins reduits dont la valeur est posee par une reponse (voir l'en-tete)."""
    res = set()
    for c, v in apm._feuilles(modele["socle"], ()):
        if isinstance(v, str) and ("{{" in v or v.startswith("@secret:")):
            res.add(apm.reduit(c))
    tables = list(modele["roles"].values()) + [p.get("ajouts", {}) for p in modele["puces"].values()]
    tables += [b[k] for b in modele["blocs"] for k in ("actif", "inactif")]
    for table in tables:
        for cle, valeur in table.items():
            res |= apm.chemins(valeur, tuple(cle.split("."))) if valeur is not None else {apm.reduit(cle.split("."))}
    res |= {c for c in apm.chemins_modele(modele) if c[-1] == "activation" and len(c) <= 3}
    for c, v in apm._feuilles(modele["metier"]["gabarit"], ("modules", "*")):
        if isinstance(v, str) and "{{" in v:
            res.add(apm.reduit(c))
    return res


def ecarts_carte(modele, rel, donnees):
    """[(chemin pointe, nature)] des ecarts entre le persist regenere et le vrai (nature : presence ou valeur)."""
    dossier = rel.rsplit("/", 1)[0]
    r = gen.reponses_depuis_persist(modele, donnees, _env(dossier), RACINE)
    v = gen.variables(RACINE, r)
    obj = gen.persist(modele, r, v, parc.secrets(RACINE, v["reseau1"], v["reseau2"]))
    decrits, pilotes = apm.chemins_modele(modele), _pilotes(modele)
    pg, pr = apm.chemins(obj) & decrits, apm.chemins(donnees) & decrits
    vg, vr = apm._valeurs(obj), apm._valeurs(donnees)
    res = [(".".join(c), "presence") for c in sorted(pg ^ pr)]
    res += [(".".join(c), "valeur") for c in sorted(pilotes & pg & pr) if vg[c] != vr[c]]
    return res


def _tolere(chemin, carte):
    for i, (motif, cartes, _) in enumerate(TOLERANCES):
        if fnmatch.fnmatchcase(chemin, motif) and (cartes is None or carte in cartes):
            return i
    return None


def rejeu(modele):
    """({dossier: [ecarts non toleres]}, [nombre d'ecarts couverts par entree de TOLERANCES])."""
    restants, couverts = {}, [0] * len(TOLERANCES)
    for rel, donnees, _ in apm.persists_du_depot(RACINE):
        dossier = rel.rsplit("/", 1)[0]
        if dossier in EXCLUES or donnees is None:
            continue
        carte = dossier.split("/")[-1]
        for chemin, nature in ecarts_carte(modele, rel, donnees):
            i = _tolere(chemin, carte)
            if i is None:
                restants.setdefault(dossier, []).append(f"{chemin} ({nature})")
            else:
                couverts[i] += 1
    return restants, couverts


def test_rejeu_parc(modele):
    restants, couverts = rejeu(modele)
    for dossier, liste in sorted(restants.items()):
        print(f"     ecarts {dossier} :")
        for e in liste:
            print(f"       {e}")
    verifie(restants, {}, "rejeu_parc : aucun ecart hors de la liste nommee")
    for (motif, cartes, raison), n in zip(TOLERANCES, couverts):
        print(f"     tolerance {n:3d} ecart(s)  {motif}  [{', '.join(cartes) if cartes else 'toutes'}]  {raison}")
    verifie([m for (m, _, _), n in zip(TOLERANCES, couverts) if n == 0], [], "rejeu_parc : chaque tolerance sert")
    for dossier, raison in EXCLUES.items():
        print(f"     hors rejeu : {dossier} : {raison}")


def _appels(texte):
    """Suite des appels demarrage.* sans commentaires ni lignes vides."""
    res = []
    for ligne in texte.splitlines():
        code = ligne.split("#", 1)[0].strip()
        if code.startswith("demarrage."):
            res.append(code)
    return res


def _reponses_cuve(modele):
    donnees = json.loads((RACINE / CUVE / "_persist.json").read_text(encoding="utf-8-sig"))
    r = gen.reponses_depuis_persist(modele, donnees, _env(CUVE), RACINE)
    # LoRaWan est ON dans le persist de la cuve mais ses modules sont exclus du cenv (incoherence du parc, rapport A1)
    r.blocs = [b for b in r.blocs if b != "lorawan"]
    return r


def test_autoexec_cuve(modele):
    r = _reponses_cuve(modele)
    reel = (RACINE / CUVE / "autoexec.be").read_text(encoding="utf-8")
    texte = gen.autoexec(modele, r)
    verifie(_appels(texte), _appels(reel), "autoexec_cuve : meme suite d'appels demarrage.*")
    verifie(texte.splitlines()[-1], "end", "autoexec_cuve : finit par end")
    verifie("import demarrage" in texte and "if demarrage.prologue()" in texte, True, "autoexec_cuve : prologue")


def test_listes_cuve(modele):
    l = gen.listes_cenv(modele, _reponses_cuve(modele))
    attendu_exclude = {"data/fs/vrFonctions.be", "data/fs/loRaWanFonctions.be", "data/fs/controleVoletRoulants.be",
                       "data/fs/controleLoRaWan.be", "data/fs/controleES8311.be", "data/fs/controleCoprocesseur.be"}
    verifie(set(l["exclude"]), attendu_exclude, "listes_cuve : exclude = celui du cenv de la cuve")
    verifie(l["solidify"][0], "${berry_commun.socle}", "listes_cuve : socle en tete")
    verifie({"${berry_commun.modbus}", "${berry_commun.historique}", "data/fs/ledsFonctions.be",
             "data/fs/controleLeds.be"} <= set(l["solidify"]), True, "listes_cuve : modbus, historique, leds solidifies")
    r = _reponses_cuve(modele)
    obj = gen.persist(modele, r, gen.variables(RACINE, r))
    verifie(gen.coherence(modele, r, obj, gen.autoexec(modele, r), l), [], "listes_cuve : cuve coherente")


def _nouvelle(**kw):
    base = dict(puce="ESP32S3", base="", lieu="garage", nom="porte-test", reseau1="MAISON")
    base.update(kw)
    return Reponses(**base)


def test_historique_esp32(modele):
    r = _nouvelle(puce="ESP32", blocs=["historique"])
    obj = gen.persist(modele, r, gen.variables(RACINE, r))
    refus = gen.coherence(modele, r, obj, gen.autoexec(modele, r), gen.listes_cenv(modele, r))
    verifie(bool(refus) and any("historique" in x for x in refus), True, "historique_esp32 : refus qui nomme l'historique")
    verifie("historique" in obj["diverses"], False, "historique_esp32 : diverses.historique retire du persist")
    r = _nouvelle(puce="ESP32S3", blocs=["historique"])
    obj = gen.persist(modele, r, gen.variables(RACINE, r))
    verifie(gen.coherence(modele, r, obj, gen.autoexec(modele, r), gen.listes_cenv(modele, r)), [],
            "historique_esp32 : temoin S3 accepte")


def test_coherence_module_exclu(modele):
    r = _nouvelle(blocs=["modbus"])
    mute = copy.deepcopy(modele)
    next(b for b in mute["blocs"] if b["id"] == "modbus")["solidify"] = []
    for m, attendu, libelle in ((modele, False, "temoin modele intact"), (mute, True, "modbus sans solidify")):
        obj = gen.persist(m, r, gen.variables(RACINE, r))
        refus = gen.coherence(m, r, obj, gen.autoexec(m, r), gen.listes_cenv(m, r))
        verifie(any("controleModbus" in x for x in refus), attendu, f"coherence_module_exclu : {libelle}")
    # module charge par l'autoexec mais exclu, et bloc coche dont la ligne manque a l'autoexec
    l = gen.listes_cenv(modele, r)
    l["exclude"].append("data/fs/controleModbus.be")
    obj = gen.persist(modele, r, gen.variables(RACINE, r))
    verifie(any("controleModbus" in x and "exclu" in x for x in gen.coherence(modele, r, obj, gen.autoexec(modele, r), l)),
            True, "coherence_module_exclu : module de l'autoexec dans exclude")
    texte = "\n".join(x for x in gen.autoexec(modele, r).splitlines() if "controleModbus" not in x)
    verifie(any("controleModbus" in x for x in gen.coherence(modele, r, obj, texte, gen.listes_cenv(modele, r))),
            True, "coherence_module_exclu : bloc ON sans sa ligne d'autoexec")
    r = _nouvelle(blocs=["ads1115"])
    obj = gen.persist(modele, r, gen.variables(RACINE, r))
    refus = gen.coherence(modele, r, obj, gen.autoexec(modele, r), gen.listes_cenv(modele, r))
    verifie(any("i2c" in x and "ads1115" in x for x in refus), True, "coherence : dependance i2c non cochee")


def test_ids_alignes(modele):
    maitre = next(m for m in parc.maitres(RACINE) if m["dossier"].endswith("p4-serveur-modbus"))
    r = _nouvelle(role="esclave", maitre=maitre["env"], id=4, reseau2="")
    v = gen.variables(RACINE, r)
    obj = gen.persist(modele, r, v)
    ids = [obj["serveur"]["rangeExtender"]["id"], obj["serveur"]["udp"]["id"], obj["serveur"]["tcp"]["id"],
           obj["drivers"]["ModBus"]["id"]]
    verifie(ids, [4, 4, 4, 4], "ids_alignes : les 4 chemins valent l'entier 4")
    verifie(all(type(i) is int for i in ids), True, "ids_alignes : entiers")
    verifie((v["reseau1"], v["reseau2"], v["passerelle"], v["ip_maitre"]),
            ("SERVEUR-GARAGE-GATEWAY", "SERVEUR-GARAGE-GATEWAY", "192.168.4.1", maitre["ip"]), "ids_alignes : esclave")
    verifie(obj["serveur"]["rangeExtender"]["ipMaitre"], maitre["ip"], "ids_alignes : ipMaitre du maitre")
    verifie(gen.coherence(modele, r, obj, gen.autoexec(modele, r), gen.listes_cenv(modele, r)), [], "ids_alignes : coherent")
    obj["serveur"]["tcp"]["id"] = 5
    verifie(any("id" in x for x in gen.coherence(modele, r, obj, gen.autoexec(modele, r), gen.listes_cenv(modele, r))),
            True, "ids_alignes : temoin, un id different est refuse")
    r = _nouvelle(id=7)
    verifie(gen.variables(RACINE, r)["id"], 0, "ids_alignes : id force a 0 hors esclave")


def test_aucun_secret_sans_secrets(modele):
    r = _nouvelle(blocs=["udp", "historique"])
    v = gen.variables(RACINE, r)
    vrais = parc.secrets(RACINE, v["reseau1"], v["reseau2"])
    texte = gen.texte_persist(gen.persist(modele, r, v), "\r\n")
    verifie([k for k, s in vrais.items() if s and s in texte], [], "aucun_secret_sans_secrets : aucune valeur reelle")
    verifie(texte.count('"***"'), 5, "aucun_secret_sans_secrets : 5 secrets masques")
    complet = gen.texte_persist(gen.persist(modele, r, v, vrais), "\n")
    verifie(all(s in complet for s in vrais.values() if s), True, "aucun_secret : temoin, les vrais secrets sont poses")
    verifie(texte.endswith("\r\n") and "\r\n\t" in texte and "\n\t" not in texte.replace("\r\n", ""), True,
            "texte_persist : fins de ligne demandees, tabulations")
    verifie(list(json.loads(texte)), list(modele["socle"]), "texte_persist : ordre des cles du socle")


def test_squelettes_compilent(modele):
    fichiers = gen.squelettes(modele, "piscine")
    verifie(sorted(fichiers), ["controlePiscine.be", "piscineFonctions.be"], "squelettes : noms")
    with tempfile.TemporaryDirectory() as t:
        for nom, texte in fichiers.items():
            chemin = Path(t) / nom
            chemin.write_text(texte, encoding="utf-8")
            p = subprocess.run([sys.executable, str(RACINE / "outils_docs/scripts_python/berry/verifie_berry.py"), str(chemin)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            verifie((p.returncode, "avertissement:" in p.stdout + p.stderr), (0, False),
                    f"squelettes_compilent : {nom} compile, aucun avertissement de charte")
            if p.returncode or "avertissement:" in p.stdout:
                print(p.stdout + p.stderr)
        temoin = Path(t) / "temoin.be"
        temoin.write_text(fichiers["controlePiscine.be"].replace("end", "", 1), encoding="utf-8")
        p = subprocess.run([sys.executable, str(RACINE / "outils_docs/scripts_python/berry/verifie_berry.py"), str(temoin)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        verifie(p.returncode != 0, True, "squelettes_compilent : temoin casse refuse")
    verifie(fichiers["controlePiscine.be"].rstrip().endswith("return controlePiscine"), True,
            "squelettes : controlePiscine.be finit par return controlePiscine")
    verifie(json.loads(gen.graphiques_initial()), {"affichage": {}, "groupes": {}}, "graphiques_initial")
    leve = False
    try:
        gen.squelettes(modele, "Thermo-Hygrometre")
    except ValueError:
        leve = True
    verifie(leve, True, "squelettes : nom hors camelCase refuse")


def _refus(fonction, *args):
    try:
        fonction(*args)
    except ValueError as exc:
        return str(exc), True
    return "", False


def test_depot_essai(modele):
    """secret_ambigu, reseau_inconnu, persist_illisible : sur une copie du depot."""
    with tempfile.TemporaryDirectory() as t:
        os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(t) / "outils")
        racine = depot_essai(Path(t) / "depot")
        r = _nouvelle(reseau1="RESEAU-QUI-N-EXISTE-PAS")
        msg, leve = _refus(gen.secrets_reponses, racine, r)
        verifie((leve, "RESEAU-QUI-N-EXISTE-PAS" in msg), (True, True), "reseau_inconnu : refus qui nomme le reseau")
        grenier = racine / "data/etage2/tasmota32s3-grenier/_persist.json"
        donnees = json.loads(grenier.read_text(encoding="utf-8-sig"))
        ancien = donnees["serveur"]["wifi"]["reseau1"]["mdpWifi"]
        donnees["serveur"]["wifi"]["reseau1"]["mdpWifi"] = "valeur-differente-pour-l-essai"
        grenier.write_text(json.dumps(donnees, ensure_ascii=False), encoding="utf-8")
        msg, leve = _refus(gen.secrets_reponses, racine, _nouvelle())
        verifie((leve, "MAISON" in msg), (True, True), "secret_ambigu : refus qui nomme le reseau")
        verifie(("valeur-differente-pour-l-essai" in msg) or (ancien in msg), False, "secret_ambigu : aucune valeur")
        grenier.write_text('{"serveur": {', encoding="utf-8")       # persist_illisible
        s = gen.secrets_reponses(racine, _nouvelle())
        verifie(sorted(s), ["ap", "ftp", "mqtt", "wifi1", "wifi2"], "persist_illisible : secrets sans planter")
        verifie(parc.illisibles(racine), ["data/etage2/tasmota32s3-grenier/_persist.json"], "persist_illisible : signale")
        verifie(gen.variables(racine, _nouvelle())["passerelle"], "192.168.0.254", "persist_illisible : variables")


def principal():
    if "--temoin" in sys.argv:
        modele = json.loads(Path(sys.argv[sys.argv.index("--temoin") + 1]).read_text(encoding="utf-8"))
        restants, _ = rejeu(modele)
        for dossier, liste in sorted(restants.items()):
            print(f"ROUGE {dossier} : {', '.join(liste)}")
        print("cartes en ecart :", sorted(restants) or "aucune")
        return 1 if restants else 0
    modele = apm.charge_modele(RACINE)
    for test in (test_rejeu_parc, test_autoexec_cuve, test_listes_cuve, test_historique_esp32,
                 test_coherence_module_exclu, test_ids_alignes, test_aucun_secret_sans_secrets,
                 test_squelettes_compilent, test_depot_essai):
        test(modele)
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
