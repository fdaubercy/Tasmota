"""Creation d'un env a partir d'une carte modele (page « Fichiers Berry par env », spec §2.6).

Une carte tient en TROIS morceaux, tous indispensables : sans dossier data/, elle demarre sans
autoexec ni persist (lecon du 2026-09-27) ; sans section du .h, son -D FIRMWARE_... ne sert a rien.
  1. la section [env:<puce>-<lieu>-<nom>] du cenv, recopiee de celle du modele ;
  2. le dossier data/<lieu>/<puce>-<nom> (regle de transform_name), copie du dossier du modele, dont le
     _persist.json ne change QUE ses valeurs d'identite (remplacement dans le texte, pas de json.dumps :
     encodage, fins de ligne et ordre des cles gardes octet pour octet) ;
  3. la section `#elif defined(FIRMWARE_...)` de user_config_override.h, copiee juste apres celle du
     modele, avec les defines d'identite remplaces.
Selon la PUCE de la base, l'alerte du coprocesseur Wi-Fi des P4 (controleCoprocesseur.be) est posee ou neutralisee
dans la section, le persist et l'autoexec copies, quel que soit le modele : fichiers_berry_coprocesseur.py.
Deux cartes de meme identite (IP, topic, client MQTT) se deconnectent mutuellement : refus si deja pris.
Rien n'est commite ; les mots de passe sont masques dans le diff.
"""

import difflib
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import fichiers_berry_coprocesseur as fbcp
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi
import fichiers_berry_sauvegarde as fbs

FICHIER_H = "tasmota/user_config_override.h"
CHAMPS_IDENTITE = ("CODE_IMAGE_STR", "PROJECT", "WIFI_IP_ADDRESS", "WIFI_RGX_SSID", "MQTT_CLIENT_ID",
                   "MQTT_TOPIC", "MQTT_GRPTOPIC", "FRIENDLY_NAME")
CLES_PERSIST = {"serveur.nom": "FRIENDLY_NAME", "serveur.hostname": "PROJECT", "serveur.IP.IPAddress": "WIFI_IP_ADDRESS",
                "serveur.mqtt.client": "MQTT_CLIENT_ID", "serveur.mqtt.topic": "MQTT_TOPIC",
                "serveur.mqtt.groupTopic1": "MQTT_GRPTOPIC", "serveur.rangeExtender.AP.SSID": "WIFI_RGX_SSID",
                "template.NAME": "CODE_IMAGE_STR"}
UNIQUES = {"MQTT_TOPIC": "serveur.mqtt.topic", "MQTT_CLIENT_ID": "serveur.mqtt.client",
           "WIFI_IP_ADDRESS": "serveur.IP.IPAddress"}          # deux cartes ne peuvent pas les partager
LIEU, NOM = re.compile(r"[a-z0-9]+"), re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
DEFINE = re.compile(r"FIRMWARE_[A-Z0-9_]+")
SANS_ESPACE = ("PROJECT", "MQTT_CLIENT_ID", "MQTT_TOPIC", "MQTT_GRPTOPIC", "WIFI_IP_ADDRESS")   # Hostname, MQTT, IP
JOKERS_MQTT = ("MQTT_CLIENT_ID", "MQTT_TOPIC", "MQTT_GRPTOPIC")                             # + et # : jokers MQTT
SECTION_H = re.compile(r" {8}(// -- Options for|#elif\b|#else\b|#endif\b)")   # niveau de la chaine des firmwares
MASQUES = ((re.compile(r'(#define\s+\w*(?:PASS|PWD)\w*\s+)"[^"]*"'), r'\1"***"'),
           (re.compile(r'("\w*(?:[Mm]dp|[Pp]ass|[Pp]wd)\w*"\s*:\s*)"[^"]*"'), r'\1"***"'))
TIRETS = ";" + "-" * 148


@dataclass
class Creation:
    modele: str                     # env de la carte modele
    base: str                       # env de base de la nouvelle carte
    lieu: str
    nom: str
    identite: dict = field(default_factory=dict)    # CHAMPS_IDENTITE -> valeur
    define: str = ""                # vide -> define(base, lieu, nom)


def nom_env(base, lieu, nom):
    return f"{base.split('-')[0]}-{lieu}-{nom}"


def define(base, lieu, nom):
    puce = base.split("-")[0]                       # tasmota32s3 -> ESP32S3
    return f"FIRMWARE_ESP{puce[len('tasmota'):].upper()}_{lieu.upper()}_{nom.upper().replace('-', '_')}"


def identite_par_defaut(lieu, nom):
    """Valeurs proposees, sur le modele du rideau (PROJECT RIDEAU-GARAGE, topic garage/rideau)."""
    projet = f"{nom.upper()}-{lieu.upper()}"
    lisible = nom.replace("-", " ").capitalize()
    return {"CODE_IMAGE_STR": lisible, "PROJECT": projet, "WIFI_IP_ADDRESS": "0.0.0.0",
            "WIFI_RGX_SSID": projet + "-GATEWAY", "MQTT_CLIENT_ID": projet, "MQTT_TOPIC": f"{lieu}/{nom}",
            "MQTT_GRPTOPIC": f"tasmotas/{lieu}", "FRIENDLY_NAME": lisible}


def spans_json(texte):
    """{(cle, sous-cle...): (debut, fin)} du CONTENU (sans guillemets) de chaque valeur chaine du JSON."""
    res, n = {}, len(texte)

    def blanc(i):
        while i < n and texte[i] in " \t\r\n﻿":
            i += 1
        return i

    def chaine(i):
        j = i + 1
        while texte[j] != '"':
            j += 2 if texte[j] == "\\" else 1
        return j + 1

    def valeur(i, chemin):
        i = blanc(i)
        if texte[i] == '"':
            fin = chaine(i)
            res[chemin] = (i + 1, fin - 1)
            return fin
        if texte[i] in "{[":
            objet, k = texte[i] == "{", 0
            i = blanc(i + 1)
            while texte[i] not in "}]":
                if objet:
                    fin = chaine(i)
                    cle = json.loads(texte[i:fin])
                    i = blanc(fin) + 1                     # le ':'
                else:
                    cle, k = k, k + 1
                i = blanc(valeur(i, chemin + (cle,)))
                if texte[i] == ",":
                    i = blanc(i + 1)
            return i + 1
        while i < n and texte[i] not in ",}] \t\r\n":
            i += 1
        return i

    valeur(0, ())
    return res


def _octets(chemin):
    return chemin.read_bytes() if chemin.is_file() else b""


def _texte(octets):
    return octets.decode("utf-8", errors="surrogateescape")


def _encode(lignes, eol):
    return eol.join(lignes).encode("utf-8", errors="surrogateescape")


def _eol(texte):
    return "\r\n" if "\r\n" in texte else "\n"


def _fin_utile(lignes, debut, fin):
    """Fin de la section sans les lignes vides et commentaires qui annoncent la section suivante."""
    while fin - 1 > debut and (not lignes[fin - 1].strip() or lignes[fin - 1].lstrip()[:1] in ";#"):
        fin -= 1
    return fin


def _copie_cenv(ini, lignes, c, env, dossier, dossier_modele, ancien, nouveau):
    regions = _regions(lignes)
    debut, fin = regions["env:" + c.modele]
    copie = lignes[debut:_fin_utile(lignes, debut, fin)]
    ancetres = {s[len("env:"):] for s in ini.chaine(c.modele)[1:]}
    ref = "${env:" + c.base + ".custom_files_upload}"
    res, i, upload = [f"[env:{env}]"], 1, False
    while i < len(copie):
        l = copie[i]
        i += 1
        if re.match(r"(upload_port|monitor_port)\s*=", l):
            continue                                       # port COM d'une autre carte
        if re.match(r"extends\s*=", l):
            res.append(l[:l.index("=") + 1] + " env:" + c.base)
            continue
        if re.match(r"custom_files_upload\s*=", l):
            col = len(re.match(r"[^=]*=\s*", l).group(0))
            res += [l[:col] + ref, " " * col + dossier]
            j = i                                          # ancienne liste : base + dossier du modele
            while j < len(copie):
                s = copie[j].strip()
                if s and s[0] not in ";#" and copie[j][:1].isspace():
                    j, i = j + 1, j + 1                    # ligne de la liste : remplacee
                elif not s or s[0] in ";#":
                    j += 1                                 # vide ou commentaire : la liste continue apres (ConfigParser)
                else:
                    break
            upload = True
            continue
        l = re.sub(r"\$\{env:([^.}]+)\.", lambda m: "${env:" + (c.base if m.group(1) in ancetres else m.group(1)) + ".", l)
        res.append(re.sub(r"\b" + ancien + r"\b", nouveau, l.replace(dossier_modele, dossier)))
    if not upload:
        res += [f"{'custom_files_upload':<24}= {ref}", " " * 26 + dossier]
    return res


def _regions(lignes):
    entetes = [(i, m.group(1).strip()) for i, l in enumerate(lignes) if l[:1] == "[" and (m := fbi.ENTETE.match(l))]
    return {nom: (i, entetes[k + 1][0] if k + 1 < len(entetes) else len(lignes)) for k, (i, nom) in enumerate(entetes)}


def _insere_cenv(ini, lignes, lieu, copie, sauf=None):
    """Apres le dernier env du lieu (hors `sauf`, l'env qu'un renommage retire), sinon sous un nouveau bandeau."""
    memes = [e for e in ini.envs_cenv() if e.split("-")[1:2] == [lieu] and e != sauf]
    if memes:
        debut, fin = _regions(lignes)["env:" + memes[-1]]
        k = _fin_utile(lignes, debut, fin)
        return lignes[:k] + [""] + copie + lignes[k:]
    k = len(lignes) - 1 if lignes and lignes[-1] == "" else len(lignes)   # garder la fin de ligne finale
    tirets = next((l for l in lignes if re.fullmatch(r";-{20,}", l)), TIRETS)
    return lignes[:k] + ["", tirets, f"; LOCALISATION: {lieu.upper()}", tirets] + copie + lignes[k:]


def _section_h(lignes, ancien):
    ouv = next((i for i, l in enumerate(lignes) if re.match(r" {8}#(?:el)?if\b", l)
                and re.search(r"defined\(\s*" + ancien + r"\s*\)", l)), None)
    if ouv is None:
        return None
    debut = ouv
    while debut and lignes[debut - 1].startswith("        //") and not lignes[debut].startswith("        // -- Options for"):
        debut -= 1                       # commentaires contigus, jusqu'a l'en-tete « // -- Options for » compris
    if not lignes[debut].startswith("        // -- Options for"):
        debut = ouv                      # pas d'en-tete : les commentaires au-dessus ne sont pas a elle
    fin = next((i for i in range(ouv + 1, len(lignes)) if SECTION_H.match(lignes[i])), len(lignes))
    return debut, ouv, fin


def _copie_h(lignes, bornes, env, nouveau, identite, avertissements):
    debut, ouv, fin = bornes
    anciens = re.findall(r"FIRMWARE_\w+", lignes[ouv])
    corps = lignes[ouv + 1:fin]
    for l in corps:
        cites = [a for a in anciens if re.search(r"\b" + a + r"\b", l)]
        if cites:
            avertissements.append(f"{FICHIER_H} : condition interne a revoir a la main : {l.strip()}")
    texte = "\n".join(corps)
    for champ in CHAMPS_IDENTITE:
        motif = re.compile(r'^(\s*#define\s+' + champ + r'\s+)"[^"]*"', re.M)
        if not motif.search(texte):
            avertissements.append(f"{FICHIER_H} : {champ} absent de la section du modele, non pose")
        texte = motif.sub(lambda m: m.group(1) + '"' + identite[champ] + '"', texte)
    # "Backlog Hostname X" ou "Backlog Module 0; Hostname X" (cave, differentiel, grenier)
    texte = re.sub(r"^(\s*#define\s+USER_BACKLOG\b.*?\bHostname\s+)[^\s\";]+",
                   lambda m: m.group(1) + identite["PROJECT"], texte, flags=re.M)
    texte = re.sub(r'(\\"NAME\\":\\")(.*?)(\\")', lambda m: m.group(1) + identite["CODE_IMAGE_STR"] + m.group(3), texte)
    return [f"        // -- Options for {env} ------", f"        #elif defined({nouveau})"] + texte.split("\n")


def _persist(texte, identite, avertissements):
    spans = spans_json(texte)
    remplacements = []
    for cle, champ in CLES_PERSIST.items():
        s = spans.get(tuple(cle.split(".")))
        if s is None:
            avertissements.append(f"_persist.json : cle {cle} absente du modele, non posee")
        else:
            remplacements.append((s, json.dumps(identite[champ], ensure_ascii=False)[1:-1]))
    for (debut, fin), valeur in sorted(remplacements, reverse=True):
        texte = texte[:debut] + valeur + texte[fin:]
    return texte


def _prises(racine, texte_h, sauf_dossier=None):
    """{champ: {valeur: ou}} des identites deja utilisees (.h et persists du depot, hors sauvegardes et hors
    `sauf_dossier`, la carte qu'un renommage reprend)."""
    prises = {c: {} for c in UNIQUES}
    for champ in UNIQUES:
        for v in re.findall(r'#define\s+' + champ + r'\s+"([^"]*)"', texte_h):
            prises[champ].setdefault(v, FICHIER_H)
    for p in sorted(Path(racine, "data").glob("*/*/_persist.json")):
        if "sauvegarde" in p.parent.name or (sauf_dossier and p.parent == Path(racine) / sauf_dossier):
            continue
        try:
            donnees = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        except ValueError:
            continue
        for champ, cle in UNIQUES.items():
            v = donnees
            for k in cle.split("."):
                v = v.get(k) if isinstance(v, dict) else None
            if isinstance(v, str):
                prises[champ].setdefault(v, p.relative_to(racine).as_posix())
    return prises


def _sans_commentaires(texte, marque):
    """Texte sans les commentaires de ligne (`;` du cenv, `//` du .h) : un define seulement cite n'existe pas."""
    return "\n".join(re.sub(r"(^|\s)" + re.escape(marque) + r".*$", "", l) for l in texte.split("\n"))


def _refus(racine, ini, c, env, dossier, nouveau, texte_h, texte_cenv, sauf_dossier=None, avertissements=None):
    """Refus de la creation (ou du renommage). Une identite deja portee par une autre carte n'est qu'un
    AVERTISSEMENT (carte remplacee : meme IP, topic, client ; decide le 2026-10-25), ajoute a `avertissements`."""
    refus = []
    envs = {e["nom"]: e["famille"] for e in fbe.envs_proposes(racine)}
    if envs.get(c.modele) != "cartes":
        refus.append(f"modele inconnu ou pas une carte : {c.modele!r}")
    if envs.get(c.base) != "bases":
        refus.append(f"base inconnue : {c.base!r}")
    if not LIEU.fullmatch(c.lieu) or not NOM.fullmatch(c.nom):
        refus.append("lieu : minuscules et chiffres ; nom : minuscules, chiffres et tirets (ex. porte-garage)")
        return refus
    if fbe.est_base(env):
        refus.append(f"{env} : un nom d'env contenant « -base » est pris pour une base (page build, dossier de carte) ; "
                     "choisir un lieu et un nom sans « base » en tete")
        return refus
    if "env:" + env in ini.sections:
        refus.append(f"l'env {env} existe deja")
    if (Path(racine) / dossier).exists():
        refus.append(f"le dossier {dossier} existe deja")
    if not DEFINE.fullmatch(nouveau):
        refus.append(f"define invalide : {nouveau!r}")
    elif re.search(r"\b" + nouveau + r"\b", _sans_commentaires(texte_h, "//") + "\n" + _sans_commentaires(texte_cenv, ";")):
        refus.append(f"le define {nouveau} existe deja")
    for champ in CHAMPS_IDENTITE:
        v = c.identite.get(champ, "")
        interdits = '"\\\r\n;' + (" \t" if champ in SANS_ESPACE else "") + ("+#" if champ in JOKERS_MQTT else "")
        if not v or any(x in v for x in interdits):
            refus.append(f"{champ} : valeur vide ou avec un caractere interdit ({interdits!r}) : {v!r}")
    for champ, valeurs in _prises(racine, texte_h, sauf_dossier).items():
        v = c.identite.get(champ)
        if v in valeurs and v != "0.0.0.0" and avertissements is not None:
            avertissements.append(f"{champ} = {v} est deja porte par une autre carte ({valeurs[v]}) : normal pour une "
                                  "carte qui en remplace une autre ; sinon les deux cartes se deconnecteront")
    return refus


def _masque(diff):
    for motif, remplace in MASQUES:
        diff = motif.sub(remplace, diff)
    return diff


def _empreinte(o_cenv, o_h, c):
    """Fichiers lus ET saisie : une saisie changee apres le diff n'est pas ecrite sans nouveau diff."""
    demande = json.dumps(asdict(c), sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(o_cenv + b"\0" + o_h + b"\0" + demande).hexdigest()


def _calcule(racine, c):
    racine = Path(racine)
    env, nouveau = nom_env(c.base, c.lieu, c.nom), c.define or define(c.base, c.lieu, c.nom)
    dossier = fbe.dossier_carte(env)
    o_cenv, o_h = _octets(racine / fbi.FICHIER_CENV), _octets(racine / FICHIER_H)
    t_cenv, t_h = _texte(o_cenv), _texte(o_h)
    l_cenv, l_h = fbi.decoupe(t_cenv), fbi.decoupe(t_h)
    ini = fbi.lit_sections(racine)
    res = {"env": env, "dossier": dossier, "define": nouveau, "avertissements": [],
           "empreinte": _empreinte(o_cenv, o_h, c), "diff": "", "eol": (_eol(t_cenv), _eol(t_h))}
    res["refus"] = refus = _refus(racine, ini, c, env, dossier, nouveau, t_h, t_cenv, avertissements=res["avertissements"])
    if refus:
        return res
    flags = " ".join(v for _, v, _ in ini.sections["env:" + c.modele].get("build_flags", fbi.Option("", "", "", 0)).morceaux)
    anciens = re.findall(r"-D\s*(FIRMWARE_\w+)", flags)
    dossier_modele = fbe.dossier_carte(c.modele)
    bornes = _section_h(l_h, anciens[-1]) if anciens else None
    if not anciens or bornes is None or not (racine / dossier_modele).is_dir():
        refus.append(f"modele incomplet : -D FIRMWARE_ du cenv, section du .h ou dossier {dossier_modele} manquant")
        return res
    # Alerte du coprocesseur Wi-Fi : cenv, persist et autoexec ajustes a la PUCE de la base (2026-10-26)
    p4 = fbcp.est_p4(c.base)
    copie = _copie_cenv(ini, l_cenv, c, env, dossier, dossier_modele, anciens[-1], nouveau)
    copie = fbcp.adapte_cenv(copie, p4, res["avertissements"])
    res["cenv"] = _insere_cenv(ini, l_cenv, c.lieu, copie)
    bloc = _copie_h(l_h, bornes, env, nouveau, c.identite, res["avertissements"])
    res["h"] = l_h[:bornes[2]] + bloc + l_h[bornes[2]:]
    p_modele = racine / dossier_modele / "_persist.json"
    t_modele = _texte(_octets(p_modele)) if p_modele.is_file() else None
    res["persist"] = _persist(t_modele, c.identite, res["avertissements"]) if t_modele is not None else None
    if res["persist"] is not None:
        res["persist"] = fbcp.adapte_persist(res["persist"], p4, res["avertissements"])
    if t_modele is None:
        res["avertissements"].append(f"{dossier_modele} n'a pas de _persist.json")
    a_modele = racine / dossier_modele / "autoexec.be"
    t_auto = _texte(_octets(a_modele)) if a_modele.is_file() else None
    res["autoexec"] = fbcp.adapte_autoexec(t_auto, p4, res["avertissements"]) if t_auto is not None else None
    if res["autoexec"] == t_auto:
        res["autoexec"] = None                                      # inchange : la copie du dossier suffit
    diffs = [difflib.unified_diff(l_cenv, res["cenv"], fbi.FICHIER_CENV, fbi.FICHIER_CENV, lineterm="", n=1),
             difflib.unified_diff(l_h, res["h"], FICHIER_H, FICHIER_H, lineterm="", n=1)]
    if t_modele is not None:
        diffs.append(difflib.unified_diff(fbi.decoupe(t_modele), fbi.decoupe(res["persist"]),
                                          f"{dossier_modele}/_persist.json", f"{dossier}/_persist.json",
                                          lineterm="", n=1))
    if res["autoexec"] is not None:
        diffs.append(difflib.unified_diff(fbi.decoupe(t_auto), fbi.decoupe(res["autoexec"]),
                                          f"{dossier_modele}/autoexec.be", f"{dossier}/autoexec.be", lineterm="", n=1))
    res["diff"] = _masque("\n".join("\n".join(d) for d in diffs))
    return res


def prepare_creation(racine, c):
    """{env, dossier, define, diff (secrets masques), empreinte, avertissements, refus}, sans rien ecrire."""
    r = _calcule(racine, c)
    return {k: r[k] for k in ("env", "dossier", "define", "diff", "empreinte", "avertissements", "refus")}


def _ignore_modele(racine, dossier_modele):
    """Pour copier le dossier du modele : ni *sauvegarde*, ni les copies temporaires d'un build interrompu
    (fichiers identiques a data/fs, sous-dossiers fs/json/sd recopies par copy_fs_image)."""
    haut = Path(racine) / dossier_modele
    copies = {Path(c).name for c in fbe.copies_temporaires(racine, dossier_modele)}

    def ignore(dossier, noms):
        res = [n for n in noms if "sauvegarde" in n]
        if Path(dossier) == haut:
            res += [n for n in noms if n in copies or (n in ("fs", "json", "sd") and (haut / n).is_dir())]
        return res
    return ignore


def cree(racine, c, empreinte_lue, builds_en_cours):
    """Cree les trois morceaux, atomiquement (copie horodatee du cenv et du .h avant ecriture). RuntimeError (-> 409) : build en cours ou
    indetectable, fichiers modifies depuis le diff, refus."""
    builds = builds_en_cours()
    if builds is None:
        raise RuntimeError("impossible de savoir si un build tourne : creation refusee")
    if builds:
        raise RuntimeError("un build est en cours (" + ", ".join(builds) + ") : creation refusee")
    racine = Path(racine)
    r = _calcule(racine, c)
    if r["empreinte"] != empreinte_lue:
        raise RuntimeError("le cenv, le .h ou la saisie ont change depuis le diff : refaire « Voir le diff »")
    if r["refus"]:
        raise RuntimeError(" ; ".join(r["refus"]))
    # atomique : une ecriture qui echoue defait les precedentes (dossier copie retire, .h remis)
    with fbs.Transaction(racine, "creation") as tr:
        tr.copie_dossier(fbe.dossier_carte(c.modele), r["dossier"], ignore=_ignore_modele(racine, fbe.dossier_carte(c.modele)))
        if r["persist"] is not None:
            tr.ecrit(r["dossier"] + "/_persist.json", r["persist"].encode("utf-8", errors="surrogateescape"))
        if r["autoexec"] is not None:
            tr.ecrit(r["dossier"] + "/autoexec.be", r["autoexec"].encode("utf-8", errors="surrogateescape"))
        for fichier, cle, eol in ((FICHIER_H, "h", r["eol"][1]), (fbi.FICHIER_CENV, "cenv", r["eol"][0])):
            tr.ecrit(fichier, _encode(r[cle], eol))
    return {"cree": True, "env": r["env"], "dossier": r["dossier"], "diff": r["diff"],
            "avertissements": r["avertissements"], "sauvegarde": str(tr.dossier)}
