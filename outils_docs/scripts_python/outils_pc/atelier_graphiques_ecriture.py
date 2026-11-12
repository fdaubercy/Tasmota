#!/usr/bin/env python3
"""Ecriture dans le depot pour l'atelier des graphiques (plan A6, spec §4.3, §7.2, §7.6).

Ce que l'atelier ecrit pour UNE carte (env du cenv, pas une base) :
  - `data/<lieu>/<carte>/pages_graphiques.json` : la description, validee par `atelier_graphiques_description.valide` ;
  - son `autoexec.be` : la ligne LIGNE_AUTOEXEC (toujours `demarrage.charge`, l'init du module pose le driver), juste
    apres `demarrage.historique()` s'il existe, sinon en fin du bloc `if demarrage.prologue()` ;
  - le cenv : les 7 fichiers du moteur (listes `pages_graphiques` et `pages_graphiques_moteur` de [berry_commun]) sont exclus du FS de TOUS les envs
    ESP32 (regle du 2026-10-31) sauf ceux qui ont une page. Une carte qui porte la ligne d'autoexec est « installee ».
Exclusion (`_exclut`) : `${berry_commun.pages_graphiques}` en fin de l'option custom_files_exclude qui donne la valeur de
l'env (la sienne, ou celle de sa base : ses cartes en heritent), creee dans l'env s'il n'en a aucune.
Levee pour la carte (`_leve`) : la ligne est retiree de l'option propre de l'env ; si l'env herite l'exclusion de sa base,
une option propre est posee, copie des valeurs de la base sans le moteur, precedee de MARQUE. Elle est figee : une
valeur ajoutee plus tard a la base ne la suit pas (c'est dit par MARQUE).
« Solidifier » : les 2 .be du moteur en fin du custom_berry_solidify de l'env (option creee -> MARQUE), seulement si
custom_files_exclude_solidified = ON (sinon les .be resteraient aussi sur le FS) ; signale « firmware a recompiler ».
Derniere page retiree (description None) : blocs MARQUE et lignes du solidify retires, ligne d'autoexec et description
retirees, puis `_exclut` : l'etat exclu est retrouve octet pour octet.
Apres chaque calcul, `_controle` relit le cenv obtenu : chaque carte installee embarque les 7 fichiers, tout autre env
les exclut tous ; sinon refus (option tenue par une reference `${env:...}`, fichiers listes a la main...).
Style `liquide` sur un env qui exclut echarts-liquidfill.min.js.gz (liste page_cuve) : refuse (palier 1).

Deux temps, comme fichiers_berry_ecriture : `prevoit` calcule sans rien ecrire ; `ecrit` refait le calcul et n'ecrit que
si l'empreinte (fichiers lus + demande) n'a pas change et si aucun build ne tourne, en une Transaction (atomique, copie
horodatee). Jamais data/fs/*.be ni un _persist.json. Apres ecriture : banc_demarrage.py a lancer, jamais --enregistre.

En ligne de commande (application au vrai depot, regle du 2026-10-31) :
    python atelier_graphiques_ecriture.py --exclusions [--ecrit]     # diff, puis ecriture avec --ecrit
"""

import difflib
import hashlib
import json
import sys
from pathlib import Path

import atelier_graphiques_description as agd
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi
import fichiers_berry_sauvegarde as fbs
from fichiers_berry_ecriture import LARGEUR_CLE, _indentation, _regions

LISTE = "pages_graphiques"                            # pagesGraphiques.be et la page : tout env sans page l'exclut
LISTE_MOTEUR = "pages_graphiques_moteur"              # moteur partage avec /graphiques : garde aussi par un env a historique
REF = "${berry_commun." + LISTE + "}"
REF_MOTEUR = "${berry_commun." + LISTE_MOTEUR + "}"
LISTES = ((LISTE, REF), (LISTE_MOTEUR, REF_MOTEUR))
PAGE_FICHIERS = ("data/fs/pagesGraphiques.be", "data/sd/html/pages_graphiques.html", "data/sd/css/pages_graphiques.css")
MOTEUR_FICHIERS = ("data/fs/pagesGraphiquesValidation.be", "data/sd/js/pages_graphiques_formule.js",
                   "data/sd/js/pages_graphiques.js", "data/sd/js/graphiques_moteur.js")
FICHIERS_MOTEUR = PAGE_FICHIERS + MOTEUR_FICHIERS
SOLIDES = ("data/fs/pagesGraphiques.be", "data/fs/pagesGraphiquesValidation.be")
NOMS_PAGE = {Path(f).name for f in PAGE_FICHIERS}    # le build exclut par nom de fichier (post_esp32.py)
NOMS_MOTEUR = {Path(f).name for f in MOTEUR_FICHIERS}
NOMS = NOMS_PAGE | NOMS_MOTEUR
LIQUIDFILL = "echarts-liquidfill.min.js.gz"
LIGNE_AUTOEXEC = 'demarrage.charge(["pagesGraphiques"])'
DESCRIPTION = "pages_graphiques.json"
MAX_FICHIER = 32768                                   # pagesGraphiques.MAX_FICHIER : au-dela la carte refuse
MARQUE = ("; atelier des graphiques : option posee pour les pages de graphiques de cet env (copie figee de la base"
          " pour l'exclusion), retiree avec la derniere page")
COMMENTAIRE_LISTE = (
    "; Pages de graphiques (atelier 7950, 2026-11-03) : la page et son module. SEULS les envs qui ont une page les embarquent ;",
    "; exclue de tous les autres envs (regle du 2026-10-31), levee env par env par atelier_graphiques_ecriture.py.")
COMMENTAIRE_MOTEUR = (
    "; Moteur de trace des pages de graphiques (2026-11-05), partage avec /graphiques : embarque par les envs a page ET par ceux",
    "; dont le _persist.json a diverses.historique.activation a ON ; exclu des autres (atelier_graphiques_ecriture.py).")


def _cle(option):
    return f"{option:<{LARGEUR_CLE}}= "


def _ini(racine, lignes):
    return fbi.lit_sections(racine, "\n".join(lignes))


def _noms(ini, env, option):
    return {Path(e.chemin).name for e in fbi.resout(ini, env, option)}


def _envs(ini):
    """Envs ESP32 du cenv (bases comprises), comme fichiers_berry_etat.envs_proposes."""
    return [e for e in ini.envs_cenv() if any(s.startswith("env:tasmota32") for s in ini.chaine(e))]


def historique(racine, env):
    """Vrai si le _persist.json de la carte a diverses.historique.activation a ON (une base n'en a pas)."""
    dossier = fbe.dossier_carte(env)
    try:
        h = json.loads((Path(racine) / dossier / "_persist.json").read_text(encoding="utf-8"))["diverses"]["historique"]
        return str(h.get("activation", "")).upper() == "ON"
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def _attendu(env, installes, histo):
    """Noms que l'env doit exclure : rien avec une page ; la page seule avec historique ; tout sinon."""
    if env in installes:
        return set()
    return NOMS_PAGE if env in histo else NOMS


def _historiques(racine, ini, lus):
    """Envs a historique ON ; les persists lus entrent dans `lus` (empreinte)."""
    res = set()
    for e in _envs(ini):
        if not fbe.est_base(e):
            rel = fbe.dossier_carte(e) + "/_persist.json"
            lus[rel] = _lit(racine, rel)
            if historique(racine, e):
                res.add(e)
    return res


def _fin_section(ini, lignes, section):
    """Index apres lequel inserer une option nouvelle : fin de la derniere option du cenv de la section, ou l'en-tete."""
    fins = [o.fin for o in ini.sections.get(section, {}).values() if o.fichier == fbi.FICHIER_CENV]
    return max(fins) if fins else _regions(lignes)[section][0]


def _ajoute(ini, lignes, env, option, valeurs, marque, texte=MARQUE):
    """`valeurs` en fin de l'option propre de l'env ; option heritee -> `${env:<ancetre>.option}` puis les valeurs ;
    absente partout -> creee. Une option creee est precedee de MARQUE si `marque`."""
    propre = ini.sections.get("env:" + env, {}).get(option)
    if propre is not None and propre.fichier == fbi.FICHIER_CENV:
        indent = _indentation(lignes, propre)
        return lignes[:propre.fin + 1] + [indent + v for v in valeurs] + lignes[propre.fin + 1:]
    ancetre = ini.definie_dans(env, option)
    tete = ["${" + ancetre + "." + option + "}"] if ancetre else []
    nouvelles = _option(option, tete + list(valeurs))
    i = _fin_section(ini, lignes, "env:" + env)
    return lignes[:i + 1] + ([texte] if marque else []) + nouvelles + lignes[i + 1:]


def _option(option, valeurs):
    indent = " " * len(_cle(option))
    if not valeurs:
        return [_cle(option).rstrip()]
    return [_cle(option) + valeurs[0]] + [indent + v for v in valeurs[1:]]


def _assure_liste(racine, lignes):
    for liste, fichiers, commentaire in ((LISTE, PAGE_FICHIERS, COMMENTAIRE_LISTE),
                                         (LISTE_MOTEUR, MOTEUR_FICHIERS, COMMENTAIRE_MOTEUR)):
        ini = _ini(racine, lignes)
        if "berry_commun" not in ini.sections:
            raise ValueError("section [berry_commun] absente du cenv")
        if liste in ini.sections["berry_commun"]:
            continue
        i = _fin_section(ini, lignes, "berry_commun")
        cle = f"{liste} =  "
        lignes = (lignes[:i + 1] + list(commentaire) + [cle + fichiers[0]] +
                  [" " * len(cle) + f for f in fichiers[1:]] + lignes[i + 1:])
    return lignes


def _exclut(racine, lignes, installes, histo=frozenset()):
    """REF / REF_MOTEUR ajoutes jusqu'a ce que tout env exclue au moins ce qu'il doit, puis levee de l'exclusion en trop
    (env a historique qui herite des deux de sa base). `installes` : envs avec page ; `histo` : envs a historique ON."""
    for _ in range(64):
        ini = _ini(racine, lignes)
        manque = next(((e, ref) for e in _envs(ini) for noms, ref in ((NOMS_PAGE, REF), (NOMS_MOTEUR, REF_MOTEUR))
                       if not noms & _attendu(e, installes, histo) <= _noms(ini, e, fbe.EXCLUDE)), None)
        if manque is None:
            break
        env, ref = manque
        definie = ini.definie_dans(env, fbe.EXCLUDE)
        opt = ini.sections[definie][fbe.EXCLUDE] if definie else None
        if opt is not None and opt.fichier == fbi.FICHIER_CENV and opt.section.startswith("env:"):  # la base porte la ligne pour ses cartes
            cible = opt.section[len("env:"):]
            if ref in [v for _, v, _ in opt.morceaux]:
                raise ValueError(f"{env} : {ref} deja dans {opt.section} mais le moteur n'est pas exclu")
        else:
            cible = env
        lignes = _ajoute(ini, lignes, cible, fbe.EXCLUDE, [ref], marque=False)
    else:
        raise ValueError("exclusion du moteur : le calcul ne converge pas")
    for env in [e for e in _envs(_ini(racine, lignes)) if not fbe.est_base(e)]:      # exclusion en trop, un env a la fois
        en_trop = _noms(_ini(racine, lignes), env, fbe.EXCLUDE) & NOMS - _attendu(env, installes, histo)
        refs = tuple(ref for noms, ref in ((NOMS_PAGE, REF), (NOMS_MOTEUR, REF_MOTEUR)) if noms & en_trop)
        if refs:
            lignes = _leve(racine, lignes, env, refs)
    return lignes


def _leve(racine, lignes, env, refs=(REF, REF_MOTEUR), marque=MARQUE):
    """Retire `refs` de l'exclusion de l'env (celles qu'elle ne porte pas sont refusees : a lever a la main)."""
    ini = _ini(racine, lignes)
    definie = ini.definie_dans(env, fbe.EXCLUDE)
    opt = ini.sections[definie][fbe.EXCLUDE] if definie else None
    valeurs = [v for _, v, _ in opt.morceaux] if opt else []
    for ref in refs:
        if opt is None or ref not in valeurs or opt.fichier != fbi.FICHIER_CENV:
            raise ValueError(f"{env} : {ref} introuvable dans son custom_files_exclude, exclusion a lever a la main")
    if definie == "env:" + env:
        retirees = {i for i, v, _ in opt.morceaux if v in refs}
        if opt.debut in retirees and len(opt.morceaux) > len(retirees):   # shortcut: une liste sur la ligne `option =` suivie d'autres valeurs : a la main
            raise ValueError(f"{env} : {', '.join(refs)} sur la ligne custom_files_exclude, exclusion a lever a la main")
        return [l for i, l in enumerate(lignes) if i not in retirees]     # option creee par _exclut : part avec sa seule liste
    reste = [v for v in valeurs if v not in refs]
    i = _fin_section(ini, lignes, "env:" + env)
    return lignes[:i + 1] + [marque] + _option(fbe.EXCLUDE, reste) + lignes[i + 1:]


def _solidifie(racine, lignes, env, solides=SOLIDES, marque=MARQUE):
    ini = _ini(racine, lignes)
    if not fbe._exclude_solidifies(ini, env):
        raise ValueError(f"{env} : custom_files_exclude_solidified n'est pas ON, le moteur solidifie resterait aussi "
                         "sur le FS : solidification refusee")
    deja = _noms(ini, env, fbe.SOLIDIFY)
    valeurs = [f for f in solides if Path(f).name not in deja]
    return _ajoute(ini, lignes, env, fbe.SOLIDIFY, valeurs, marque=True, texte=marque) if valeurs else lignes


def _retire(racine, lignes, env, solides=SOLIDES, marque=MARQUE):
    """Blocs MARQUE de l'env et lignes du moteur dans son solidify retires."""
    ini = _ini(racine, lignes)
    debut, fin = _regions(lignes)["env:" + env]
    propres = {o.nom: o for o in ini.sections.get("env:" + env, {}).values() if o.fichier == fbi.FICHIER_CENV}
    options = {o.debut: o for o in propres.values()}
    supprimees = set()
    for i in range(debut, fin):
        if lignes[i] == marque:                  # la marque puis l'option qu'elle annonce
            o = options.get(i + 1)
            supprimees |= set(range(i, (o.fin if o else i) + 1))
    solid = propres.get(fbe.SOLIDIFY)
    if solid is not None:
        supprimees |= {i for i, v, _ in solid.morceaux if v in solides and i != solid.debut}
    return [l for i, l in enumerate(lignes) if i not in supprimees]


def _controle(racine, lignes, installes, histo=frozenset()):
    ini = _ini(racine, lignes)
    for e in _envs(ini):
        noms, attendu = NOMS & _noms(ini, e, fbe.EXCLUDE), _attendu(e, installes, histo)
        if noms - attendu:
            raise ValueError(f"{e} : {', '.join(sorted(noms - attendu))} toujours exclu(s) : exclusion a lever a la main")
        if attendu - noms:
            raise ValueError(f"{e} : {', '.join(sorted(attendu - noms))} embarque(s) sans page ni historique : exclusion a revoir a la main")
    return ini


def _autoexec(texte, installe, ligne=LIGNE_AUTOEXEC):
    """Texte de l'autoexec avec (ou sans) ligne."""
    eol = "\r\n" if "\r\n" in texte else "\n"
    lignes = fbi.decoupe(texte)
    presente = [i for i, l in enumerate(lignes) if l.strip() == ligne]
    if not installe:
        return eol.join(l for i, l in enumerate(lignes) if i not in presente)
    if presente:
        return texte
    debut = next((i for i, l in enumerate(lignes) if l.rstrip() == "if demarrage.prologue()"), None)
    fin = next((i for i in range(debut + 1, len(lignes)) if lignes[i].rstrip() == "end"), None) if debut is not None else None
    if fin is None:
        raise ValueError("autoexec.be sans bloc `if demarrage.prologue()` ... `end` : ligne a poser a la main")
    histo = next((i for i in range(debut + 1, fin) if lignes[i].strip().startswith("demarrage.historique()")), None)
    modele = lignes[histo] if histo is not None else next((l for l in lignes[debut + 1:fin] if l.strip()), "    x")
    indent = modele[:len(modele) - len(modele.lstrip())]
    i = histo + 1 if histo is not None else fin
    return eol.join(lignes[:i] + [indent + ligne] + lignes[i:])


def _styles(desc):
    return {g.get("type") for p in desc.get("pages", []) for g in p.get("graphiques", [])} | \
           {e.get("type") for e in desc.get("encadres", [])}


def _lit(racine, rel):
    p = Path(racine) / rel
    return p.read_bytes() if p.is_file() else None


def _texte(octets):
    return None if octets is None else octets.decode("utf-8", errors="surrogateescape")


def _empreinte(lus, demande):
    h = hashlib.sha256(json.dumps(demande, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    for rel in sorted(lus):
        h.update(b"\0" + rel.encode("utf-8") + b"\0" + (hashlib.sha256(lus[rel]).digest() if lus[rel] is not None else b"-"))
    return h.hexdigest()


def _lit_cenv(racine):
    octets = (Path(racine) / fbi.FICHIER_CENV).read_bytes()
    texte = octets.decode("utf-8", errors="surrogateescape")
    return octets, ("\r\n" if "\r\n" in texte else "\n"), fbi.decoupe(texte)


def _installes(racine, ini, lus):
    res = set()
    for e in _envs(ini):
        if fbe.est_base(e):
            continue
        rel = fbe.dossier_carte(e) + "/autoexec.be"
        lus[rel] = _lit(racine, rel)
        if lus[rel] is not None and LIGNE_AUTOEXEC in [l.strip() for l in fbi.decoupe(_texte(lus[rel]))]:
            res.add(e)
    return res


def _calcule(racine, env, description, solidifier):
    """(lus {rel: octets|None}, apres {rel: octets|None} des fichiers qui changent, signaux)."""
    racine = Path(racine)
    octets, eol, lignes = _lit_cenv(racine)
    lus = {fbi.FICHIER_CENV: octets}
    ini = fbi.lit_sections(racine)
    if env not in _envs(ini) or fbe.est_base(env):
        raise LookupError(f"env inconnu, non ESP32 ou de base : {env!r}")
    installe = description is not None
    if installe:
        motifs = agd.valide(description)
        if motifs:
            raise ValueError("description invalide : " + " ; ".join(motifs))
    installes = _installes(racine, ini, lus)
    dossier = fbe.dossier_carte(env)
    rel_auto, rel_desc = dossier + "/autoexec.be", dossier + "/" + DESCRIPTION
    lus[rel_desc] = _lit(racine, rel_desc)
    if lus[rel_auto] is None:
        raise ValueError(f"{rel_auto} absent : rien n'est ecrit")
    deja, solide = env in installes, {Path(f).name for f in SOLIDES} <= _noms(ini, env, fbe.SOLIDIFY)
    apres_lignes = lignes
    apres_installes = (installes - {env}) | ({env} if installe else set())
    histo = _historiques(racine, ini, lus)
    if not (installe and deja and bool(solidifier) == solide):          # sinon : la description seule
        apres_lignes = _assure_liste(racine, lignes)
        if deja:
            apres_lignes = _retire(racine, apres_lignes, env)
        apres_lignes = _exclut(racine, apres_lignes, apres_installes, histo)
        if installe and solidifier:
            apres_lignes = _solidifie(racine, apres_lignes, env)
    final = _controle(racine, apres_lignes, apres_installes, histo)
    if installe and "liquide" in _styles(description) and LIQUIDFILL in _noms(final, env, fbe.EXCLUDE):
        raise ValueError(f"style liquide refuse sur {env} : {LIQUIDFILL} est exclu de son FS (liste page_cuve)")
    apres = {}
    if apres_lignes != lignes:
        apres[fbi.FICHIER_CENV] = eol.join(apres_lignes).encode("utf-8", errors="surrogateescape")
    auto = _autoexec(_texte(lus[rel_auto]), installe).encode("utf-8", errors="surrogateescape")
    if auto != lus[rel_auto]:
        apres[rel_auto] = auto
    desc = None
    if installe:
        desc = (json.dumps(description, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
        if len(desc) > MAX_FICHIER:
            desc = json.dumps(description, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if desc != lus[rel_desc]:
        apres[rel_desc] = desc
    signaux = []
    if _noms(final, env, fbe.SOLIDIFY) != _noms(ini, env, fbe.SOLIDIFY):
        signaux.append("firmware a recompiler (custom_berry_solidify change)")
    if fbi.FICHIER_CENV in apres or rel_auto in apres:
        signaux.append("banc_demarrage.py a lancer (jamais --enregistre automatique)")
    if apres:
        signaux.append("FS de la carte a reconstruire et televerser")
    return lus, apres, signaux


def _fichiers(lus, apres):
    return [{"chemin": rel, "avant": _texte(lus.get(rel)), "apres": _texte(apres[rel])} for rel in sorted(apres)]


def prevoit(racine, env, description, solidifier):
    """{"fichiers": [{"chemin", "avant", "apres"}] (None = absent), "empreinte", "signaux"} sans rien ecrire.
    description None = derniere page retiree. ValueError / LookupError : refus, avec le motif."""
    lus, apres, signaux = _calcule(racine, env, description, solidifier)
    return {"fichiers": _fichiers(lus, apres), "signaux": signaux,
            "empreinte": _empreinte(lus, [env, description, bool(solidifier)])}


def _ecrit_transaction(racine, apres, nature):
    with fbs.Transaction(racine, nature) as tr:
        for rel in sorted(apres):
            if apres[rel] is None:
                tr.supprime(rel)
            else:
                tr.ecrit(rel, apres[rel])
    return sorted(apres)


def _refuse_build(builds_en_cours):
    builds = builds_en_cours()
    if builds is None:
        raise RuntimeError("impossible de savoir si un build tourne : ecriture refusee")
    if builds:
        raise RuntimeError("un build est en cours (" + ", ".join(builds) + ") : ecriture refusee")


def ecrit(racine, env, description, solidifier, empreinte_lue, builds_en_cours):
    """Chemins ecrits (relatifs a la racine). RuntimeError : build en cours ou indetectable, fichiers ou demande changes
    depuis `prevoit` (rien n'est ecrit)."""
    _refuse_build(builds_en_cours)
    lus, apres, _ = _calcule(racine, env, description, solidifier)
    if _empreinte(lus, [env, description, bool(solidifier)]) != empreinte_lue:
        raise RuntimeError("cenv, autoexec ou description modifies depuis le diff : refaire le diff, rien n'est ecrit")
    return _ecrit_transaction(racine, apres, "atelier-graphiques") if apres else []


def _calcule_exclusions(racine):
    octets, eol, lignes = _lit_cenv(racine)
    lus = {fbi.FICHIER_CENV: octets}
    ini = fbi.lit_sections(racine)
    installes = _installes(racine, ini, lus)
    histo = _historiques(racine, ini, lus)
    apres_lignes = _exclut(racine, _assure_liste(racine, lignes), installes, histo)
    _controle(racine, apres_lignes, installes, histo)
    apres = {fbi.FICHIER_CENV: eol.join(apres_lignes).encode("utf-8", errors="surrogateescape")} if apres_lignes != lignes else {}
    return lus, apres


def prevoit_exclusions(racine):
    """Liste `pages_graphiques` dans [berry_commun] et moteur exclu de tout env sans page : {"fichiers", "empreinte"}."""
    lus, apres = _calcule_exclusions(racine)
    return {"fichiers": _fichiers(lus, apres), "empreinte": _empreinte(lus, ["exclusions"])}


def ecrit_exclusions(racine, empreinte_lue, builds_en_cours):
    _refuse_build(builds_en_cours)
    lus, apres = _calcule_exclusions(racine)
    if _empreinte(lus, ["exclusions"]) != empreinte_lue:
        raise RuntimeError("cenv ou autoexec modifies depuis le diff : rien n'est ecrit")
    return _ecrit_transaction(racine, apres, "atelier-exclusions") if apres else []


if __name__ == "__main__":
    racine = Path(__file__).resolve().parents[3]
    if "--exclusions" not in sys.argv:
        sys.exit(__doc__)
    p = prevoit_exclusions(racine)
    for f in p["fichiers"]:
        sys.stdout.writelines(l + "\n" for l in difflib.unified_diff(
            f["avant"].splitlines(), f["apres"].splitlines(), f["chemin"], f["chemin"], lineterm="", n=1))
    if not p["fichiers"]:
        print("rien a faire : le moteur est deja exclu de tous les envs sans page")
    elif "--ecrit" in sys.argv:
        import build_serie
        print("ecrits :", ecrit_exclusions(racine, p["empreinte"], build_serie.builds_en_cours_defaut))
