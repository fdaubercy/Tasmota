"""Suppression d'un env (page « Fichiers Berry par env », spec §9) ; retraits reutilises par le renommage (§10).

Une carte tient en trois morceaux (fichiers_berry_creation) ; la supprimer, c'est :
  1. retirer sa section [env:...] du cenv (avec la ligne vide qui la precede : une creation suivie d'une
     suppression rend le cenv octet pour octet) ; les commentaires des autres sections restent ;
  2. retirer sa section du .h : propre -> retiree (la suivante devient #if si c'etait la tete de chaine) ;
     partagee (#if defined(A) || defined(B)) -> seul defined(X) part de la condition ;
  3. renommer son dossier data/<lieu>/<carte> en <carte>-sauvegarde (-2, -3... si pris) : les *sauvegarde*
     sont ignores par le recensement, les copies et les builds ;
  4. la retirer de default_envs (platformio_override.ini), ligne active ou commentee : un env actif inconnu
     fait echouer `pio run`. data_dir sur ce dossier : signale.
Le tout dans une Transaction (fichiers_berry_sauvegarde) : atomique, avec copie horodatee des fichiers.
Refus : env reference par un autre (extends, ${env:<env>...}), build en cours. Rien n'est commite.
"""

import difflib
import hashlib
import re
from pathlib import Path

import fichiers_berry_creation as fbc
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi
import fichiers_berry_sauvegarde as fbs

OVERRIDE = "platformio_override.ini"
SCRIPTS = "outils_docs/scripts_python"
OUVERTURE_H = re.compile(r" {8}#(?:el)?if\b")
BORNE_H = re.compile(r" {8}#(elif|else|endif)\b")


def define_de(ini, env):
    """Dernier -D FIRMWARE_... des build_flags propres de l'env, None sans."""
    flags = " ".join(v for _, v, _ in ini.sections["env:" + env].get("build_flags", fbi.Option("", "", "", 0)).morceaux)
    trouves = re.findall(r"-D\s*(FIRMWARE_\w+)", flags)
    return trouves[-1] if trouves else None


def references(ini, env):
    """Envs qui dependent de celui-ci : `extends` dans leur chaine, ou une reference ${env:<env>.option}."""
    section, res = "env:" + env, set()
    for autre in ini.envs_cenv():
        if autre != env and section in ini.chaine(autre):
            res.add(autre)
    for nom, options in ini.sections.items():
        if nom != section and any("${" + section + "." in v for o in options.values() for _, v, _ in o.morceaux):
            res.add(nom[len("env:"):] if nom.startswith("env:") else nom)
    return sorted(res)


def bandeau(ligne):
    """Ligne d'un bandeau de lieu du cenv : tirets `;----` ou `; LOCALISATION: ...`."""
    s = ligne.strip()
    return bool(re.fullmatch(r";-{20,}", s)) or s.startswith("; LOCALISATION:")


def retire_cenv(lignes, env, avertissements):
    """Lignes du cenv sans la section de l'env ; le bandeau de lieu juste au-dessus part aussi s'il ne
    couvre plus rien (lieu cree par une creation ou un renommage, puis vide)."""
    debut, fin = fbc._regions(lignes)["env:" + env]
    k = fbc._fin_utile(lignes, debut, fin)
    i = debut
    while i > 0 and lignes[i - 1].lstrip()[:1] in (";", "#") and lignes[i - 1].strip():
        i -= 1
    propres = [l.strip() for l in lignes[i:debut] if not bandeau(l)]
    if propres:                              # le bandeau du lieu n'est pas un commentaire de la section
        avertissements.append(f"{fbi.FICHIER_CENV} : commentaire au-dessus de la section, garde (a revoir) : "
                              + " / ".join(propres))
    haut = debut - 1 if debut > 0 and lignes[debut - 1] == "" else debut   # ligne vide inseree par une creation
    suite = [l for l in lignes[k:] if l.strip()]
    if i == debut - 3 and not propres and (not suite or bandeau(suite[0])):
        b = debut - 3 - (1 if debut > 3 and lignes[debut - 4] == "" else 0)
        avertissements.append(f"{fbi.FICHIER_CENV} : bandeau devenu vide retire : {lignes[debut - 2].strip()}")
        return lignes[:b] + lignes[k:]
    return lignes[:haut] + lignes[k:]


def retire_h(lignes, define, avertissements, refus):
    """Lignes du .h sans la section de `define` (ou sans son terme, section partagee)."""
    bornes = fbc._section_h(lignes, define)
    if bornes is None:
        avertissements.append(f"{fbc.FICHIER_H} : aucune section pour {define}, rien a retirer")
        return lignes
    debut, ouv, fin = bornes
    termes = re.findall(r"defined\(\s*(\w+)\s*\)", lignes[ouv])
    if len(termes) > 1:                      # section partagee : seul defined(X) part
        l = lignes[ouv]
        nouvelle = re.sub(r"\s*\|\|\s*defined\(\s*" + define + r"\s*\)", "", l, count=1)
        if nouvelle == l:
            nouvelle = re.sub(r"defined\(\s*" + define + r"\s*\)\s*\|\|\s*", "", l, count=1)
        restants = [t for t in termes if t != define]
        for c in lignes[ouv + 1:fin]:
            if any(re.search(r"\b" + t + r"\b", c) for t in termes):
                avertissements.append(f"{fbc.FICHIER_H} : condition interne a revoir a la main ({', '.join(restants)} "
                                      f"reste seul) : {c.strip()}")
        return lignes[:ouv] + [nouvelle] + lignes[ouv + 1:]
    res = list(lignes)
    if res[ouv].lstrip().startswith("#if"):  # tete de chaine : la section suivante devient #if
        j = next((i for i in range(fin, len(res)) if BORNE_H.match(res[i])), None)
        if j is None or not res[j].lstrip().startswith("#elif"):
            refus.append(f"{fbc.FICHIER_H} : {define} est la seule section de la chaine des firmwares")
            return lignes
        res[j] = res[j].replace("#elif", "#if", 1)
    return res[:debut] + res[fin:]


def ligne_default_envs(l, env):
    """(prefixe, suffixe) si la ligne de default_envs designe exactement l'env (active ou commentee), sinon None."""
    m = re.fullmatch(r"(\s*;?\s*)" + re.escape(env) + r"(\s*)", l)
    return (m.group(1), m.group(2)) if m else None


def bloc_default_envs(lignes):
    """Indices du bloc default_envs : sa ligne et les suivantes, jusqu'a la prochaine cle ou section."""
    d = next((i for i, l in enumerate(lignes) if re.match(r"default_envs\s*=", l)), None)
    if d is None:
        return range(0)
    return range(d, next((i for i in range(d + 1, len(lignes)) if re.match(r"[\[A-Za-z_]", lignes[i])), len(lignes)))


def _actifs(lignes, bloc):
    if not bloc:
        return []
    res = [v for v in re.split(r"[\s,]+", lignes[bloc[0]].split("=", 1)[1].split(";")[0]) if v]
    return res + [l.strip() for n, l in enumerate(lignes) if n in bloc[1:] and l.strip() and l.strip()[0] not in ";#"]


def maj_override(lignes, env, dossier, avertissements, nouvel_env=None, nouveau_dossier=None):
    """default_envs (son seul bloc) : ligne retiree (ou renommee, meme etat) ; data_dir : signale (ou suit le dossier)."""
    res, bloc = [], bloc_default_envs(lignes)
    for n, l in enumerate(lignes):
        bouts = ligne_default_envs(l, env) if n in bloc else None
        if bouts is not None:
            if nouvel_env:
                res.append(bouts[0] + nouvel_env + bouts[1])
            continue
        m = re.match(r"(data_dir\s*=\s*)(\S+)(\s*)$", l)
        if dossier and m and fbi.normalise(m.group(2)) == dossier:
            if nouveau_dossier:
                l = m.group(1) + nouveau_dossier + m.group(3)
            else:
                avertissements.append(f"{OVERRIDE} : data_dir = {dossier} (dossier supprime) : a changer avant un build")
        res.append(l)
    if not nouvel_env and _actifs(lignes, bloc) and not _actifs(res, bloc_default_envs(res)):
        avertissements.append(f"{OVERRIDE} : default_envs n'a plus aucun env actif : un `pio run` sans -e construirait "
                              "TOUS les envs ; decommenter un env")
    return res


def citations(racine, env, avertissements, apres):
    """Signale ce qui cite encore l'env, rien n'est modifie : fichiers .ini et scripts du depot ; pour les
    fichiers que l'on reecrit (`apres` : {fichier: lignes}), leur texte d'APRES le retrait."""
    motif = re.compile(r"(?<![\w-])" + re.escape(env) + r"(?![\w-])")
    fichiers = sorted(Path(racine).glob("platformio*.ini")) + sorted((Path(racine) / SCRIPTS).rglob("*.py"))
    for f in fichiers:
        rel = f.relative_to(racine).as_posix()
        try:
            lignes = apres.get(rel) or fbi.decoupe(f.read_bytes().decode("utf-8", errors="replace"))
        except OSError:
            continue
        for n, l in enumerate(lignes, 1):
            if motif.search(l):
                avertissements.append(f"cite encore {env} (non modifie) : {rel}:{n}")


def dossier_libre(racine, dossier, suffixe="-sauvegarde"):
    nom, n = dossier + suffixe, 2
    while (Path(racine) / nom).exists():
        nom, n = f"{dossier}{suffixe}-{n}", n + 1
    return nom


def lit(racine, fichier):
    o = fbc._octets(Path(racine) / fichier)
    t = fbc._texte(o)
    return o, fbc._eol(t), fbi.decoupe(t)


def diff(avant, apres, fichier):
    return "\n".join(difflib.unified_diff(avant, apres, fichier, fichier, lineterm="", n=1))


def _calcule(racine, env):
    racine = Path(racine)
    if env not in [e["nom"] for e in fbe.envs_proposes(racine)]:
        raise LookupError(f"env inconnu ou non modifiable (pas dans {fbi.FICHIER_CENV}) : {env!r}")
    ini = fbi.lit_sections(racine)
    (o_c, e_c, l_c), (o_h, e_h, l_h), (o_o, e_o, l_o) = (lit(racine, f) for f in (fbi.FICHIER_CENV, fbc.FICHIER_H, OVERRIDE))
    dossier = fbe.dossier_carte(env)
    res = {"env": env, "dossier": dossier, "dossier_sauvegarde": None, "avertissements": [], "refus": []}
    av, refus = res["avertissements"], res["refus"]
    dependants = references(ini, env)
    if dependants:
        refus.append(f"{env} est utilise par d'autres envs (extends ou ${{env:{env}...}}) : " + ", ".join(dependants))
    define = define_de(ini, env)
    res["cenv"] = retire_cenv(l_c, env, av)
    res["h"] = retire_h(l_h, define, av, refus) if define else l_h
    if not define:
        av.append(f"{env} n'a pas de -D FIRMWARE_... : {fbc.FICHIER_H} n'est pas touche")
    res["override"] = maj_override(l_o, env, dossier, av)
    if dossier and (racine / dossier).is_dir():
        res["dossier_sauvegarde"] = dossier_libre(racine, dossier)
    elif dossier:
        av.append(f"dossier {dossier} absent : rien a renommer")
    demande = (env + "\0" + (res["dossier_sauvegarde"] or "")).encode("utf-8")    # le nom -sauvegarde montre au diff
    res["empreinte"] = hashlib.sha256(b"\0".join((o_c, o_h, o_o, demande))).hexdigest()
    citations(racine, env, av, {fbi.FICHIER_CENV: res["cenv"], OVERRIDE: res["override"]})
    res["eol"] = (e_c, e_h, e_o)
    textes = [diff(l_c, res["cenv"], fbi.FICHIER_CENV), diff(l_h, res["h"], fbc.FICHIER_H),
              diff(l_o, res["override"], OVERRIDE)]
    if res["dossier_sauvegarde"]:
        textes.append(f"dossier renomme : {dossier} -> {res['dossier_sauvegarde']}")
    res["diff"] = fbc._masque("\n".join(t for t in textes if t))
    return res


def prepare_suppression(racine, env):
    """{env, dossier, dossier_sauvegarde, diff (secrets masques), empreinte, avertissements, refus}, sans ecrire."""
    r = _calcule(racine, env)
    return {k: r[k] for k in ("env", "dossier", "dossier_sauvegarde", "diff", "empreinte", "avertissements", "refus")}


def supprime(racine, env, empreinte_lue, builds_en_cours):
    """Supprime l'env (atomique). RuntimeError (-> 409) : build, empreinte perimee, refus."""
    builds = builds_en_cours()
    if builds is None:
        raise RuntimeError("impossible de savoir si un build tourne : suppression refusee")
    if builds:
        raise RuntimeError("un build est en cours (" + ", ".join(builds) + ") : suppression refusee")
    r = _calcule(racine, env)
    if r["empreinte"] != empreinte_lue:
        raise RuntimeError("les fichiers ou l'env demande ont change depuis le diff : refaire le diff")
    if r["refus"]:
        raise RuntimeError(" ; ".join(r["refus"]))
    (e_c, e_h, e_o), (_, _, l_h), (_, _, l_o) = r["eol"], lit(racine, fbc.FICHIER_H), lit(racine, OVERRIDE)
    with fbs.Transaction(racine, "suppression") as tr:
        tr.ecrit(fbi.FICHIER_CENV, fbc._encode(r["cenv"], e_c))
        if r["h"] != l_h:
            tr.ecrit(fbc.FICHIER_H, fbc._encode(r["h"], e_h))
        if r["override"] != l_o:
            tr.ecrit(OVERRIDE, fbc._encode(r["override"], e_o))
        if r["dossier_sauvegarde"]:
            tr.renomme(r["dossier"], r["dossier_sauvegarde"])
    return {"supprime": True, "env": env, "dossier_sauvegarde": r["dossier_sauvegarde"], "sauvegarde": str(tr.dossier),
            "avertissements": r["avertissements"]}
