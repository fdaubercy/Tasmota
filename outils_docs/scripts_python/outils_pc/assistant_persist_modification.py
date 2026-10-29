"""Modification d'un env existant par l'assistant de persist (spec 2026-10-27 §10, page 7900).

Partie 1 : recenser les cartes du parc et relire les reponses d'une carte depuis son persist.
  cartes(racine)                -> [{env, dossier, puce}] : envs « cartes » dont le dossier porte un _persist.json.
  reponses_de_l_env(racine, env) -> Reponses relues (reponses_depuis_persist + base + define). LookupError : pas une
                                   carte ; ValueError : persist illisible ou reponses refusees (jamais une valeur du persist).
  charge_env(racine, env)       -> {env, reponses (sans mot de passe : Reponses n'en porte pas), reglages_propres,
                                   avertissements}. reglages_propres = chemins du vrai persist qui different de ce que
                                   l'assistant regenererait (cles propres, retouches) : conserves a la modification.

Partie 2 : preparer puis ecrire la modification (spec §10.2) en appliquant au VRAI fichier le seul ecart A -> B
(A = reponses relues, B = reponses de la page), jamais une regeneration.
  prepare_modification(racine, env, r) -> {env, dossier, diff (masque), empreinte, avertissements, refus, vide,
                                   chemins}. Rien n'est ecrit. `chemins` = chemins JSON de l'ecart du persist (jamais
                                   une valeur). Ecart vide -> aucun controle, `vide` vrai, aucun refus.
  modifie(racine, env, r, empreinte_lue, builds_en_cours) -> {modifie, env, diff, sauvegarde, avertissements}.
                                   RuntimeError (409) : build en cours ou inconnu, refus, empreinte perimee ;
                                   ValueError (400) : ecart vide. Une Transaction : tout ou rien.
Refus : lieu, nom, puce, base ou define changes (renommer : page 7800) ; bloc de A introuvable dans le vrai fichier
(ligne retouchee a la main) -> TOUTE la modification est refusee, le refus cite le fichier et les lignes ; ligne qui
serait en double (ex. un esclave dont l'autoexec porte deja controleRangeExtender, page qui coche rangeExtender :
refuse, jamais deux fois la meme ligne). Mots de passe : A et B generes avec les vrais, diff, refus et erreurs masques
(regex de fbc._masque, puis toute valeur de secret remplacee par ***).
"""

import difflib
import hashlib
import json
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path

import assistant_persist_creation as apc
import assistant_persist_delta as delta
import assistant_persist_generation as gen
import assistant_persist_modele as apm
import assistant_persist_parc as parc
import assistant_persist_texte as texte
import fichiers_berry_coprocesseur as fbcp
import fichiers_berry_creation as fbc
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi
import fichiers_berry_renommage as fbr
import fichiers_berry_sauvegarde as fbs
import fichiers_berry_suppression as fbx

PUCES = {prefixe: puce for puce, prefixe in parc.PREFIXES.items()}


def cartes(racine):
    """Les cartes du parc : famille « cartes » du cenv avec un _persist.json dans leur dossier."""
    res = []
    for e in fbe.envs_proposes(racine):
        if e["famille"] != "cartes":
            continue
        dossier = fbe.dossier_carte(e["nom"])
        if (Path(racine) / dossier / "_persist.json").is_file():
            res.append({"env": e["nom"], "dossier": dossier, "puce": PUCES.get(e["nom"].split("-")[0], "")})
    return res


def _persist_de(racine, env):
    """(dict du persist de la carte, texte de son chemin) ; LookupError si l'env n'est pas une carte."""
    carte = next((c for c in cartes(racine) if c["env"] == env), None)
    if carte is None:
        raise LookupError(f"{env} n'est pas une carte du parc")
    try:
        donnees = json.loads((Path(racine) / carte["dossier"] / "_persist.json").read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"{carte['dossier']}/_persist.json illisible : {exc.strerror or exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{carte['dossier']}/_persist.json ligne {exc.lineno} : {exc.msg}") from exc
    if not isinstance(donnees, dict):
        raise ValueError(f"{carte['dossier']}/_persist.json : un objet JSON est attendu")
    return donnees


def _relit(racine, env):
    """(modele, persist, Reponses) ; toute cle manquante devient une ValueError qui nomme la cle seulement."""
    donnees = _persist_de(racine, env)
    modele = apm.charge_modele(racine)
    try:
        r = gen.reponses_depuis_persist(modele, donnees, env, racine)
    except (KeyError, TypeError, AttributeError, StopIteration) as exc:
        cle = f" (cle {exc.args[0]!r})" if isinstance(exc, KeyError) else ""
        raise ValueError(f"{env} : persist incomplet ou dont le role n'est pas decrit par le modele{cle}") from None
    ini = fbi.lit_sections(racine)
    r.base = fbr._base(ini, env)
    r.define = fbx.define_de(ini, env) or ""
    return modele, donnees, r


def reponses_de_l_env(racine, env):
    modele, _, r = _relit(racine, env)
    gen.variables(racine, r)                                  # ValueError : role, heure, ip ou maitre inadmissibles
    return r


def charge_env(racine, env):
    modele, donnees, r = _relit(racine, env)
    v = gen.variables(racine, r)
    A = gen.persist(modele, r, v, gen.secrets_reponses(racine, r))
    return {"env": env, "reponses": asdict(r), "reglages_propres": len(texte.ecart(A, donnees)),
            "avertissements": []}


# ---- Partie 2 : preparer et ecrire la modification --------------------------------------------------------------
FIGES = ("lieu", "nom", "puce", "base", "define")
NON_SIGNIFICATIVES = ("end",)
COMMENTAIRES = (";", "//", "#if", "#el", "#end")


def _doublons(avant, apres, genere):
    """Lignes significatives devenues doubles : leur nombre augmente, depasse 1 et depasse celui de B genere (une
    ligne legitimement presente deux fois dans le modele, ex. un fichier dans deux listes du cenv, n'est pas un doublon)."""
    def compte(lignes):
        return Counter(s for s in (l.strip() for l in lignes)
                       if s and s not in NON_SIGNIFICATIVES and not s.startswith(COMMENTAIRES))
    ca, cb, cg = compte(avant), compte(apres), compte(genere)
    return [x for x, n in cb.items() if n > 1 and n > ca[x] and n > cg[x]]


def _cache(txt, secrets):
    """Texte masque : regex du depot, puis toute valeur de secret en clair (une valeur retouchee a la main aussi)."""
    txt = fbc._masque(txt)
    for s in secrets:
        txt = txt.replace(s, "***")
    return txt


def _diff(nom, avant, apres):
    return "\n".join(difflib.unified_diff(avant, apres, nom, nom, lineterm="", n=1))


def _applique_section(fichier, reel, a, b, refus):
    """Lignes apres l'ecart A -> B ; les blocs de A introuvables dans `reel` vont (masques) dans `refus`."""
    nouv, ref = delta.applique_lignes(reel, a, b)
    refus += [f"{fichier} : {x}" for x in ref]
    return nouv


def _calcule(racine, env, r):
    """_calcule_brut ; une ValueError de generation (secret du modele sans valeur...) devient un refus.
    LookupError (pas une carte) remonte : c'est un 404 pour la page.
    Point UNIQUE de masquage : refus, avertissements et diff sortent tous d'ici, retours anticipes et repli compris ;
    `secrets` est rempli des que les mots de passe sont connus (avant toute citation de ligne)."""
    secrets = set()
    try:
        res = _calcule_brut(Path(racine), env, r, secrets)
    except ValueError as exc:
        res = {"env": env, "dossier": fbe.dossier_carte(env), "diff": "", "empreinte": "", "avertissements": [],
               "refus": [str(exc)], "vide": False, "chemins": []}
    for cle in ("refus", "avertissements"):
        res[cle] = [_cache(x, secrets) for x in res[cle]]
    res["diff"] = _cache(res["diff"], secrets)
    return res


def _calcule_brut(racine, env, r, secrets):
    d = fbe.dossier_carte(env)
    res = {"env": env, "dossier": d, "diff": "", "empreinte": "", "avertissements": [], "refus": [], "vide": False,
           "chemins": []}
    refus = res["refus"]
    a = reponses_de_l_env(racine, env)                        # LookupError / ValueError : voir _calcule
    b = replace(r, base=r.base or a.base, define=r.define or a.define)    # page muette sur base / define : inchanges
    rel = {"cenv": fbi.FICHIER_CENV, "h": fbc.FICHIER_H, "modele": apm.FICHIER_MODELE, "persist": d + "/_persist.json",
           "autoexec": d + "/autoexec.be"}
    o = {k: fbc._octets(racine / f) for k, f in rel.items()}
    res["empreinte"] = hashlib.sha256(b"\0".join(
        list(o.values()) + [env.encode("utf-8"), json.dumps(asdict(r), sort_keys=True, ensure_ascii=False).encode("utf-8")]
    )).hexdigest()
    for champ in FIGES:
        if getattr(a, champ) != getattr(b, champ):
            refus.append(f"{champ} : non modifiable ici (renommer ou changer de puce ou de base : page 7800, ou creer une autre carte)")
    for k in ("persist", "autoexec"):
        if not (racine / rel[k]).is_file():
            refus.append(f"{rel[k]} : fichier absent")
    if refus:
        return res
    modele = apm.charge_modele(racine)
    va, vb = gen.variables(racine, a), gen.variables(racine, b)
    sa, sb = gen.secrets_reponses(racine, a), gen.secrets_reponses(racine, b)
    secrets.update(x for x in (*sa.values(), *sb.values()) if x)
    # 3. persist : ecart par chemin JSON, applique dans le texte
    PA, PB = gen.persist(modele, a, va, sa), gen.persist(modele, b, vb, sb)
    ops = texte.ecart(PA, PB)
    res["chemins"] = [".".join(c) for c, *_ in ops]
    t_p = fbc._texte(o["persist"])
    absents = texte.ecart_applicable(t_p, ops)
    n_p = t_p
    if absents:
        refus.append(f"{rel['persist']} : objets absents du fichier (retouche a la main ?) : {', '.join(absents)}")
    else:
        try:
            n_p = texte.applique(t_p, ops)
            json.loads(n_p)
        except (LookupError, ValueError, IndexError):
            refus.append(f"{rel['persist']} : ecart non applicable au fichier : {', '.join(res['chemins'])}")
            n_p = t_p
    # 4. autoexec
    t_a = fbc._texte(o["autoexec"])
    l_a = fbi.decoupe(t_a)
    n_a = _applique_section(rel["autoexec"], l_a, fbi.decoupe(gen.autoexec(modele, a)), fbi.decoupe(gen.autoexec(modele, b)), refus)
    # 5. section du cenv
    t_c, t_h = fbc._texte(o["cenv"]), fbc._texte(o["h"])
    l_c, l_h = fbi.decoupe(t_c), fbi.decoupe(t_h)
    bornes = fbc._regions(l_c).get("env:" + env)
    if bornes is None:
        refus.append(f"{rel['cenv']} : section [env:{env}] introuvable")
        return res
    ignore = []
    sec_a = fbcp.adapte_cenv(apc._section_cenv(modele, va, gen.listes_cenv(modele, a)), fbcp.est_p4(va["base"]), ignore)
    sec_b = fbcp.adapte_cenv(apc._section_cenv(modele, vb, gen.listes_cenv(modele, b)), fbcp.est_p4(vb["base"]), ignore)
    s_c = _applique_section(rel["cenv"], l_c[bornes[0]:bornes[1]], sec_a, sec_b, refus)
    n_c = l_c[:bornes[0]] + s_c + l_c[bornes[1]:]
    # 6. section du .h
    h_b = fbc._section_h(l_h, va["define"])
    if h_b is None:
        refus.append(f"{rel['h']} : section de {va['define']} introuvable")
        return res
    s_h = _applique_section(rel["h"], l_h[h_b[0]:h_b[2]], apc._section_h(modele, a, va, sa), apc._section_h(modele, b, vb, sb), refus)
    n_h = l_h[:h_b[0]] + s_h + l_h[h_b[2]:]
    # 9. squelettes des metiers nouveaux, jamais sur un fichier deja present
    eol_c = fbc._eol(t_c)
    nouveaux = [m for m in dict.fromkeys(b.metiers) if m not in a.metiers]
    squelettes = {}
    for m in nouveaux if b.squelettes else []:
        for nom, txt in gen.squelettes(modele, m).items():
            if (racine / d / nom).exists():
                res["avertissements"].append(f"{d}/{nom} existe deja : laisse tel quel")
            else:
                squelettes[f"{d}/{nom}"] = apc._eol_texte(txt, eol_c)
    t_a_eol = fbc._eol(t_a)
    avant = {rel["persist"]: fbi.decoupe(t_p), rel["autoexec"]: l_a, rel["cenv"]: l_c, rel["h"]: l_h}
    apres = {rel["persist"]: fbi.decoupe(n_p), rel["autoexec"]: n_a, rel["cenv"]: n_c, rel["h"]: n_h}
    ecritures = {f: fbc._encode(apres[f], e) for f, e in ((rel["autoexec"], t_a_eol), (rel["cenv"], fbc._eol(t_c)),
                                                          (rel["h"], fbc._eol(t_h))) if apres[f] != avant[f]}
    if n_p != t_p:                                            # le persist garde ses octets : seul l'ecart est ecrit
        ecritures[rel["persist"]] = n_p.encode("utf-8", errors="surrogateescape")
    res["vide"] = not ecritures and not squelettes and not refus
    if res["vide"]:
        return res                                            # rien ne change : rien a controler, rien a ecrire
    # 7. controles de B
    gb = {rel["autoexec"]: fbi.decoupe(gen.autoexec(modele, b)), rel["cenv"]: sec_b, rel["h"]: apc._section_h(modele, b, vb, sb)}
    sections = {rel["autoexec"]: (l_a, n_a), rel["cenv"]: (l_c[bornes[0]:bornes[1]], s_c), rel["h"]: (l_h[h_b[0]:h_b[2]], s_h)}
    for f, g in gb.items():                                   # par section : une ligne d'une autre carte n'est pas un doublon
        refus += [f"{f} : ligne deja presente, elle serait en double : {x}" for x in _doublons(*sections[f], g)]
    refus += gen.coherence(modele, b, PB, gen.autoexec(modele, b), gen.listes_cenv(modele, b), racine)
    erreurs = apc._erreurs_schema(racine, PB)
    if erreurs:
        refus.append("persist genere refuse par le schema : " + ", ".join(erreurs[:12]))
    if nouveaux:
        refus += apc._refus_metiers(racine, replace(b, metiers=nouveaux))
    elif not b.metiers or len(set(b.metiers)) != len(b.metiers):
        refus += apc._refus_metiers(racine, b)
    ia, ib = apc._identite_h(va), apc._identite_h(vb)
    changes = {c for c in ib if ib[c] != ia[c]}
    refus += [x for x in fbc.refus_identite(ib) if x.split(" ")[0] in changes]
    for champ in ("reseau1", "reseau2", "nom_template"):
        if vb[champ] != va[champ] and any(x in vb[champ] for x in apc.INTERDITS_H):
            refus.append(f"{champ} : caractere interdit dans une chaine du .h")
    hors = "\n".join(l_h[:h_b[0]] + l_h[h_b[2]:])               # les AUTRES cartes seulement, pas l'env contre lui-meme
    fbc.avertit_prises(racine, hors, {c: ib[c] for c in changes}, res["avertissements"], d)
    if b.role == "esclave" and b.id != a.id and [e for e in parc.ids_pris(racine).get(b.id, []) if e != d]:
        res["avertissements"].append(f"id {b.id} deja pris par une autre carte : deux esclaves de meme id se repondent l'un a l'autre")
    diffs = [_diff(f, avant[f], apres[f]) for f in ecritures if f in avant]
    diffs += [_diff(f, [], fbi.decoupe(txt)) for f, txt in squelettes.items()]
    res["diff"] = "\n".join(x for x in diffs if x)
    res["_ecritures"] = {**ecritures, **{f: txt.encode("utf-8") for f, txt in squelettes.items()}}
    return res


def prepare_modification(racine, env, r):
    """Voir l'en-tete : rien n'est ecrit, aucun mot de passe en clair."""
    res = _calcule(racine, env, r)
    return {k: res[k] for k in ("env", "dossier", "diff", "empreinte", "avertissements", "refus", "vide", "chemins")}


def modifie(racine, env, r, empreinte_lue, builds_en_cours):
    """Ecrit l'ecart dans une Transaction (voir l'en-tete)."""
    builds = builds_en_cours()
    if builds is None:
        raise RuntimeError("impossible de savoir si un build tourne : modification refusee")
    if builds:
        raise RuntimeError("un build est en cours (" + ", ".join(builds) + ") : modification refusee")
    res = _calcule(racine, env, r)
    if res["refus"]:
        raise RuntimeError(" ; ".join(res["refus"]))
    if res["empreinte"] != empreinte_lue:
        raise RuntimeError("les fichiers de la carte, le modele ou la saisie ont change depuis le diff : refaire « Voir le diff »")
    if res["vide"]:
        raise ValueError("aucun changement : rien a modifier")
    with fbs.Transaction(racine, "modification-assistant") as tr:
        for f, octets in res["_ecritures"].items():
            tr.ecrit(f, octets)
    return {"modifie": True, "env": env, "diff": res["diff"], "sauvegarde": str(tr.dossier),
            "avertissements": res["avertissements"]}
