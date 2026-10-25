"""Banc de fichiers_berry_creation (nouvel env a partir d'une carte modele).

Code de sortie 0 = vert. Le depot d'essai est une COPIE des vrais .ini, du vrai user_config_override.h et
des vrais dossiers data/<lieu>/<carte> (lecture seule du depot), dans un dossier temporaire : la creation
y est faite pour de vrai, jamais dans le depot. A lancer avec le Python du penv (ProjectConfig).
"""

import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import build_envs
import fichiers_berry_creation as fbc
import fichiers_berry_ini as fbi
from fichiers_berry_creation import Creation

ECHECS = []
RACINE = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))
RIDEAU = "tasmota32s3-garage-rideau-garage-modbus"
DOSSIER_RIDEAU = "data/garage/tasmota32s3-rideau-garage-modbus"
BASE_RIDEAU = "tasmota32s3-base-N16R8-sans-ecran"
SANS_BUILD = lambda: []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def depot_essai(dossier):
    racine = Path(dossier)
    for f in fbi.FICHIERS_INI + (fbc.FICHIER_H, "platformio.ini", "platformio_tasmota32.ini"):
        if (RACINE / f).is_file():
            (racine / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(RACINE / f, racine / f)
    for carte in (RACINE / "data").glob("*/*"):
        if carte.is_dir() and "sauvegarde" not in carte.name and carte.parent.name not in ("fs", "sd", "json"):
            shutil.copytree(carte, racine / carte.relative_to(RACINE))
    return racine


def creation(nom="porte-test", lieu="garage", modele=RIDEAU, base=BASE_RIDEAU, **identite):
    ident = fbc.identite_par_defaut(lieu, nom)
    ident.update(identite)
    return Creation(modele=modele, base=base, lieu=lieu, nom=nom, identite=ident)


def cree(racine, c):
    p = fbc.prepare_creation(racine, c)
    verifie(p["refus"], [], f"prepare {c.nom} : aucun refus")
    return p, fbc.cree(racine, c, p["empreinte"], SANS_BUILD)


def texte(racine, f):
    return (racine / f).read_bytes().decode("utf-8", errors="surrogateescape")


def fin_section(h, i):
    """Debut de la section suivante de la chaine des firmwares (8 espaces : les #endif internes en ont 12)."""
    return i + 1 + re.search(r"\n {8}(// -- Options for|#elif\b|#else\b|#endif\b)", h[i + 1:]).start() + 1


def section_cenv(racine, env):
    lignes = fbi.decoupe(texte(racine, fbi.FICHIER_CENV))
    i = lignes.index(f"[env:{env}]")
    j = next((k for k in range(i + 1, len(lignes)) if lignes[k].startswith("[")), len(lignes))
    return lignes[i:j]


def test_nom_et_define():
    verifie(fbc.nom_env(BASE_RIDEAU, "garage", "porte-test"), "tasmota32s3-garage-porte-test", "nom_env")
    verifie(fbc.define(BASE_RIDEAU, "garage", "porte-test"), "FIRMWARE_ESP32S3_GARAGE_PORTE_TEST", "define S3")
    verifie(fbc.define("tasmota32p4-base-devkit", "garage", "x"), "FIRMWARE_ESP32P4_GARAGE_X", "define P4")
    verifie(fbc.define("tasmota32-base", "cave", "x"), "FIRMWARE_ESP32_CAVE_X", "define ESP32")
    verifie(fbc.identite_par_defaut("garage", "porte-test"),
            {"CODE_IMAGE_STR": "Porte test", "PROJECT": "PORTE-TEST-GARAGE", "WIFI_IP_ADDRESS": "0.0.0.0",
             "WIFI_RGX_SSID": "PORTE-TEST-GARAGE-GATEWAY", "MQTT_CLIENT_ID": "PORTE-TEST-GARAGE",
             "MQTT_TOPIC": "garage/porte-test", "MQTT_GRPTOPIC": "tasmotas/garage", "FRIENDLY_NAME": "Porte test"},
            "identite_par_defaut (modele : le rideau)")


def test_section_cenv(racine):
    cree(racine, creation())
    env = "tasmota32s3-garage-porte-test"
    sec = section_cenv(racine, env)
    actives = [l for l in sec if not l.lstrip().startswith(";")]
    verifie([l for l in actives if re.match(r"(upload|monitor)_port\s*=", l)], [], "section cenv : ports COM non recopies")
    from platformio.project.config import ProjectConfig
    ici = os.getcwd()
    os.chdir(racine)
    try:
        conf = ProjectConfig(str(racine / "platformio.ini"))
        verifie(conf.get(f"env:{env}", "extends"), [f"env:{BASE_RIDEAU}"], "section cenv : extends = base choisie")
        flags = " ".join(conf.get(f"env:{env}", "build_flags"))
        verifie(("FIRMWARE_ESP32S3_GARAGE_PORTE_TEST" in flags, "FIRMWARE_ESP32S3_RIDEAU_GARAGE_MODBUS" in flags),
                (True, False), "section cenv : define remplace (relu par PlatformIO)")
    finally:
        os.chdir(ici)
    ini = fbi.lit_sections(racine)
    up = [e.chemin for e in fbi.resout(ini, env, "custom_files_upload")]
    verifie(up, [e.chemin for e in fbi.resout(ini, BASE_RIDEAU, "custom_files_upload")] + ["data/garage/tasmota32s3-porte-test"],
            "section cenv : custom_files_upload = base + nouveau dossier")


def test_chemins_reecrits(racine):
    cree(racine, creation())
    so = [e.chemin for e in fbi.resout(fbi.lit_sections(racine), "tasmota32s3-garage-porte-test", "custom_berry_solidify")]
    verifie(("data/garage/tasmota32s3-porte-test/controleRideau.be" in so, any(DOSSIER_RIDEAU in c for c in so)),
            (True, False), "chemins du dossier modele reecrits vers le nouveau")
    verifie((racine / "data/garage/tasmota32s3-porte-test/controleRideau.be").is_file(), True, "dossier copie")


def test_section_h(racine):
    avant = texte(racine, fbc.FICHIER_H)
    cree(racine, creation())
    h = texte(racine, fbc.FICHIER_H)
    i = h.index("#elif defined(FIRMWARE_ESP32S3_GARAGE_PORTE_TEST)")
    fin = fin_section(h, i)
    debut = h.rindex("        // -- Options for", 0, i)
    sec = h[i:fin]
    for nom, val in fbc.identite_par_defaut("garage", "porte-test").items():
        if re.search(r"#define\s+" + nom + r"\s", sec):
            verifie(re.search(r"#define\s+" + nom + r'\s+"' + re.escape(val) + '"', sec) is not None, True,
                    f"section .h : {nom} = {val}")
    verifie("Backlog Hostname PORTE-TEST-GARAGE" in sec, True, "section .h : Hostname de USER_BACKLOG")
    verifie('\\"NAME\\":\\"Porte test\\"' in sec, True, "section .h : NAME du USER_TEMPLATE")
    verifie(h.count("#endif") - avant.count("#endif"), sec.count("#endif"), "section .h : chaine #if/#elif intacte")
    verifie(h[:debut] + h[fin:] == avant, True, "section .h : un seul bloc ajoute, le reste du .h inchange")
    verifie(h[debut:i].startswith("        // -- Options for tasmota32s3-garage-porte-test"), True,
            "section .h : commentaire d'en-tete au nom du nouvel env")


def test_modele_cave(racine):
    c = creation(nom="essai", lieu="cave", modele="tasmota32-cave-serveur-rly", base="tasmota32-base")
    p, _ = cree(racine, c)
    h = texte(racine, fbc.FICHIER_H)
    verifie(h.count("#elif defined(FIRMWARE_ESP32_CAVE_ESSAI)"), 1, "modele cave (#if ... || ...) : copie en #elif")
    verifie(h.count("#if defined(FIRMWARE_ESP32_CAVE_SERVEUR_RLY) || defined(FIRMWARE_ESP32S3_CAVE_SERVEUR_RLY)"), 1,
            "modele cave : ouverture de la chaine intacte")
    verifie(any("FIRMWARE_ESP32S3_CAVE_SERVEUR_RLY" in a for a in p["avertissements"]), True,
            "modele cave : conditions internes signalees")
    i = h.index("#elif defined(FIRMWARE_ESP32_CAVE_ESSAI)")
    bloc = h[i:fin_section(h, i)]
    verifie(re.findall(r"Hostname\s+([^\s\";]+)", bloc), [c.identite["PROJECT"]],
            "modele cave (Backlog Module 0; Hostname X) : Hostname remplace par PROJECT")


def test_persist_octets(racine):
    modele = (racine / DOSSIER_RIDEAU / "_persist.json").read_bytes()
    cree(racine, creation())
    neuf = (racine / "data/garage/tasmota32s3-porte-test/_persist.json").read_bytes()
    a, b = json.loads(modele.decode("utf-8")), json.loads(neuf.decode("utf-8"))
    ident = fbc.identite_par_defaut("garage", "porte-test")
    for cle, champ in fbc.CLES_PERSIST.items():
        noeud = b
        for k in cle.split("."):
            noeud = noeud[k]
        verifie(noeud, ident[champ], f"persist : {cle} = {champ}")
    # en remettant les anciennes valeurs dans le nouveau texte, on doit retrouver le modele octet pour octet
    t = neuf.decode("utf-8", errors="surrogateescape")
    for (debut, fin), cle in sorted(((v, k) for k, v in fbc.spans_json(t).items()
                                     if ".".join(map(str, k)) in fbc.CLES_PERSIST), reverse=True):
        ancien = a
        for k in cle:
            ancien = ancien[k]
        t = t[:debut] + json.dumps(ancien, ensure_ascii=False)[1:-1] + t[fin:]
    verifie(t.encode("utf-8", errors="surrogateescape") == modele, True, "persist : reste du fichier octet pour octet")


def test_insertion_lieu(racine):
    cree(racine, creation())
    envs = fbi.lit_sections(racine).envs_cenv()
    garage = [e for e in envs if e.split("-")[1] == "garage"]
    verifie(garage[-1], "tasmota32s3-garage-porte-test", "insertion : apres le dernier env du garage")
    cree(racine, creation(nom="pompe", lieu="jardin2"))
    t = texte(racine, fbi.FICHIER_CENV)
    verifie(t.index("; LOCALISATION: JARDIN2") < t.index("[env:tasmota32s3-jardin2-pompe]"), True,
            "insertion : nouveau lieu -> nouveau bandeau en fin de fichier")


def test_refus(racine):
    p = fbc.prepare_creation(racine, creation(MQTT_TOPIC="garage/rideau"))
    verifie((any("garage/rideau" in r for r in p["refus"]), any("garage/rideau" in a for a in p["avertissements"])),
            (False, True), "topic deja pris par le rideau : avertissement, plus un refus (carte remplacee)")
    refus = fbc.prepare_creation(racine, creation(nom="rideau-garage-modbus"))["refus"]
    verifie(any("existe" in r for r in refus), True, "refus : env existant")
    refus = fbc.prepare_creation(racine, creation(nom="Porte_Test"))["refus"]
    verifie(len(refus) > 0, True, "refus : nom invalide")
    c = creation()
    p = fbc.prepare_creation(racine, c)
    for builds in (lambda: ["pio run"], lambda: None):
        try:
            fbc.cree(racine, c, p["empreinte"], builds)
            verifie("cree", "refus", "refus build")
        except RuntimeError:
            verifie((racine / "data/garage/tasmota32s3-porte-test").exists(), False, "refus build : rien de cree")
    autre = creation(WIFI_IP_ADDRESS="192.168.0.250")       # saisie changee apres « Voir le diff »
    try:
        fbc.cree(racine, autre, p["empreinte"], SANS_BUILD)
        verifie("cree", "refus", "refus : identite changee depuis le diff")
    except RuntimeError:
        verifie((racine / "data/garage/tasmota32s3-porte-test").exists(), False, "refus identite changee : rien de cree")
    (racine / fbc.FICHIER_H).write_bytes((racine / fbc.FICHIER_H).read_bytes() + b"// touche\r\n")
    try:
        fbc.cree(racine, c, p["empreinte"], SANS_BUILD)
        verifie("cree", "refus", "refus empreinte")
    except RuntimeError:
        verifie((racine / "data/garage/tasmota32s3-porte-test").exists(), False, "refus empreinte : rien de cree")


def test_identite_invalide(racine):
    for champ, valeur in (("PROJECT", "PORTE; Reset 1"), ("PROJECT", "PORTE TEST"), ("MQTT_TOPIC", "garage/#"),
                          ("MQTT_CLIENT_ID", "porte+"), ("FRIENDLY_NAME", "Porte;x"), ("WIFI_IP_ADDRESS", "192.168.0.1 ")):
        refus = fbc.prepare_creation(racine, creation(**{champ: valeur}))["refus"]
        verifie(any(champ in r for r in refus), True, f"identite invalide refusee : {champ} = {valeur!r}")
    verifie(fbc.prepare_creation(racine, creation(FRIENDLY_NAME="Porte du garage"))["refus"], [],
            "FRIENDLY_NAME avec espaces : accepte")


def test_define_en_commentaire(racine):
    for f, ligne in ((fbi.FICHIER_CENV, b"; ancien : -D FIRMWARE_ESP32S3_GARAGE_PORTE_TEST\n"),
                     (fbc.FICHIER_H, b"// ancien : FIRMWARE_ESP32S3_GARAGE_PORTE_TEST\r\n")):
        (racine / f).write_bytes((racine / f).read_bytes() + ligne)
    verifie(fbc.prepare_creation(racine, creation())["refus"], [], "define cite en commentaire seulement : pas un refus")


def test_nom_base(racine):
    for lieu, nom in (("garage", "base-x"), ("base", "porte"), ("garage", "porte-base")):
        try:
            refus = fbc.prepare_creation(racine, creation(lieu=lieu, nom=nom))["refus"]
            verifie(any("base" in r for r in refus), True, f"nom d'env avec « -base » : refus clair ({lieu}/{nom})")
        except Exception as erreur:
            verifie(repr(erreur), "un refus", f"nom d'env avec « -base » : refus clair ({lieu}/{nom})")


def test_commentaire_dans_upload(racine):
    f = racine / fbi.FICHIER_CENV
    t = f.read_bytes().decode("utf-8")
    eol = "\r\n" if "\r\n" in t else "\n"
    a = "custom_files_upload     =   ${env:tasmota32s3-base-N16R8.custom_files_upload}" + eol
    debut = t.index("[env:" + RIDEAU + "]")
    i = t.index(a, debut)
    f.write_bytes((t[:i + len(a)] + "; commentaire au milieu de la liste" + eol + t[i + len(a):]).encode("utf-8"))
    cree(racine, creation())
    up = [e.chemin for e in fbi.resout(fbi.lit_sections(racine), "tasmota32s3-garage-porte-test", "custom_files_upload")]
    verifie((up.count("data/garage/tasmota32s3-porte-test"), DOSSIER_RIDEAU in up), (1, False),
            "modele avec un commentaire dans custom_files_upload : liste remplacee en entier")


def test_diff_masque(racine):
    p = fbc.prepare_creation(racine, creation())
    h = texte(racine, fbc.FICHIER_H)
    i = h.index("#elif defined(FIRMWARE_ESP32S3_RIDEAU_GARAGE_MODBUS)")
    secrets = re.findall(r'#define\s+\w*(?:PASS|PWD)\w*\s+"([^"]+)"', h[i:fin_section(h, i)])
    persist = texte(racine, DOSSIER_RIDEAU + "/_persist.json")
    secrets += [v for v in re.findall(r'"\w*(?:[Mm]dp|[Pp]ass|[Pp]wd)\w*"\s*:\s*"([^"]+)"', persist)]
    verifie(len(secrets) > 0, True, "diff masque : le modele porte bien des secrets (sinon test vide)")
    # le NOMBRE seulement : un echec ne doit jamais imprimer les mots de passe qu'il a trouves
    verifie(sum(s in p["diff"] for s in secrets), 0, "diff masque : aucun secret en clair (nombre trouve)")
    verifie("***" in p["diff"], True, "diff masque : marque de masquage presente")


def test_sauvegarde(racine):
    avant_h = (racine / fbc.FICHIER_H).read_bytes()
    _, r = cree(racine, creation())
    verifie((Path(r["sauvegarde"]) / fbc.FICHIER_H).read_bytes(), avant_h, "creation : sauvegarde horodatee du .h d'avant")
    verifie([f for f in (fbc.FICHIER_H, fbi.FICHIER_CENV) if (racine / (f + ".bak")).exists()], [],
            "creation : plus de .bak commun avec la page build")


def test_creation_atomique(racine):
    import fichiers_berry_sauvegarde as fbs
    avant = {f: (racine / f).read_bytes() for f in (fbc.FICHIER_H, fbi.FICHIER_CENV)}
    c = creation()
    p = fbc.prepare_creation(racine, c)
    origine = fbs.Transaction.ecrit

    def panne(self, rel, octets):                   # le cenv, ecrit en dernier, ne passe pas
        if rel == fbi.FICHIER_CENV:
            raise OSError("panne simulee")
        return origine(self, rel, octets)
    fbs.Transaction.ecrit = panne
    try:
        fbc.cree(racine, c, p["empreinte"], SANS_BUILD)
        verifie("cree", "panne", "creation atomique : la panne remonte")
    except OSError:
        pass
    finally:
        fbs.Transaction.ecrit = origine
    verifie({f: (racine / f).read_bytes() for f in avant} == avant, True, "creation atomique : .h et cenv remis")
    verifie((racine / "data/garage/tasmota32s3-porte-test").exists(), False, "creation atomique : dossier copie retire")
    verifie(fbc.prepare_creation(racine, c)["refus"], [], "creation atomique : un nouvel essai n'est pas refuse")


def test_copies_temporaires_ignorees(racine):
    """Un build interrompu laisse dans le dossier du modele des copies de data/fs, json/ et sd/ : non recopiees."""
    (racine / "data/fs").mkdir(parents=True, exist_ok=True)
    (racine / "data/fs/copieFonctions.be").write_bytes(b"# module commun")
    shutil.copyfile(racine / "data/fs/copieFonctions.be", racine / DOSSIER_RIDEAU / "copieFonctions.be")
    for sous in ("json", "sd"):
        (racine / DOSSIER_RIDEAU / sous).mkdir()
        (racine / DOSSIER_RIDEAU / sous / "f.txt").write_bytes(b"x")
    cree(racine, creation())
    neuf = racine / "data/garage/tasmota32s3-porte-test"
    verifie(((neuf / "copieFonctions.be").exists(), (neuf / "json").exists(), (neuf / "sd").exists(),
             (neuf / "autoexec.be").is_file()), (False, False, False, True),
            "creation : copies temporaires d'un build non recopiees, vrais fichiers copies")


def test_vu_par_build(racine):
    cree(racine, creation())
    envs = {e.nom: e.famille for e in build_envs.liste_envs(racine)}
    verifie(envs.get("tasmota32s3-garage-porte-test"), "cartes", "nouvelle carte vue par la page build (famille cartes)")


def principal():
    test_nom_et_define()
    for test in (test_section_cenv, test_chemins_reecrits, test_section_h, test_modele_cave, test_persist_octets,
                 test_insertion_lieu, test_refus, test_identite_invalide, test_define_en_commentaire, test_nom_base, test_commentaire_dans_upload, test_diff_masque, test_sauvegarde, test_creation_atomique,
                 test_copies_temporaires_ignorees, test_vu_par_build):
        with tempfile.TemporaryDirectory() as t:
            os.environ["OUTILS_TASMOTA_DOSSIER"] = os.path.join(t, "outils")    # sauvegardes hors du vrai dossier
            try:
                test(depot_essai(t))
            except Exception as exc:
                verifie(repr(exc), "pas d'exception", test.__name__)
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s) : {ECHECS}"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
