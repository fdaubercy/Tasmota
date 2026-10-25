"""Renommage d'un env (page « Fichiers Berry par env », spec §10) : nouveau lieu et/ou nom, identite reproposee.

Le renommage se fait SUR PLACE (renommer puis revenir rend le cenv octet pour octet) :
  1. cenv : la section est reprise telle quelle (ports compris : c'est la meme carte), en-tete, chemins du
     dossier et define remplaces ; a sa place si le lieu ne change pas, sinon sous le bandeau du nouveau lieu ;
  2. .h : la section est remplacee la ou elle est, identite nouvelle (comme une creation) ; section partagee
     (#if defined(A) || defined(B)) : copie ajoutee apres elle et seul defined(X) quitte la condition ;
  3. dossier data/<lieu>/<carte> DEPLACE (pas copie), _persist.json aux valeurs d'identite nouvelles ;
  4. default_envs : la ligne garde son etat (active ou commentee) au nouveau nom ; data_dir suit le dossier.
Une seule Transaction (atomique, sauvegardes horodatees). L'identite actuelle de l'env ne compte pas dans le
controle d'unicite : garder son IP est permis. Seules les cartes se renomment ; rien n'est commite.
"""

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import fichiers_berry_creation as fbc
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi
import fichiers_berry_sauvegarde as fbs
import fichiers_berry_suppression as fbx


@dataclass
class Renommage:
    env: str                        # env a renommer (une carte du cenv)
    lieu: str
    nom: str
    identite: dict = field(default_factory=dict)    # CHAMPS_IDENTITE -> valeur
    define: str = ""                # vide -> fichiers_berry_creation.define(base, lieu, nom)


def _base(ini, env):
    ext = ini.sections["env:" + env].get("extends")
    parents = ext.morceaux[0][1] if ext and ext.morceaux else ""
    premier = parents.split(",")[0].strip()
    return premier[len("env:"):] if premier.startswith("env:") else premier


def _copie_section(lignes, env, nouvel_env, dossier, nouveau_dossier, ancien, nouveau):
    """(debut, fin utile, lignes reecrites) de la section de l'env dans le cenv."""
    debut, fin = fbc._regions(lignes)["env:" + env]
    k = fbc._fin_utile(lignes, debut, fin)
    copie = [lignes[debut].replace("env:" + env, "env:" + nouvel_env, 1)]
    copie += [re.sub(r"\b" + ancien + r"\b", nouveau, l.replace(dossier, nouveau_dossier)) for l in lignes[debut + 1:k]]
    return debut, k, copie


def _h(l_h, env, nouvel_env, ancien, nouveau, identite, av, refus):
    bornes = fbc._section_h(l_h, ancien)
    if bornes is None:
        refus.append(f"{fbc.FICHIER_H} : aucune section pour {ancien}")
        return l_h
    debut, ouv, fin = bornes
    bloc = fbc._copie_h(l_h, bornes, nouvel_env, nouveau, identite, av)
    if len(re.findall(r"defined\(\s*\w+\s*\)", l_h[ouv])) > 1:      # partagee : copie apres elle, terme retire
        return fbx.retire_h(l_h[:fin] + bloc + l_h[fin:], ancien, av, refus)
    if l_h[ouv].lstrip().startswith("#if"):
        bloc[1] = bloc[1].replace("#elif", "#if", 1)
    commentaires = [l.replace(env, nouvel_env) for l in l_h[debut:ouv]]
    if commentaires and not any(env in l for l in l_h[debut:ouv]):
        av.append(f"{fbc.FICHIER_H} : commentaire de la section sans le nom de l'env, garde tel quel (a revoir) : "
                  + commentaires[0].strip())
    bloc = commentaires + bloc[1:]
    return l_h[:debut] + bloc + l_h[fin:]


def _calcule(racine, r):
    racine = Path(racine)
    cartes = [e["nom"] for e in fbe.envs_proposes(racine) if e["famille"] == "cartes"]
    if r.env not in cartes:
        raise LookupError(f"seules les cartes du cenv se renomment : {r.env!r}")
    ini = fbi.lit_sections(racine)
    (o_c, e_c, l_c), (o_h, e_h, l_h), (o_o, e_o, l_o) = (fbx.lit(racine, f) for f in
                                                          (fbi.FICHIER_CENV, fbc.FICHIER_H, fbx.OVERRIDE))
    base = _base(ini, r.env)
    nouvel_env = fbc.nom_env(base, r.lieu, r.nom)
    nouveau = r.define or fbc.define(base, r.lieu, r.nom)
    dossier, ancien = fbe.dossier_carte(r.env), fbx.define_de(ini, r.env)
    nouveau_dossier = fbe.dossier_carte(nouvel_env) if fbc.NOM.fullmatch(r.nom) and fbc.LIEU.fullmatch(r.lieu) else ""
    demande = json.dumps(asdict(r), sort_keys=True, ensure_ascii=False).encode("utf-8")
    res = {"env": r.env, "nouvel_env": nouvel_env, "dossier": dossier, "nouveau_dossier": nouveau_dossier,
           "define": nouveau, "avertissements": [], "refus": [], "diff": "", "eol": (e_c, e_h, e_o),
           "empreinte": hashlib.sha256(b"\0".join((o_c, o_h, o_o, fbc._octets(racine / dossier / "_persist.json")
                                                    if dossier else b"", demande))).hexdigest()}
    av, refus = res["avertissements"], res["refus"]
    if nouvel_env == r.env:
        refus.append("le nouveau nom est celui de l'env : rien a renommer")
    dependants = fbx.references(ini, r.env)
    if dependants:
        refus.append(f"{r.env} est utilise par d'autres envs : " + ", ".join(dependants))
    if not ancien or not (racine / dossier).is_dir():
        refus.append(f"{r.env} incomplet : -D FIRMWARE_ du cenv ou dossier {dossier} manquant")
    if refus:
        return res
    sans_c, sans_h = fbx.retire_cenv(l_c, r.env, []), fbx.retire_h(l_h, ancien, [], [])
    c = fbc.Creation(modele=r.env, base=base, lieu=r.lieu, nom=r.nom, identite=r.identite, define=r.define)
    refus += fbc._refus(racine, ini, c, nouvel_env, nouveau_dossier, nouveau, "\n".join(sans_h), "\n".join(sans_c),
                        sauf_dossier=dossier, avertissements=av)
    if refus:
        return res
    debut, k, copie = _copie_section(l_c, r.env, nouvel_env, dossier, nouveau_dossier, ancien, nouveau)
    if r.lieu == r.env.split("-")[1]:
        res["cenv"] = l_c[:debut] + copie + l_c[k:]
    else:
        res["cenv"] = fbc._insere_cenv(ini, sans_c, r.lieu, copie, sauf=r.env)
    res["h"] = _h(l_h, r.env, nouvel_env, ancien, nouveau, r.identite, av, refus)
    res["override"] = fbx.maj_override(l_o, r.env, dossier, av, nouvel_env, nouveau_dossier)
    t_persist = fbc._texte(fbc._octets(racine / dossier / "_persist.json"))
    res["persist"] = fbc._persist(t_persist, r.identite, av) if t_persist else None
    fbx.citations(racine, r.env, av, {fbi.FICHIER_CENV: res["cenv"], fbx.OVERRIDE: res["override"]})
    textes = [fbx.diff(l_c, res["cenv"], fbi.FICHIER_CENV), fbx.diff(l_h, res["h"], fbc.FICHIER_H),
              fbx.diff(l_o, res["override"], fbx.OVERRIDE), f"dossier deplace : {dossier} -> {nouveau_dossier}"]
    if res["persist"] is not None:
        textes.append(fbx.diff(fbi.decoupe(t_persist), fbi.decoupe(res["persist"]), nouveau_dossier + "/_persist.json"))
    res["diff"] = fbc._masque("\n".join(t for t in textes if t))
    return res


def prepare_renommage(racine, r):
    """{env, nouvel_env, dossier, nouveau_dossier, define, diff (secrets masques), empreinte, avertissements, refus}."""
    res = _calcule(racine, r)
    return {k: res[k] for k in ("env", "nouvel_env", "dossier", "nouveau_dossier", "define", "diff", "empreinte",
                                "avertissements", "refus")}


def renomme(racine, r, empreinte_lue, builds_en_cours):
    """Renomme l'env (atomique). RuntimeError (-> 409) : build, fichiers ou saisie changes depuis le diff, refus."""
    builds = builds_en_cours()
    if builds is None:
        raise RuntimeError("impossible de savoir si un build tourne : renommage refuse")
    if builds:
        raise RuntimeError("un build est en cours (" + ", ".join(builds) + ") : renommage refuse")
    res = _calcule(racine, r)
    if res["empreinte"] != empreinte_lue:
        raise RuntimeError("les fichiers ou la saisie ont change depuis le diff : refaire le diff")
    if res["refus"]:
        raise RuntimeError(" ; ".join(res["refus"]))
    e_c, e_h, e_o = res["eol"]
    _, _, l_o = fbx.lit(racine, fbx.OVERRIDE)
    with fbs.Transaction(racine, "renommage") as tr:
        tr.ecrit(fbi.FICHIER_CENV, fbc._encode(res["cenv"], e_c))
        tr.ecrit(fbc.FICHIER_H, fbc._encode(res["h"], e_h))
        if res["override"] != l_o:
            tr.ecrit(fbx.OVERRIDE, fbc._encode(res["override"], e_o))
        tr.renomme(res["dossier"], res["nouveau_dossier"])
        if res["persist"] is not None:
            tr.ecrit(res["nouveau_dossier"] + "/_persist.json", res["persist"].encode("utf-8", errors="surrogateescape"))
    return {"renomme": True, "env": res["nouvel_env"], "dossier": res["nouveau_dossier"], "sauvegarde": str(tr.dossier),
            "avertissements": res["avertissements"]}
