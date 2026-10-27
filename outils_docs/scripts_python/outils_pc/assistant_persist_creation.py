"""Creation atomique d'un env genere par l'assistant de persist (spec 2026-10-27 §5.2 et §7, page 7900).

Trois morceaux, comme la page 7800 (fichiers_berry_creation), mais tires du MODELE et des reponses au lieu d'une
carte modele :
  1. la section [env:...] du cenv (gabarit `cenv`, listes `solidify` / `exclude` des blocs coches) ;
  2. le dossier data/<lieu>/<puce>-<nom> : _persist.json, autoexec.be, graphiques.json, et les squelettes du metier ;
  3. la section `#elif defined(FIRMWARE_...)` du .h : gabarit `puces[puce].h` + lignes `h` des blocs coches
     (dedoublonnees : `#define USE_WS2812` du ruban et de la LED RGB), mots de passe remplis par
     assistant_persist_parc.secrets, inseree juste avant le #else/#endif qui ferme la chaine des firmwares.

  prepare(racine, r)  -> {env, dossier, define, diff, empreinte, avertissements, refus, apercu: {persist, autoexec}}
                         Rien n'est ecrit. Les mots de passe ne sortent JAMAIS : le diff, l'apercu, les refus sont
                         construits avec "***" (les vraies valeurs ne servent qu'a l'ecriture dans cree()).
  cree(racine, r, empreinte_lue, builds_en_cours) -> {cree, env, dossier, diff, avertissements, sauvegarde, resume,
                         liens}. RuntimeError (-> 409) : build en cours ou indetectable, saisie ou fichiers changes
                         depuis le diff (empreinte), refus. Une seule Transaction : une ecriture qui echoue defait
                         les precedentes (dossier, .h, cenv remis).
L'empreinte couvre le cenv, le .h, le modele et la saisie : une saisie changee apres « Voir le diff » n'est pas
ecrite sans nouveau diff. Le modele est lu dans la RACINE cible (le depot d'essai des bancs en recoit une copie).
"""

import difflib
import hashlib
import json
import re
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

import assistant_persist_elements as ape
import assistant_persist_generation as gen
import assistant_persist_modele as apm
import assistant_persist_parc as parc
import fichiers_berry_coprocesseur as fbcp
import fichiers_berry_creation as fbc
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi
import fichiers_berry_sauvegarde as fbs

LIEN_BUILD = "http://127.0.0.1:7700/?env="
LIEN_FICHIERS = "http://127.0.0.1:7800/?env="
GABARIT_H = re.compile(r"\{\{(@?\w+)\}\}")
DEFINE = re.compile(r"\s*#define\s+(\w+)")
ELIF_FIRMWARE = re.compile(r" {8}#elif\s+defined\(\s*FIRMWARE_")
INTERDITS_H = '"\\\r\n'                       # casseraient une chaine du .h (SSID, nom de template)


def _schema(racine):
    chemin = Path(racine) / "outils_docs" / "schemas" / "persist.schema.json"
    if not chemin.is_file():
        chemin = gen.RACINE / "outils_docs" / "schemas" / "persist.schema.json"     # depot d'essai : le vrai schema
    return json.loads(chemin.read_text(encoding="utf-8"))


def _erreurs_schema(racine, obj):
    """Chemins fautifs du persist genere contre persist.schema.json (jamais une valeur : un mot de passe pourrait y etre)."""
    sys.path.insert(0, str(gen.RACINE / "outils_docs" / "scripts_python" / "berry"))
    try:
        import genere_schema_persist as gsp
    finally:
        sys.path.pop(0)
    return list(dict.fromkeys(e.split(" : ")[0] for e in gsp.valide(obj, _schema(racine))))


def _octets(chemin):
    return chemin.read_bytes() if chemin.is_file() else b""


def _refus_metiers(racine, r):
    refus = []
    if not r.metiers:                  # prouve par banc_demarrage : sans modules.<x>, controleGeneral leve key_error 'switchs'
        refus.append("au moins un metier est requis : sans bloc modules.<metier>, controleGeneral echoue au demarrage "
                     "(configDevices.be ne cree ses compteurs que pour un module)")
    if len(set(r.metiers)) != len(r.metiers):
        refus.append("metiers : un nom est donne deux fois")
    for m in dict.fromkeys(r.metiers):
        if not isinstance(m, str) or not re.fullmatch(r"[a-z][a-zA-Z0-9]*", m):
            refus.append(f"metier {m!r} : nom invalide (camelCase, [a-z][a-zA-Z0-9]*)")
            continue
        cap = m[:1].upper() + m[1:]
        for f in (f"controle{cap}.be", f"{m}Fonctions.be"):
            if (Path(racine) / "data" / "fs" / f).exists():
                refus.append(f"metier {m} : data/fs/{f} existe deja")
    if r.metiers and not r.squelettes:
        refus.append("metier donne sans squelettes : l'autoexec chargerait des fichiers qui n'existeraient pas")
    return refus


def _identite_h(v):
    """Les 8 champs d'identite (fichiers_berry_creation.CHAMPS_IDENTITE) tels que le gabarit du .h les pose."""
    return {"CODE_IMAGE_STR": v["nom_lisible"], "PROJECT": v["hostname"], "WIFI_IP_ADDRESS": v["ip"],
            "WIFI_RGX_SSID": v["ssid_ap"], "MQTT_CLIENT_ID": v["client"], "MQTT_TOPIC": v["topic"],
            "MQTT_GRPTOPIC": v["groupe"], "FRIENDLY_NAME": v["nom_lisible"]}


def _remplit(ligne, v, secrets):
    """{{variable}} et {{@secret}} d'une ligne de gabarit ; secrets=None -> '***'."""
    def sub(m):
        nom = m.group(1)
        if nom.startswith("@"):
            return "***" if secrets is None else secrets[nom[1:]]
        if nom not in v:
            raise ValueError(f"gabarit inconnu dans le modele : {m.group(0)}")
        return str(v[nom])
    return GABARIT_H.sub(sub, ligne)


def _section_h(modele, r, v, secrets):
    """Lignes de la section #elif : gabarit de la puce, puis les lignes `h` des blocs coches (un #define deja pose
    par un bloc precedent n'est pas repete)."""
    lignes = [_remplit(x, v, secrets) for x in modele["puces"][r.puce]["h"]]
    vus = {l.strip() for l in lignes if l.strip().startswith("#define")}
    for b in modele["blocs"]:
        if b["id"] not in gen.blocs_coches(modele, r) or r.puce not in b["puces"] or not b["h"]:
            continue
        lignes.append(f"            // -- Bloc {b['id']} (assistant de persist) --")
        for x in b["h"]:
            if x.strip().startswith("#define"):
                if x.strip() in vus:
                    continue
                vus.add(x.strip())
            lignes.append(_remplit(x, v, secrets))
    deja = {m.group(1) for l in lignes if (m := DEFINE.match(l))}
    neuves = [x for x in ape.lignes_h(modele, r) if (m := DEFINE.match(x)) is None or m.group(1) not in deja]
    if neuves:                                               # ex. USE_DS18x20 des thermometres, sauf si la puce le pose deja
        lignes += ["            // -- Entrees/sorties du bloc metier (assistant de persist) --"] + [_remplit(x, v, secrets) for x in neuves]
    return lignes


def _insere_h(l_h, section):
    """Section inseree avant le #else/#endif de niveau 8 qui ferme la chaine des firmwares."""
    dernier = max((i for i, l in enumerate(l_h) if ELIF_FIRMWARE.match(l)), default=None)
    if dernier is None:
        raise ValueError(f"{fbc.FICHIER_H} : chaine des firmwares introuvable (aucun #elif defined(FIRMWARE_...))")
    fin = next((i for i in range(dernier + 1, len(l_h)) if fbc.SECTION_H.match(l_h[i])), None)
    if fin is None or not re.match(r" {8}#(else|endif)\b", l_h[fin]):
        raise ValueError(f"{fbc.FICHIER_H} : fin de la chaine des firmwares introuvable")
    avant = [""] if l_h[fin - 1].strip() else []
    return l_h[:fin] + avant + section + l_h[fin:]


def _section_cenv(modele, v, listes):
    """Gabarit `cenv` rempli ; {{solidify}} et {{exclude}} : une valeur par ligne, alignees sous la premiere."""
    res = []
    for ligne in modele["cenv"]:
        for cle in ("solidify", "exclude"):
            marque = "{{" + cle + "}}"
            if marque in ligne:
                col, valeurs = ligne.index(marque), listes[cle]
                res.append(ligne.replace(marque, valeurs[0] if valeurs else "").rstrip())
                res += [" " * col + x for x in valeurs[1:]]
                break
        else:
            res.append(_remplit(ligne, v, None))
    return res


def _eol_texte(texte, eol):
    return texte.replace("\r\n", "\n").replace("\n", eol)


def _diff(nom, avant, apres):
    return "\n".join(difflib.unified_diff(avant, apres, nom, nom, lineterm="", n=1))


def _calcule(racine, r):
    racine = Path(racine)
    res = {"env": "", "dossier": "", "define": "", "diff": "", "avertissements": [], "refus": [],
           "apercu": {"persist": "", "autoexec": ""}}
    refus = res["refus"] = _refus_metiers(racine, r)
    if refus:
        return res                                           # nom metier valide AVANT persist et autoexec
    try:
        modele = apm.charge_modele(racine)
        v = gen.variables(racine, r)
        secrets = gen.secrets_reponses(racine, r)
    except (ValueError, KeyError) as exc:
        refus.append(str(exc.args[0]) if isinstance(exc, KeyError) else str(exc))
        return res
    o_cenv, o_h = _octets(racine / fbi.FICHIER_CENV), _octets(racine / fbc.FICHIER_H)
    o_modele = _octets(racine / apm.FICHIER_MODELE)
    res["empreinte"] = hashlib.sha256(b"\0".join(
        [o_cenv, o_h, o_modele, json.dumps(asdict(r), sort_keys=True, ensure_ascii=False).encode("utf-8")])).hexdigest()
    env, dossier, nouveau = v["env"], fbe.dossier_carte(v["env"]), v["define"]
    res.update(env=env, dossier=dossier, define=nouveau)
    t_cenv, t_h = fbc._texte(o_cenv), fbc._texte(o_h)
    eol_cenv, eol_h = fbc._eol(t_cenv), fbc._eol(t_h)
    l_cenv, l_h, ini = fbi.decoupe(t_cenv), fbi.decoupe(t_h), fbi.lit_sections(racine)
    refus += fbc.refus_nom(racine, ini, v["base"], r.lieu, r.nom, env, dossier, nouveau, t_h, t_cenv)
    identite = _identite_h(v)
    refus += fbc.refus_identite(identite)
    for champ in ("reseau1", "reseau2", "nom_template"):
        if any(x in v[champ] for x in INTERDITS_H):
            refus.append(f"{champ} : caractere interdit dans une chaine du .h")
    fbc.avertit_prises(racine, t_h, identite, res["avertissements"])
    if r.role == "esclave" and r.id in parc.ids_pris(racine):
        res["avertissements"].append(f"id {r.id} deja pris par {', '.join(parc.ids_pris(racine)[r.id])} : deux "
                                     "esclaves de meme id se repondent l'un a l'autre")
    if refus:
        return res
    obj = gen.persist(modele, r, v, secrets)
    masque = gen.persist(modele, r, v, None)
    texte_auto = gen.autoexec(modele, r)
    listes = gen.listes_cenv(modele, r)
    refus += gen.coherence(modele, r, obj, texte_auto, listes, racine)
    erreurs = _erreurs_schema(racine, obj)
    if erreurs:
        refus.append("persist genere refuse par le schema : " + ", ".join(erreurs[:12]))
    if refus:
        return res
    p4 = fbcp.est_p4(v["base"])
    copie = fbcp.adapte_cenv(_section_cenv(modele, v, listes), p4, res["avertissements"])
    cenv = fbc._insere_cenv(ini, l_cenv, r.lieu, copie)
    h = _insere_h(l_h, _section_h(modele, r, v, secrets))
    h_montre = _insere_h(l_h, _section_h(modele, r, v, None))
    fichiers = {"_persist.json": gen.texte_persist(obj, eol_cenv),
                "autoexec.be": _eol_texte(texte_auto, eol_cenv), "graphiques.json": gen.graphiques_initial()}
    montre = {"_persist.json": gen.texte_persist(masque, eol_cenv), "autoexec.be": fichiers["autoexec.be"],
              "graphiques.json": fichiers["graphiques.json"]}
    if r.squelettes:
        for m in dict.fromkeys(r.metiers):
            for nom, texte in gen.squelettes(modele, m).items():
                fichiers[nom] = montre[nom] = _eol_texte(texte, eol_cenv)
    res.update(cenv=cenv, h=h, fichiers=fichiers, eol=(eol_cenv, eol_h))
    res["apercu"] = {"persist": montre["_persist.json"], "autoexec": montre["autoexec.be"]}
    diffs = [_diff(fbi.FICHIER_CENV, l_cenv, cenv), _diff(fbc.FICHIER_H, l_h, h_montre)]
    diffs += [_diff(f"{dossier}/{nom}", [], fbi.decoupe(texte)) for nom, texte in montre.items()]
    res["diff"] = fbc._masque("\n".join(diffs))
    return res


def prepare(racine, r):
    """Voir l'en-tete : rien n'est ecrit, aucun mot de passe en clair."""
    res = _calcule(racine, r)
    return {k: res.get(k, "") for k in ("env", "dossier", "define", "diff", "empreinte", "avertissements", "refus",
                                         "apercu")}


def _resume(res, r):
    lignes = [f"env : {res['env']}", f"dossier : {res['dossier']}", f"define : {res['define']}", f"role : {r.role}"]
    if r.role == "esclave":
        lignes.append(f"id : {r.id} (maitre : {r.maitre})")
    lignes += [f"IP : {r.ip}", f"topic : {r.topic or fbc.identite_par_defaut(r.lieu, r.nom)['MQTT_TOPIC']}",
               "blocs : " + (", ".join(r.blocs) or "aucun")]
    if r.metiers:
        lignes.append("metiers : " + ", ".join(r.metiers))
    ecrits = [f"{res['dossier']}/{n}" for n in res["fichiers"]] + [fbc.FICHIER_H, fbi.FICHIER_CENV]
    return "\n".join(lignes + ["fichiers ecrits :"] + [f"  {x}" for x in ecrits])


def cree(racine, r, empreinte_lue, builds_en_cours):
    """Ecrit les trois morceaux dans une Transaction (voir l'en-tete)."""
    builds = builds_en_cours()
    if builds is None:
        raise RuntimeError("impossible de savoir si un build tourne : creation refusee")
    if builds:
        raise RuntimeError("un build est en cours (" + ", ".join(builds) + ") : creation refusee")
    racine = Path(racine)
    res = _calcule(racine, r)
    if res.get("empreinte") != empreinte_lue:
        raise RuntimeError("le cenv, le .h, le modele ou la saisie ont change depuis le diff : refaire « Voir le diff »")
    if res["refus"]:
        raise RuntimeError(" ; ".join(res["refus"]))
    eol_cenv, eol_h = res["eol"]
    with tempfile.TemporaryDirectory() as tmp:               # dossier monte hors depot, copie en une etape annulable
        for nom, texte in res["fichiers"].items():
            Path(tmp, nom).write_bytes(texte.encode("utf-8", errors="surrogateescape"))
        with fbs.Transaction(racine, "creation-assistant") as tr:
            tr.copie_dossier(tmp, res["dossier"])
            tr.ecrit(fbc.FICHIER_H, fbc._encode(res["h"], eol_h))
            tr.ecrit(fbi.FICHIER_CENV, fbc._encode(res["cenv"], eol_cenv))
    return {"cree": True, "env": res["env"], "dossier": res["dossier"], "diff": res["diff"],
            "avertissements": res["avertissements"], "sauvegarde": str(tr.dossier), "resume": _resume(res, r),
            "liens": {"build": LIEN_BUILD + res["env"], "fichiers": LIEN_FICHIERS + res["env"]}}
