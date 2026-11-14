"""Ecriture dans le depot pour l'atelier des visuels d'accueil (plan atelier-visuels A7, spec §6.1, §6.5).

Pour UNE carte ESP32 (env du cenv, famille « cartes ») :
  - `data/<lieu>/<carte>/visuel.json` : la description, validee par `atelier_visuels_description.valide` ;
  - le fond `visuel.svg|webp|jpg` (un seul : les autres types sont retires ; un fond different du depot apparait dans le diff) ;
  - `autoexec.be` : la ligne LIGNE_AUTOEXEC EN DERNIER du bloc `if demarrage.prologue()` (le visuel vient sous la facade) ;
  - le cenv : liste `visuel_accueil` de [berry_commun] (creee si absente), exclue de tous les envs ESP32 sauf ceux qui portent
    la ligne, et ses deux .be dans custom_berry_solidify si custom_files_exclude_solidified vaut ON (sinon signale).
`retire` fait l'inverse. Refus : empreinte perimee, build en cours, fichiers de la page absents du depot (la ligne d'autoexec
chargerait un module absent), description ou fond refuses. Jamais data/fs/*.be, un _persist.json ni le .h.
Mecanique du cenv reprise de `etiquettes_qr_ecriture` (fonctions generiques de `atelier_graphiques_ecriture`).
fond None = garder le fond deja au depot du type demande (refus s'il n'y en a pas).
"""

import hashlib
import json
from pathlib import Path

import atelier_graphiques_ecriture as age
import atelier_visuels_description as avd
import atelier_visuels_fond as avf
import build_envs
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi
import lieux

LISTE = "visuel_accueil"
REF = "${berry_commun." + LISTE + "}"
FICHIERS_PAGE = ("data/fs/visuelFonctions.be", "data/fs/controleVisuel.be", "data/sd/js/visuel.js")
SOLIDES = FICHIERS_PAGE[:2]
NOMS = {Path(f).name for f in FICHIERS_PAGE}
LIGNE_AUTOEXEC = 'demarrage.charge(["controleVisuel"])'
FICHIER_CARTE = "visuel.json"
TYPES_FOND = ("svg", "webp", "jpg")
MARQUE = ("; atelier des visuels : option posee pour le visuel d'accueil de cet env (copie figee de la base pour l'exclusion),"
          " retiree avec le visuel")
COMMENTAIRE_LISTE = (
    "; Visuel d'accueil (atelier 7985, 2026-11-13) : modules et moteur de dessin. SEULS les envs qui ont un visuel les embarquent ;",
    "; exclue de tous les autres envs (regle du 2026-10-31), levee env par env par atelier_visuels_ecriture.py.")


def _attendu(env, installes):
    return set() if env in installes else NOMS


def _assure_liste(racine, lignes):
    ini = age._ini(racine, lignes)
    if "berry_commun" not in ini.sections:
        raise ValueError("section [berry_commun] absente du cenv")
    if LISTE in ini.sections["berry_commun"]:
        return lignes
    i = age._fin_section(ini, lignes, "berry_commun")
    cle = f"{LISTE} =  "
    return (lignes[:i + 1] + list(COMMENTAIRE_LISTE) + [cle + FICHIERS_PAGE[0]] +
            [" " * len(cle) + f for f in FICHIERS_PAGE[1:]] + lignes[i + 1:])


def _exclut(racine, lignes, installes):
    """REF ajoutee jusqu'a ce que tout env ESP32 exclue la page sauf les installes, puis levee pour ceux-ci."""
    for _ in range(64):
        ini = age._ini(racine, lignes)
        env = next((e for e in age._envs(ini) if not _attendu(e, installes) <= age._noms(ini, e, fbe.EXCLUDE)), None)
        if env is None:
            break
        definie = ini.definie_dans(env, fbe.EXCLUDE)
        opt = ini.sections[definie][fbe.EXCLUDE] if definie else None
        if opt is not None and opt.fichier == fbi.FICHIER_CENV and opt.section.startswith("env:"):
            cible = opt.section[len("env:"):]
            if REF in [v for _, v, _ in opt.morceaux]:
                raise ValueError(f"{env} : {REF} deja dans {opt.section} mais le visuel n'est pas exclu")
        else:
            cible = env
        lignes = age._ajoute(ini, lignes, cible, fbe.EXCLUDE, [REF], marque=False)
    else:
        raise ValueError("exclusion du visuel : le calcul ne converge pas")
    for env in [e for e in age._envs(age._ini(racine, lignes)) if not fbe.est_base(e)]:
        if age._noms(age._ini(racine, lignes), env, fbe.EXCLUDE) & NOMS - _attendu(env, installes):
            lignes = age._leve(racine, lignes, env, (REF,), marque=MARQUE)
    return lignes


def _controle(racine, lignes, installes):
    ini = age._ini(racine, lignes)
    for e in age._envs(ini):
        noms, attendu = NOMS & age._noms(ini, e, fbe.EXCLUDE), _attendu(e, installes)
        if noms != attendu:
            raise ValueError(f"{e} : visuel {'exclu' if noms - attendu else 'embarque'} a tort, exclusion a revoir a la main")
    return ini


def _installes(racine, ini, lus):
    res = set()
    for e in age._envs(ini):
        if not fbe.est_base(e):
            rel = fbe.dossier_carte(e) + "/autoexec.be"
            lus[rel] = age._lit(racine, rel)
            if lus[rel] is not None and LIGNE_AUTOEXEC in [l.strip() for l in fbi.decoupe(age._texte(lus[rel]))]:
                res.add(e)
    return res


def _autoexec(texte, installe):
    """Texte de l'autoexec avec la ligne EN DERNIER du bloc `if demarrage.prologue()` (sans elle si `installe` est faux)."""
    eol = "\r\n" if "\r\n" in texte else "\n"
    lignes = fbi.decoupe(texte)
    presente = [i for i, l in enumerate(lignes) if l.strip() == LIGNE_AUTOEXEC]
    if not installe:
        return eol.join(l for i, l in enumerate(lignes) if i not in presente)
    if presente:
        return texte
    debut = next((i for i, l in enumerate(lignes) if l.rstrip() == "if demarrage.prologue()"), None)
    fin = next((i for i in range(debut + 1, len(lignes)) if lignes[i].rstrip() == "end"), None) if debut is not None else None
    if fin is None:
        raise ValueError("autoexec.be sans bloc `if demarrage.prologue()` ... `end` : ligne a poser a la main")
    modele = next((l for l in reversed(lignes[debut + 1:fin]) if l.strip()), "    x")
    return eol.join(lignes[:fin] + [modele[:len(modele) - len(modele.lstrip())] + LIGNE_AUTOEXEC] + lignes[fin:])


def _carte(racine, env):
    e = next((x for x in build_envs.liste_envs(racine) if x.nom == env), None)
    if e is None or e.famille != "cartes":
        raise LookupError(f"carte inconnue : {env!r}")
    return e


def _json(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def _nouveaux(description, fond, type_fond, env, lus, rel_fonds, rel_auto, rel_json):
    """({rel: octets|None} voulus pour visuel.json et les fonds, avertissements) ; ValueError = refus."""
    if type_fond not in TYPES_FOND:
        raise ValueError(f"type de fond inconnu : {type_fond!r}")
    if lus[rel_auto] is None:
        raise ValueError(f"{rel_auto} absent : rien n'est écrit")
    declare = (description.get("fond") or {}).get("type") if isinstance(description, dict) else None
    if declare != type_fond:
        raise ValueError(f"fond.type de la description ({declare!r}) différent du fond envoyé ({type_fond!r})")
    puce, avert = lieux.puce(env), []
    if fond is None:
        fond = lus[rel_fonds[type_fond]]
        if fond is None:
            raise ValueError(f"aucun fond {type_fond} au dépôt pour {env} : en envoyer un")
    else:
        message = avf.controle_fond(type_fond, fond, puce)
        if avf.refuse(fond, puce):
            raise ValueError(message)
        if message:
            avert.append(message)
    erreurs = avd.valide(description, len(fond), puce)
    if erreurs:
        raise ValueError("description invalide : " + " ; ".join(erreurs))
    voulus = {rel_json: _json(description), rel_fonds[type_fond]: fond}
    voulus.update({r: None for t, r in rel_fonds.items() if t != type_fond})
    return voulus, avert


def _calcule(racine, env, description, fond, type_fond):
    """(lus {rel: octets|None}, apres {rel: octets|None} des fichiers qui changent, signaux, avertissements).
    description None = visuel retire."""
    racine = Path(racine)
    _carte(racine, env)
    installe = description is not None
    if env not in age._envs(fbi.lit_sections(racine)):
        raise ValueError(f"{env} : pas de visuel sur une carte sans Berry (ESP8266)")
    if installe and not all((racine / f).is_file() for f in FICHIERS_PAGE):
        raise ValueError("fichiers du visuel pas encore disponibles dans le dépôt (plan A3 et A4) : rien n'est écrit")
    dossier = fbe.dossier_carte(env)
    rel_auto, rel_json = dossier + "/autoexec.be", dossier + "/" + FICHIER_CARTE
    rel_fonds = {t: f"{dossier}/visuel.{t}" for t in TYPES_FOND}
    octets, eol, lignes = age._lit_cenv(racine)
    lus = {fbi.FICHIER_CENV: octets, rel_json: age._lit(racine, rel_json), **{r: age._lit(racine, r) for r in rel_fonds.values()}}
    ini = fbi.lit_sections(racine)
    installes = _installes(racine, ini, lus)
    deja = env in installes
    signaux = []
    if installe:
        voulus, avert = _nouveaux(description, fond, type_fond, env, lus, rel_fonds, rel_auto, rel_json)
    else:
        voulus, avert = {rel_json: None, **{r: None for r in rel_fonds.values()}}, []
    apres = {rel: neuf for rel, neuf in voulus.items() if neuf != lus[rel]}
    if installe or deja:
        apres_installes = (installes - {env}) | ({env} if installe else set())
        apres_lignes = _assure_liste(racine, lignes)
        if deja and not installe:
            apres_lignes = age._retire(racine, apres_lignes, env, solides=SOLIDES, marque=MARQUE)
        apres_lignes = _exclut(racine, apres_lignes, apres_installes)
        if installe and not deja:
            if fbe._exclude_solidifies(age._ini(racine, apres_lignes), env):
                apres_lignes = age._solidifie(racine, apres_lignes, env, solides=SOLIDES, marque=MARQUE)
            else:
                signaux.append("visuelFonctions.be et controleVisuel.be restent sur le FS "
                               "(custom_files_exclude_solidified n'est pas ON) : non solidifiés")
        final = _controle(racine, apres_lignes, apres_installes)
        if apres_lignes != lignes:
            apres[fbi.FICHIER_CENV] = eol.join(apres_lignes).encode("utf-8", errors="surrogateescape")
        if lus[rel_auto] is not None:
            auto = _autoexec(age._texte(lus[rel_auto]), installe).encode("utf-8", errors="surrogateescape")
            if auto != lus[rel_auto]:
                apres[rel_auto] = auto
        if age._noms(final, env, fbe.SOLIDIFY) != age._noms(ini, env, fbe.SOLIDIFY):
            signaux.append("firmware à recompiler par la page Build (custom_berry_solidify change)")
        if fbi.FICHIER_CENV in apres or rel_auto in apres:
            signaux.append("banc_demarrage.py à lancer (jamais --enregistre automatique)")
    if apres:
        signaux.append("FS de la carte à reconstruire et téléverser")
    return lus, apres, signaux, avert


def _resume(octets):
    return None if octets is None else f"{len(octets)} octets, sha256 {hashlib.sha256(octets).hexdigest()[:12]}"


def _diff(lus, apres):
    """Comme age._fichiers, mais un fond binaire est resume (taille, empreinte) au lieu d'un texte illisible."""
    res = age._fichiers(lus, apres)
    for f in res:
        if f["chemin"].endswith((".webp", ".jpg")):
            f["avant"], f["apres"] = _resume(lus.get(f["chemin"])), _resume(apres[f["chemin"]])
    return res


def _demande(env, description, fond, type_fond):
    return [env, description, type_fond, hashlib.sha256(fond).hexdigest() if fond is not None else None]


def _prevoit(racine, env, description, fond, type_fond):
    lus, apres, signaux, avert = _calcule(racine, env, description, fond, type_fond)
    return {"diff": _diff(lus, apres), "empreinte": age._empreinte(lus, _demande(env, description, fond, type_fond)),
            "avertissements": avert + signaux}


def _applique(racine, env, description, fond, type_fond, empreinte_lue, builds_en_cours, nature):
    age._refuse_build(builds_en_cours)
    lus, apres, _, _ = _calcule(racine, env, description, fond, type_fond)
    if age._empreinte(lus, _demande(env, description, fond, type_fond)) != empreinte_lue:
        raise RuntimeError("dépôt ou visuel modifiés depuis le diff : refaire le diff, rien n'est écrit")
    return age._ecrit_transaction(racine, apres, nature) if apres else []


def prevoit(racine, env, description, fond, type_fond):
    """{"diff": [{"chemin", "avant", "apres"}] (None = absent), "empreinte", "avertissements"} sans rien ecrire.
    ValueError / LookupError : refus, avec le motif."""
    return _prevoit(racine, env, description, fond, type_fond)


def ecrit(racine, env, description, fond, type_fond, empreinte_lue, builds_en_cours):
    """Chemins ecrits. RuntimeError : build en cours ou indetectable, depot ou demande changes depuis `prevoit`."""
    return _applique(racine, env, description, fond, type_fond, empreinte_lue, builds_en_cours, "atelier-visuels")


def prevoit_retire(racine, env):
    """Meme forme que `prevoit`, pour le visuel decoche."""
    return _prevoit(racine, env, None, None, None)


def retire(racine, env, empreinte_lue, builds_en_cours):
    """Visuel decoche : fichiers, ligne d'autoexec et cenv retires. `empreinte_lue` vient de `prevoit_retire`."""
    return _applique(racine, env, None, None, None, empreinte_lue, builds_en_cours, "atelier-visuels-retire")
