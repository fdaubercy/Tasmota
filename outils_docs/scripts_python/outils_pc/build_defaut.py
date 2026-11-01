"""Bloc `default_envs` de platformio_override.ini, ce que compile un `pio run` sans -e (onglet « Envs par defaut » de la
page Build, plan tasks/plans/default-envs-page.md).

Une ligne du bloc = un env, active ou commentee. Seul cet etat change : commentaires de groupe, indentation, espaces de
fin et fins de ligne restent tels quels, comme le reste du fichier. Un env de Mes cartes / Mes bases sans ligne dans le
bloc est propose ; il n'y est ajoute, au groupe de sa puce, que s'il est coche.

L'ordre du bloc ne compte pas : `pio run` suit l'ordre des sections du .ini (platformio/run/cli.py).
Liste vide refusee : sans env actif, `pio run` construirait TOUS les envs.
Toute modification change l'empreinte du projet (project/helpers.py::compute_project_checksum hache la config) : le
`pio run` suivant vide .pio/build ; les objets inchanges reviennent du cache .cache.
"""

import hashlib
import re
from pathlib import Path

import build_envs
import fichiers_berry_sauvegarde as fbs
from fichiers_berry_suppression import bloc_default_envs

FICHIER = build_envs.FICHIER_OVERRIDE
GROUPES = ("Safeboot", "ESP32", "ESP32-S3", "ESP32-P4", "Autres")
LIGNE = re.compile(r"(\s*)(;\s*)?([A-Za-z0-9_.-]+)(\s*)")
PURGE = "le prochain pio run videra .pio/build ; les objets inchangés reviennent du cache .cache"


def groupe(nom):
    """Colonne de l'onglet, tiree du nom de l'env (les memes groupes que les commentaires du bloc)."""
    if "safeboot" in nom:
        return "Safeboot"
    if nom.startswith("tasmota32p4"):
        return "ESP32-P4"
    if nom.startswith("tasmota32s3"):
        return "ESP32-S3"
    return "ESP32" if re.match(r"tasmota32(-|$)", nom) else "Autres"


def _analyse(texte, connus):
    """(lignes, bloc, {env: [indices]}, actifs, erreurs). Une ligne commentee n'est un env que si elle en nomme un connu."""
    lignes = texte.splitlines(keepends=True)
    bloc = bloc_default_envs(lignes)
    if not bloc:
        return lignes, bloc, {}, [], [f"{FICHIER} : bloc default_envs introuvable"]
    erreurs = []
    if lignes[bloc[0]].split("=", 1)[1].split(";")[0].strip():
        erreurs.append(f"{FICHIER} : valeur sur la ligne default_envs elle-même, à déplacer d'abord à la main")
    entrees, actifs = {}, []
    for i in bloc[1:]:
        s = lignes[i].rstrip("\r\n")
        m = LIGNE.fullmatch(s)
        if m and (not m.group(2) or m.group(3) in connus):
            entrees.setdefault(m.group(3), []).append(i)
            if not m.group(2) and m.group(3) not in actifs:
                actifs.append(m.group(3))
        elif s.strip() and s.strip()[0] not in ";#":
            erreurs.append(f"{FICHIER}, ligne {i + 1} non gérée : {s.strip()}")
    return lignes, bloc, entrees, actifs, erreurs


def _lit(racine):
    chemin = Path(racine) / FICHIER
    return chemin.read_bytes().decode("utf-8") if chemin.is_file() else ""


def _ancre(lignes, bloc, entrees, nom):
    """Indice de la ligne apres laquelle ajouter `nom` : dernier env de son groupe, sinon derniere ligne utile du bloc."""
    du_groupe = [i for env, indices in entrees.items() if groupe(env) == groupe(nom) for i in indices]
    return max(du_groupe) if du_groupe else max(i for i in bloc if lignes[i].strip())


def _bascule(ligne, active):
    corps = ligne.rstrip("\r\n")
    fin = ligne[len(corps):]
    m = LIGNE.fullmatch(corps)
    return m.group(1) + ("" if active else "; ") + m.group(3) + m.group(4) + fin


def prepare(racine, coches, nouveau=None):
    """Futur fichier et controles ; rien n'est ecrit. Apercu : une entree {t: texte, m: "" | "modif" | "ajout"} par ligne.
    `nouveau` : env en cours de creation, valable bien qu'il ne soit pas encore dans le cenv."""
    if not isinstance(coches, list) or not all(isinstance(c, str) for c in coches):
        raise ValueError("coches attendu : liste de noms d'envs")
    coches = sorted(set(coches))
    avant = _lit(racine)
    envs = build_envs.liste_envs(racine)
    connus = {e.nom for e in envs} | ({nouveau} if nouveau else set())
    lignes, bloc, entrees, _, erreurs = _analyse(avant, connus)
    if not coches:
        erreurs.append("aucun env coché : un pio run sans -e construirait tous les envs")
    erreurs += [f"env inconnu : {c} (pio run refuserait de démarrer)" for c in coches if c not in connus]
    apercu = [{"t": l, "m": ""} for l in lignes]
    if not erreurs:
        ajouts = {}
        for c in coches:
            if c not in entrees:
                ajouts.setdefault(_ancre(lignes, bloc, entrees, c), []).append(c)
        for i in bloc[1:]:
            m = LIGNE.fullmatch(lignes[i].rstrip("\r\n"))
            if m and m.group(3) in entrees and (not m.group(2)) != (m.group(3) in coches):
                apercu[i] = {"t": _bascule(lignes[i], m.group(3) in coches), "m": "modif"}
        for ancre in sorted(ajouts, reverse=True):       # de la fin vers le debut : les indices restent valables
            voisine = LIGNE.fullmatch(lignes[ancre].rstrip("\r\n"))
            retrait = voisine.group(1) if voisine else "    "    # aucun env dans le bloc : pio exige un retrait
            eol = "\r\n" if "\r\n" in avant else "\n"
            if not apercu[ancre]["t"].endswith(("\n", "\r")):
                apercu[ancre] = dict(apercu[ancre], t=apercu[ancre]["t"] + eol)
            apercu[ancre + 1:ancre + 1] = [{"t": f"{retrait}{c}{eol}", "m": "ajout"} for c in ajouts[ancre]]
    apres = "".join(a["t"] for a in apercu)
    inchange = apres == avant
    return {"fichier": FICHIER, "coches": coches, "apercu": apercu, "debut": bloc[0] if bloc else 0, "inchange": inchange,
            "apres": apres, "erreurs": erreurs, "avertissements": [] if inchange or erreurs else [PURGE],
            "empreinte": hashlib.sha256((avant + "\0" + ",".join(coches)).encode("utf-8")).hexdigest()}


def avec_env_cree(racine, env):
    """Le bloc avec `env`, en cours de creation, actif en plus de la liste actuelle (creation d'un env, si demande)."""
    actifs = _analyse(_lit(racine), {e.nom for e in build_envs.liste_envs(racine)} | {env})[3]
    return prepare(racine, actifs + [env], nouveau=env)


def lit(racine):
    """Etat du bloc : colonnes de l'onglet, envs actifs, et l'apercu du fichier tel qu'il est."""
    envs = build_envs.liste_envs(racine)
    connus = {e.nom for e in envs}
    _, _, entrees, actifs, _ = _analyse(_lit(racine), connus)
    propres = [e.nom for e in envs if e.famille in ("cartes", "bases")]
    noms = list(entrees) + [n for n in propres if n not in entrees]
    colonnes = [{"titre": g, "envs": [{"nom": n, "actif": n in actifs, "absent": n not in entrees, "inconnu": n not in connus}
                                      for n in noms if groupe(n) == g]} for g in GROUPES]
    p = prepare(racine, actifs)
    return {"groupes": [c for c in colonnes if c["envs"]], "actifs": actifs,
            **{k: p[k] for k in ("fichier", "apercu", "debut", "inchange", "erreurs", "avertissements", "empreinte")}}


def ecrit(racine, coches, empreinte_lue, builds_en_cours):
    """Ecrit le bloc en une Transaction (copie d'origine sauvegardee). RuntimeError (-> 409) : build en cours ou
    indetectable, liste refusee, rien a ecrire, fichier change depuis l'apercu."""
    builds = builds_en_cours()
    if builds is None:
        raise RuntimeError("impossible de savoir si un build tourne : écriture refusée")
    if builds:
        raise RuntimeError("un build est en cours (" + ", ".join(builds) + ") : écriture refusée")
    p = prepare(racine, coches)
    if p["erreurs"]:
        raise RuntimeError("liste refusée : " + " ; ".join(p["erreurs"]))
    if p["inchange"]:
        raise RuntimeError("le fichier contient déjà cette liste : rien à écrire")
    if p["empreinte"] != empreinte_lue:
        raise RuntimeError(f"{FICHIER} a changé depuis l'aperçu : relire l'aperçu puis enregistrer")
    with fbs.Transaction(racine, "default_envs") as tr:
        tr.ecrit(FICHIER, p["apres"].encode("utf-8"))
    return {"ecrit": True, "coches": p["coches"], "sauvegarde": str(tr.dossier)}
