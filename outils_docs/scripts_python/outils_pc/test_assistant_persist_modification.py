"""Banc de assistant_persist_modification : groupes « charge » (A4, recenser et relire les cartes) et « modification »
(A5, preparer et ecrire l'ecart A -> B).

Code de sortie 0 = vert. Depot d'essai dans un dossier temporaire, jamais le vrai depot. Aucun mot de passe imprime.
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" -u outils_docs/scripts_python/outils_pc/test_assistant_persist_modification.py
"""

import hashlib
import json
import os
import re
import sys
import tempfile
from dataclasses import asdict, replace
from pathlib import Path

import assistant_persist_creation as apc
import assistant_persist_modification as apmod
import assistant_persist_parc as parc
import fichiers_berry_creation as fbc
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi
from assistant_persist_generation import Reponses
from test_assistant_persist_creation import BLOCS, ENV, MAITRE, RACINE, SANS_BUILD, depot, reponses, secrets_reels

ECHECS = []
TEMOIN = "TEMOIN-SECRET-4242"
SORTIES = []                    # tout ce que les fonctions renvoient ou levent : relu a la fin, aucun secret permis
GARAGE = (MAITRE, "tasmota32s3-garage-capteurs-cuve-modbus", "tasmota32s3-garage-rideau-garage-modbus")
SANS_RE = [b for b in BLOCS if b != "rangeExtender"]    # un esclave relu n'a jamais le bloc rangeExtender


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def leve(exc, fonction, *args):
    try:
        fonction(*args)
    except exc as e:
        return str(e)
    return None


def test_charge(t):
    racine = depot(t)
    os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(t) / "outils")
    # cartes_du_parc
    cartes = apmod.cartes(racine)
    envs = [c["env"] for c in cartes]
    attendu = [e["nom"] for e in fbe.envs_proposes(racine) if e["famille"] == "cartes"
               and (racine / fbe.dossier_carte(e["nom"]) / "_persist.json").is_file()]
    verifie(envs, attendu, "cartes_du_parc : les cartes du depot d'essai")
    verifie(MAITRE in envs and len(envs) > 1, True, "cartes_du_parc : le maitre y est")
    verifie([e for e in envs if fbe.est_base(e)], [], "cartes_du_parc : aucune base")
    verifie(set(cartes[0]), {"env", "dossier", "puce"}, "cartes_du_parc : champs")
    verifie(next(c["dossier"] for c in cartes if c["env"] == MAITRE), fbe.dossier_carte(MAITRE), "cartes_du_parc : dossier")
    # charge_carte_creee
    r = reponses()
    apc.cree(racine, r, apc.prepare(racine, r)["empreinte"], SANS_BUILD)
    c = apmod.charge_env(racine, ENV)
    rep = c["reponses"]
    for champ in ("puce", "lieu", "nom", "role", "maitre", "id", "ip", "metiers"):
        verifie(rep[champ], asdict(r)[champ], f"charge_carte_creee : {champ}")
    verifie(sorted(rep["blocs"]), sorted(b for b in r.blocs if b != "rangeExtender"), "charge_carte_creee : blocs (rangeExtender : maitre seulement)")
    verifie(rep["base"] != "" and "define" in rep and rep["define"].startswith("FIRMWARE_"), True,
            "charge_carte_creee : base et define relus")
    verifie((c["env"], c["reglages_propres"], c["avertissements"]), (ENV, 0, []), "charge_carte_creee : aucun reglage propre")
    # carte du parc, avec une cle propre : comptee
    persist = racine / fbe.dossier_carte(MAITRE) / "_persist.json"
    j = json.loads(persist.read_text(encoding="utf-8"))
    j["cle_propre_a_la_carte"] = 1
    persist.write_text(json.dumps(j, indent="\t"), encoding="utf-8")
    verifie(apmod.charge_env(racine, MAITRE)["reglages_propres"] >= 1, True, "reglages_propres : cle propre comptee")
    # charge_inconnu
    verifie(leve(LookupError, apmod.charge_env, racine, "tasmota32s3-nulle-part") is not None, True, "charge_inconnu : LookupError")
    base = next(e["nom"] for e in fbe.envs_proposes(racine) if e["famille"] == "bases")
    verifie(leve(LookupError, apmod.charge_env, racine, base) is not None, True, "charge_inconnu : une base -> LookupError")
    # charge_persist_casse
    persist.write_text('{"serveur": {"wifi": "' + TEMOIN + '"', encoding="utf-8")
    msg = leve(ValueError, apmod.charge_env, racine, MAITRE)
    verifie((msg is not None, TEMOIN in (msg or "")), (True, False), "charge_persist_casse : ValueError sans valeur")
    persist.write_text(json.dumps({"serveur": {"wifi": TEMOIN}}), encoding="utf-8")
    msg = leve(ValueError, apmod.charge_env, racine, MAITRE)
    verifie((msg is not None, TEMOIN in (msg or "")), (True, False), "charge_persist_incomplet : ValueError sans valeur")
    # aucun_secret
    racine2 = depot(Path(t) / "b")
    sortie = json.dumps(apmod.charge_env(racine2, MAITRE), ensure_ascii=False) + json.dumps(c, ensure_ascii=False)
    verifie([s for s in secrets_reels() if s in sortie], [], "aucun_secret : charge_env du maitre")


# ---- groupe « modification » (A5) ------------------------------------------------------------------------------------
def lit(racine, rel):
    p = Path(racine) / rel
    return p.read_bytes() if p.is_file() else None


def reps(racine, env):
    return Reponses(**apmod.charge_env(racine, env)["reponses"])


def prepare(racine, env, r):
    p = apmod.prepare_modification(racine, env, r)
    SORTIES.append(json.dumps(p, ensure_ascii=False))
    return p


def modifie(racine, env, r, empreinte=None, builds=SANS_BUILD):
    """(resultat, message) : RuntimeError et ValueError rendus en texte, relus par aucun_secret."""
    p = prepare(racine, env, r)
    try:
        res = apmod.modifie(racine, env, r, p["empreinte"] if empreinte is None else empreinte, builds)
        SORTIES.append(json.dumps(res, ensure_ascii=False))
        return res, None
    except (RuntimeError, ValueError) as exc:
        SORTIES.append(str(exc))
        return None, f"{type(exc).__name__} : {exc}"


def fichiers(racine, env):
    d = fbe.dossier_carte(env)
    return {f: hashlib.sha256(lit(racine, f) or b"").hexdigest() for f in (fbi.FICHIER_CENV, fbc.FICHIER_H, d + "/_persist.json", d + "/autoexec.be")}


def section(racine, env, rel):
    """Lignes de la section de l'env : cenv ([env:...]) ou .h (#elif defined(define))."""
    lignes = fbi.decoupe(fbc._texte(lit(racine, rel)))
    if rel == fbi.FICHIER_CENV:
        a, b = fbc._regions(lignes)["env:" + env]
    else:
        a, _, b = fbc._section_h(lignes, fbx_define(racine, env))
    return lignes[a:b]


def fbx_define(racine, env):
    import fichiers_berry_suppression as fbx
    return fbx.define_de(fbi.lit_sections(racine), env)


def meme_carte(r1, r2, env, libelle):
    """Memes persist (JSON), autoexec, section du cenv et section du .h dans les deux depots."""
    d = fbe.dossier_carte(env)
    verifie(json.loads(lit(r1, d + "/_persist.json")) == json.loads(lit(r2, d + "/_persist.json")), True, libelle + " : persist")
    verifie(lit(r1, d + "/autoexec.be") == lit(r2, d + "/autoexec.be"), True, libelle + " : autoexec")
    verifie(section(r1, env, fbi.FICHIER_CENV) == section(r2, env, fbi.FICHIER_CENV), True, libelle + " : section du cenv")
    verifie(section(r1, env, fbc.FICHIER_H) == section(r2, env, fbc.FICHIER_H), True, libelle + " : section du .h")


def neuf(t, nom, r):
    """Oracle : le meme env cree d'emblee avec les reponses de creation r, dans un depot a part."""
    racine = depot(Path(t) / nom)
    r = replace(r, squelettes=True)
    p = apc.prepare(racine, r)
    verifie(p["refus"], [], f"oracle {nom} : creation sans refus")
    apc.cree(racine, r, p["empreinte"], SANS_BUILD)
    return racine


def cree_piscine(t, nom, blocs):
    racine = depot(Path(t) / nom)
    os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(t) / "outils")
    r = reponses(blocs=list(blocs))
    apc.cree(racine, r, apc.prepare(racine, r)["empreinte"], SANS_BUILD)
    return racine


def test_modification(t):
    racine = cree_piscine(t, "m", SANS_RE)
    r0 = reps(racine, ENV)
    d = fbe.dossier_carte(ENV)
    origine = fichiers(racine, ENV)
    # rien_change_ecart_vide
    p = prepare(racine, ENV, r0)
    verifie((p["vide"], p["refus"], p["diff"], p["env"], p["dossier"]), (True, [], "", ENV, d), "rien_change_ecart_vide : prepare")
    res, msg = modifie(racine, ENV, r0)
    verifie((res, (msg or "").startswith("ValueError")), (None, True), "rien_change_ecart_vide : modifie -> ValueError")
    verifie(fichiers(racine, ENV), origine, "rien_change_ecart_vide : rien d'ecrit")
    # bloc_retire (oracle : l'env cree d'emblee sans le bloc) puis aller_retour (bloc re-ajoute)
    r1 = replace(r0, blocs=[b for b in r0.blocs if b != "historique"])
    p = prepare(racine, ENV, r1)
    verifie((p["vide"], p["refus"]), (False, []), "bloc_retire : prepare")
    verifie((p["diff"] != "", p["chemins"] != []), (True, True), "bloc_retire : diff et chemins du persist non vides")
    res, msg = modifie(racine, ENV, r1)
    verifie((res is not None and res["modifie"], msg), (True, None), "bloc_retire : modifie")
    meme_carte(racine, neuf(t, "o1", reponses(blocs=[b for b in SANS_RE if b != "historique"])), ENV, "bloc_retire : = env cree sans le bloc")
    verifie(fichiers(racine, ENV) != origine, True, "bloc_retire : fichiers changes")
    p = prepare(racine, ENV, r0)                                  # bloc_ajoute : le retour
    res, msg = modifie(racine, ENV, r0)
    verifie((res is not None, msg), (True, None), "bloc_ajoute : modifie")
    verifie(fichiers(racine, ENV), origine, "aller_retour : fichiers (cenv, .h, persist, autoexec) identiques octet pour octet")
    # identite_changee
    r2 = replace(r0, hostname="PISCINE2-GARAGE", client="PISCINE2-GARAGE", topic="garage/piscine2", ssid_ap="PISCINE2-GARAGE-GATEWAY")
    res, msg = modifie(racine, ENV, r2)
    verifie((res is not None, msg), (True, None), "identite_changee : modifie")
    pers = json.loads(lit(racine, d + "/_persist.json"))
    verifie((pers["serveur"]["hostname"], pers["serveur"]["mqtt"]["topic"]), ("PISCINE2-GARAGE", "garage/piscine2"), "identite_changee : persist")
    h = "\n".join(section(racine, ENV, fbc.FICHIER_H))
    verifie((re.search(r'#define\s+PROJECT\s+"PISCINE2-GARAGE"', h) is not None, '"garage/piscine2"' in h), (True, True), "identite_changee : .h")
    meme_carte(racine, neuf(t, "o2", reponses(blocs=SANS_RE, hostname="PISCINE2-GARAGE", client="PISCINE2-GARAGE", topic="garage/piscine2", ssid_ap="PISCINE2-GARAGE-GATEWAY")), ENV, "identite_changee : = env cree avec cette identite")
    res, msg = modifie(racine, ENV, r0)
    verifie(fichiers(racine, ENV), origine, "identite_changee : retour octet pour octet")
    # retouches_gardees
    j = json.loads(lit(racine, d + "/_persist.json"))
    j["cle_propre_a_la_carte"] = {"a": 1}
    (racine / d / "_persist.json").write_bytes(json.dumps(j, indent="\t", ensure_ascii=False).encode("utf-8"))
    cenv = lit(racine, fbi.FICHIER_CENV).decode("utf-8")
    eol_c = fbc._eol(cenv)
    cenv = cenv.replace(f"[env:{ENV}]{eol_c}", f"[env:{ENV}]{eol_c}upload_port = COM7{eol_c}", 1)
    (racine / fbi.FICHIER_CENV).write_bytes(cenv.encode("utf-8"))
    h_txt = lit(racine, fbc.FICHIER_H).decode("utf-8", errors="surrogateescape")
    cle = f"#elif defined({fbx_define(racine, ENV)})"
    eol = fbc._eol(h_txt)
    h_txt = h_txt.replace(cle + eol, cle + eol + "            #define MA_LIGNE_A_MOI 1" + eol, 1)
    verifie("MA_LIGNE_A_MOI" in h_txt, True, "retouches_gardees : ligne posee dans le .h d'essai")
    (racine / fbc.FICHIER_H).write_bytes(h_txt.encode("utf-8", errors="surrogateescape"))
    r3 = replace(r0, blocs=[b for b in r0.blocs if b != "ruban"])
    res, msg = modifie(racine, ENV, r3)
    verifie((res is not None, msg), (True, None), "retouches_gardees : modifie")
    verifie("cle_propre_a_la_carte" in json.loads(lit(racine, d + "/_persist.json")), True, "retouches_gardees : cle du persist")
    verifie("upload_port = COM7" in section(racine, ENV, fbi.FICHIER_CENV), True, "retouches_gardees : ligne du cenv")
    verifie("            #define MA_LIGNE_A_MOI 1" in section(racine, ENV, fbc.FICHIER_H), True, "retouches_gardees : ligne du .h")
    verifie(fichiers(racine, ENV)[fbc.FICHIER_H] != hashlib.sha256(h_txt.encode("utf-8", errors="surrogateescape")).hexdigest(), True, "retouches_gardees : l'ecart est applique")
    # ligne_retouchee_refus : la ligne de A visee par l'ecart a ete modifiee a la main
    racine = cree_piscine(t, "n", SANS_RE)
    h_txt = lit(racine, fbc.FICHIER_H).decode("utf-8", errors="surrogateescape")
    deb = h_txt.index(f"#elif defined({fbx_define(racine, ENV)})")
    i = h_txt.index("#define USE_MODBUS", deb)
    h_txt = h_txt[:i] + "#define USE_MODBUS 2 // a la main" + h_txt[h_txt.index("\n", i):]
    (racine / fbc.FICHIER_H).write_bytes(h_txt.encode("utf-8", errors="surrogateescape"))
    origine = fichiers(racine, ENV)
    r4 = replace(reps(racine, ENV), blocs=[b for b in SANS_RE if b != "modbus"])
    p = prepare(racine, ENV, r4)
    verifie((len(p["refus"]) >= 1, any("USE_MODBUS" in x and fbc.FICHIER_H in x for x in p["refus"])), (True, True), "ligne_retouchee_refus : prepare cite le fichier et la ligne")
    res, msg = modifie(racine, ENV, r4)
    verifie((res, (msg or "").startswith("RuntimeError")), (None, True), "ligne_retouchee_refus : modifie -> RuntimeError")
    verifie(fichiers(racine, ENV), origine, "ligne_retouchee_refus : toute la modification refusee, rien d'ecrit")
    # figes
    for champ, valeur in (("nom", "autre"), ("lieu", "ailleurs"), ("puce", "ESP32"), ("base", next(e["nom"] for e in fbe.envs_proposes(racine) if e["famille"] == "bases" and e["nom"] != reps(racine, ENV).base and e["nom"].startswith("tasmota32s3")))):
        r5 = replace(reps(racine, ENV), **{champ: valeur})
        p = prepare(racine, ENV, r5)
        verifie((len(p["refus"]) >= 1, any("7800" in x for x in p["refus"])), (True, True), f"figes : {champ} change -> refus (renommer : page 7800)")
    # empreinte_perimee, build_en_cours, build_inconnu
    r6 = replace(reps(racine, ENV), ip="192.168.0.77")
    p = prepare(racine, ENV, r6)
    verifie(p["vide"], False, "empreinte_perimee : l'IP change")
    res, msg = modifie(racine, ENV, r6, empreinte=p["empreinte"])
    verifie(msg, None, "empreinte_perimee : empreinte lue -> ecrit")
    verifie(modifie(racine, ENV, replace(r6, ip="192.168.0.78"), empreinte=p["empreinte"])[1] is not None, True, "empreinte_perimee : saisie changee -> RuntimeError")
    racine = cree_piscine(t, "p", SANS_RE)
    r7 = replace(reps(racine, ENV), ip="192.168.0.77")
    origine = fichiers(racine, ENV)
    verifie((modifie(racine, ENV, r7, builds=lambda: ["pio run"])[1] or "").startswith("RuntimeError"), True, "build_en_cours : RuntimeError")
    verifie((modifie(racine, ENV, r7, builds=lambda: None)[1] or "").startswith("RuntimeError"), True, "build_inconnu : RuntimeError")
    verifie(fichiers(racine, ENV), origine, "build_en_cours : rien d'ecrit")
    # metier_nouveau_squelettes, fichier_existant_non_ecrase
    (racine / d / "controleChauffage.be").write_text(TEMOIN, encoding="utf-8")
    r8 = replace(reps(racine, ENV), metiers=["piscine", "chauffage"], squelettes=True)
    res, msg = modifie(racine, ENV, r8)
    verifie((res is not None, msg), (True, None), "metier_nouveau : modifie")
    verifie("chauffage" in json.loads(lit(racine, d + "/_persist.json")).get("modules", {}), True, "metier_nouveau : module dans le persist")
    verifie((racine / d / "chauffageFonctions.be").is_file(), True, "metier_nouveau_squelettes : fichier cree")
    verifie((racine / d / "controleChauffage.be").read_text(encoding="utf-8"), TEMOIN, "fichier_existant_non_ecrase : intact")
    # metier deja pris dans data/fs : refus
    verifie(any("existe deja" in x for x in prepare(racine, ENV, replace(r8, metiers=["piscine", "leds"]))["refus"]), True,
            "metier_nouveau : nom pris dans data/fs -> refus")
    # reseau_change : carte autonome, SSID et mot de passe changent ensemble
    reseau_change(t)
    esclave_range_extender(t)
    doublon_refuse(t)
    masquage_unique(t)


def reseau_change(t):
    racine = depot(Path(t) / "r")
    env, d = "tasmota32s3-garage-autonome1", "data/garage/tasmota32s3-autonome1"
    r = Reponses(puce="ESP32S3", base="", lieu="garage", nom="autonome1", reseau1="MAISON", blocs=["udp"],
                 metiers=["autonome1"], squelettes=True)
    p = apc.prepare(racine, r)
    verifie(p["refus"], [], "reseau_change : creation de la carte autonome")
    apc.cree(racine, r, p["empreinte"], SANS_BUILD)
    avant, apres = parc.secrets(racine, "MAISON", "MAISON")["wifi1"], parc.secrets(racine, "iPhone de Frederic", "iPhone de Frederic")["wifi1"]
    verifie(avant != apres, True, "reseau_change : les deux reseaux ont des mots de passe differents (precondition)")
    r1 = replace(reps(racine, env), reseau1="iPhone de Frederic", reseau2="iPhone de Frederic")
    res, msg = modifie(racine, env, r1)
    verifie((res is not None, msg), (True, None), "reseau_change : modifie")
    w = json.loads(lit(racine, d + "/_persist.json"))["serveur"]["wifi"]
    verifie((w["reseau1"]["nomReseauWifi"], w["reseau1"]["mdpWifi"] == apres), ("iPhone de Frederic", True), "reseau_change : persist, SSID et mot de passe ensemble")
    h = "\n".join(section(racine, env, fbc.FICHIER_H))
    verifie((re.search(r'#define\s+STA_SSID1\s+"iPhone de Frederic"', h) is not None, re.search(r'#define\s+STA_PASS1\s+"' + re.escape(apres) + '"', h) is not None), (True, True), "reseau_change : .h, SSID et mot de passe ensemble")
    # ligne du mot de passe retouchee a la main : refus masque, ni le mot de passe ni le temoin ne sortent
    h_txt = lit(racine, fbc.FICHIER_H).decode("utf-8", errors="surrogateescape")
    deb = h_txt.index(f"#elif defined({fbx_define(racine, env)})")        # la section de l'env, pas celle d'une autre carte
    h_txt = h_txt[:deb] + re.sub(r'(#define\s+STA_PASS1\s+)"' + re.escape(apres) + '"', lambda m: m.group(1) + f'"{TEMOIN}"',
                                 h_txt[deb:], count=1)
    (racine / fbc.FICHIER_H).write_bytes(h_txt.encode("utf-8", errors="surrogateescape"))
    origine = fichiers(racine, env)
    p = prepare(racine, env, replace(r1, reseau1="MAISON", reseau2="MAISON"))
    verifie((len(p["refus"]) >= 1, any("STA_PASS1" in x for x in p["refus"])), (True, True), "reseau_change : ligne retouchee -> refus qui la cite")
    verifie(modifie(racine, env, replace(r1, reseau1="MAISON", reseau2="MAISON"))[0], None, "reseau_change : modification refusee")
    verifie(fichiers(racine, env), origine, "reseau_change : refus, rien d'ecrit")


def esclave_range_extender(t):
    """Ruling 8 : un esclave dont l'autoexec porte deja controleRangeExtender, page qui coche rangeExtender :
    refus propre ou aucun doublon, jamais deux fois la meme ligne."""
    racine = cree_piscine(t, "e", BLOCS)
    d = fbe.dossier_carte(ENV)
    avant = lit(racine, d + "/autoexec.be").decode("utf-8")
    verifie("controleRangeExtender" in avant, True, "rangeExtender esclave : l'autoexec cree porte deja controleRangeExtender")
    r = replace(reps(racine, ENV), blocs=list(BLOCS))
    p = prepare(racine, ENV, r)
    res, msg = modifie(racine, ENV, r)
    lignes = [l.strip() for l in lit(racine, d + "/autoexec.be").decode("utf-8").splitlines() if l.strip().startswith("demarrage.")]
    verifie(len(lignes) == len(set(lignes)), True, "rangeExtender esclave : aucune ligne en double dans l'autoexec")
    verifie((res is None, (msg or "").startswith("RuntimeError")), (True, True), "rangeExtender esclave : refuse (RuntimeError)")


def doublon_refuse(t):
    """I2 : une ligne presente UNE fois dans le vrai autoexec (ajoutee a la main) que l'ecart A -> B ajoute encore :
    refus qui la cite, rien d'ecrit. Prouve par temoin que _doublons est ce qui refuse."""
    racine = cree_piscine(t, "dbl", [b for b in SANS_RE if b != "historique"])
    d = fbe.dossier_carte(ENV)
    chemin = racine / d / "autoexec.be"
    texte_a = chemin.read_bytes().decode("utf-8")
    eol = fbc._eol(texte_a)
    lignes = texte_a.split(eol)
    lignes.insert(len(lignes) - 1 - lignes[::-1].index("end"), "    demarrage.historique()")
    chemin.write_bytes(eol.join(lignes).encode("utf-8"))
    origine = fichiers(racine, ENV)
    r = replace(reps(racine, ENV), blocs=list(SANS_RE))              # la page coche historique : A -> B l'ajoute
    p = prepare(racine, ENV, r)
    verifie(any("serait en double" in x and "demarrage.historique()" in x and d + "/autoexec.be" in x for x in p["refus"]), True,
            "doublon_refuse : prepare cite le fichier et la ligne")
    res, msg = modifie(racine, ENV, r)
    verifie((res, (msg or "").startswith("RuntimeError")), (None, True), "doublon_refuse : modifie -> RuntimeError")
    verifie(fichiers(racine, ENV), origine, "doublon_refuse : rien d'ecrit")


def masquage_unique(t):
    """I1 : un retour anticipe (section .h introuvable) et le repli sur ValueError masquent aussi les secrets."""
    # secrets emboites, le court en premier (pire ordre d'iteration) : aucun fragment du long en clair
    sortie = apmod._cache("x abcdef y abc z", ["abc", "abcdef", ""])
    verifie((("def" in sortie), sortie.count("***")), (False, 2), "masquage_unique : secrets emboites, le long masque d'abord")
    racine = cree_piscine(t, "msq", SANS_RE)
    r = replace(reps(racine, ENV), ip="192.168.0.77")
    secret = apmod.gen.secrets_reponses(racine, reps(racine, ENV))["mqtt"]
    verifie(bool(secret), True, "masquage_unique : secret de test present")
    orig = (apmod.delta.applique_lignes, apmod.fbc._section_h, apmod.gen.persist)
    try:
        apmod.delta.applique_lignes = lambda reel, a, b: (reel, [f"replace : lignes absentes :\n  ligne citee {secret} fin"])
        apmod.fbc._section_h = lambda lignes, define: None                      # retour anticipe apres le refus cite
        p = prepare(racine, ENV, r)
        res, msg = modifie(racine, ENV, r)
        verifie((len(p["refus"]) >= 2, secret in json.dumps(p), secret in (msg or ""), "***" in " ".join(p["refus"])),
                (True, False, False, True), "masquage_unique : retour anticipe, refus et exception masques")
        apmod.gen.persist = lambda *a, **k: (_ for _ in ()).throw(ValueError(f"boom {secret}"))     # repli _calcule
        p = prepare(racine, ENV, r)
        res, msg = modifie(racine, ENV, r)
        verifie((secret in json.dumps(p), secret in (msg or ""), "***" in " ".join(p["refus"])), (False, False, True),
                "masquage_unique : repli ValueError masque")
    finally:
        apmod.delta.applique_lignes, apmod.fbc._section_h, apmod.gen.persist = orig


def test_rejeu_parc(t):
    """Chaque carte du parc (copiee dans le depot d'essai) : chargee puis preparee sans changement -> ecart vide."""
    racine = depot(Path(t) / "parc")
    exclues, vues = {}, []
    for c in apmod.cartes(racine):
        try:
            r = Reponses(**apmod.charge_env(racine, c["env"])["reponses"])
        except ValueError as exc:
            exclues[c["env"]] = str(exc)
            continue
        p = prepare(racine, c["env"], r)
        vues.append(c["env"])
        if not verifie((p["vide"], p["refus"], p["chemins"]), (True, [], []), f"rejeu_parc_ecart_vide : {c['env']}"):
            print("     chemins fautifs :", ", ".join(p["chemins"]) or "(aucun)")
    for env in GARAGE:
        verifie((env in vues, env in exclues), (True, False), f"rejeu_parc_ecart_vide : {env} (garage) rejouee, jamais exclue")
    rejeu_vraie_modification(racine, vues)
    print(f"     rejouees : {len(vues)} ({', '.join(vues)})")
    for env, raison in exclues.items():
        print(f"     exclue : {env} : {raison}")


def feuilles(o, chemin=()):
    if isinstance(o, dict):
        return {k: v for c, x in o.items() for k, v in feuilles(x, chemin + (c,)).items()}
    if isinstance(o, list):
        return {k: v for i, x in enumerate(o) for k, v in feuilles(x, chemin + (str(i),)).items()}
    return {".".join(chemin): o}


def rejeu_vraie_modification(racine, envs):
    """I2 : ici A et B ne sont pas identiques par construction : on change l'IP, on prepare puis on ecrit (sur la copie).
    Chaque carte est soit appliquee (le persist ne change qu'aux chemins de l'ecart, et l'IP y passe de l'ancienne a la
    nouvelle), soit refusee par un refus qui cite un fichier. Les cartes du garage doivent etre appliquees."""
    for i, env in enumerate(envs):
        r = reps(racine, env)
        r2 = replace(r, ip=f"192.168.0.{200 + i}")
        p = prepare(racine, env, r2)
        if p["refus"]:
            fich = sorted({m for x in p["refus"] for m in re.findall(r"[\w./-]+\.(?:json|be|ini|h)\b", x)})
            print(f"     {env} : refuse ({', '.join(fich) or 'aucun fichier cite'})")
            verifie((bool(fich), env in GARAGE), (True, False), f"rejeu_parc_modifie : {env} refus cite un fichier, hors garage")
            continue
        fp = fbe.dossier_carte(env) + "/_persist.json"
        avant = feuilles(json.loads(lit(racine, fp)))
        res, msg = modifie(racine, env, r2)
        apres = feuilles(json.loads(lit(racine, fp)))
        diff = {k for k in avant.keys() | apres.keys() if avant.get(k) != apres.get(k)}
        ip_ok = all(r2.ip in str(apres.get(k)) and r.ip in str(avant.get(k)) for k in diff)
        ok = verifie((msg, p["vide"], diff == set(p["chemins"]), ip_ok), (None, False, True, True),
                     f"rejeu_parc_modifie : {env} appliquee, seule l'IP change dans le persist")
        print(f"     {env} : applique ({len(diff)} chemin(s) du persist)" if ok else f"     {env} : ECHEC")


def test_aucun_secret():
    sortie = "\n".join(SORTIES)
    trouves = [s for s in secrets_reels() + [TEMOIN] if s in sortie]
    mdp = {parc.secrets(RACINE, n, n)["wifi1"] for n in ("MAISON", "iPhone de Frederic")}
    verifie((trouves, [s for s in mdp if s in sortie]), ([], []), f"aucun_secret : {len(SORTIES)} sorties (diff, refus, erreurs, resultats)")


def principal():
    with tempfile.TemporaryDirectory() as t:
        test_charge(t)
        test_modification(t)
        test_rejeu_parc(t)
        test_aucun_secret()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
