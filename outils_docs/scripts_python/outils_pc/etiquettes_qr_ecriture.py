"""Ecriture dans le depot pour les etiquettes QR code (plan etiquettes-qrcode A3, spec §7.1, §7.6, §7.9).

Pour UNE carte (env du cenv, famille « cartes ») :
  - `outils_docs/etiquettes_qr/cartes/<env>.json` : la SURCHARGE, c.-a-d. ce qui differe du gabarit commun (retiree si vide) ;
  - avec « Page sur la carte » (ESP32 seulement) : `data/<lieu>/<carte>/qrcode.json` (texte resolu, style, image), la ligne
    LIGNE_AUTOEXEC dans son `autoexec.be`, et le cenv : liste `etiquette_qr` de [berry_commun] levee pour l'env, exclue de tous
    les autres envs ESP32 (regle du 2026-10-31), `qrcodePage.be` dans son custom_berry_solidify si l'env a
    custom_files_exclude_solidified a ON (sinon le module reste sur le FS, signale). Page decochee : tout cela retire.
Refus tant que les fichiers de la page de carte (A6, FICHIERS_PAGE) ne sont pas dans le depot : la ligne d'autoexec chargerait
un module absent et la carte planterait au demarrage.

Mecanique du cenv reprise de `atelier_graphiques_ecriture` (ses fonctions generiques, la marque et la ligne d'autoexec passees en
parametre) ; une carte est « installee » si son autoexec porte LIGNE_AUTOEXEC. Deux temps : `prevoit` sans rien ecrire, `ecrit`
qui refait le calcul et n'ecrit que si l'empreinte (fichiers lus, demande, texte resolu) n'a pas change et qu'aucun build ne
tourne, en une Transaction. Jamais data/fs/*.be, un _persist.json ni le .h.

shortcut: un env qui a a la fois une page de l'atelier des graphiques et la page /qrcode peut porter une option
custom_files_exclude posee par l'un et completee par l'autre ; retirer l'une des pages retire alors le bloc entier de sa marque.
`_controle` (des deux modules) le detecte au calcul suivant et refuse : a reprendre a la main si le cas se presente.

`impressions.json` (hors de tout dossier de carte : imprimer ne touche pas le FS) garde par env l'empreinte du texte imprime,
la date et la taille ; jamais le texte.
"""

import datetime
import json
import os
from pathlib import Path

import atelier_graphiques_ecriture as age
import build_envs
import etiquettes_qr_modele as modele
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi

LISTE = "etiquette_qr"
REF = "${berry_commun." + LISTE + "}"
FICHIERS_PAGE = ("data/fs/qrcodePage.be", "data/sd/html/qrcode.html", "data/sd/css/qrcode.css", "data/sd/js/qrcode.js",
                 "data/sd/js/qr-code-styling.min.js.gz")
SOLIDES = ("data/fs/qrcodePage.be",)
NOMS = {Path(f).name for f in FICHIERS_PAGE}
LIGNE_AUTOEXEC = 'demarrage.charge(["qrcodePage"])'
FICHIER_CARTE = "qrcode.json"
IMPRESSIONS = modele.DOSSIER / "impressions.json"
MARQUE = ("; etiquettes QR : option posee pour la page /qrcode de cet env (copie figee de la base pour l'exclusion),"
          " retiree avec la page")
COMMENTAIRE_LISTE = (
    "; Page /qrcode des etiquettes QR (page 7970, 2026-11-12) : module et page. SEULS les envs qui l'affichent les embarquent ;",
    "; exclue de tous les autres envs (regle du 2026-10-31), levee env par env par etiquettes_qr_ecriture.py.")


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
                raise ValueError(f"{env} : {REF} deja dans {opt.section} mais la page n'est pas exclue")
        else:
            cible = env
        lignes = age._ajoute(ini, lignes, cible, fbe.EXCLUDE, [REF], marque=False)
    else:
        raise ValueError("exclusion de la page /qrcode : le calcul ne converge pas")
    for env in [e for e in age._envs(age._ini(racine, lignes)) if not fbe.est_base(e)]:
        if age._noms(age._ini(racine, lignes), env, fbe.EXCLUDE) & NOMS - _attendu(env, installes):
            lignes = age._leve(racine, lignes, env, (REF,), marque=MARQUE)
    return lignes


def _controle(racine, lignes, installes):
    ini = age._ini(racine, lignes)
    for e in age._envs(ini):
        noms, attendu = NOMS & age._noms(ini, e, fbe.EXCLUDE), _attendu(e, installes)
        if noms != attendu:
            raise ValueError(f"{e} : page /qrcode {'exclue' if noms - attendu else 'embarquee'} a tort, exclusion a revoir a la main")
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


def surcharge(gabarit, reglage):
    """Ce qui differe du gabarit : cles de premier niveau, et `style` cle par cle ; fusionne(gabarit, surcharge) == reglage."""
    s = {k: v for k, v in reglage.items() if k != "style" and gabarit.get(k) != v}
    style = {k: v for k, v in (reglage.get("style") or {}).items() if (gabarit.get("style") or {}).get(k) != v}
    return {**s, **({"style": style} if style else {})}


def _json(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def _carte(racine, env):
    e = next((x for x in build_envs.liste_envs(racine) if x.nom == env), None)
    if e is None or e.famille != "cartes":
        raise LookupError(f"carte inconnue : {env!r}")
    return e


def _calcule(racine, env, reglage, page_carte):
    """(lus {rel: octets|None}, apres {rel: octets|None} des fichiers qui changent, signaux, texte resolu)."""
    racine = Path(racine)
    modele._env_valide(env)
    erreurs = modele.valide_reglage(reglage, racine)
    if erreurs:
        raise ValueError("réglage invalide : " + " ; ".join(erreurs))
    esp32 = env in age._envs(fbi.lit_sections(racine))
    if page_carte and not esp32:
        raise ValueError(f"{env} : pas de page /qrcode sur une carte sans Berry (ESP8266), étiquette papier seulement")
    if page_carte and not all((racine / f).is_file() for f in FICHIERS_PAGE):
        raise ValueError("page /qrcode pas encore disponible dans le dépôt (plan A6) : décocher « Page sur la carte »")
    resolu = modele.resout_avec(reglage, modele.champs_standards(racine, env, [_carte(racine, env)]), modele.persist_de(racine, env))
    rel_sur = (modele.DOSSIER / "cartes" / f"{env}.json").as_posix()
    lus, apres, signaux = {rel_sur: age._lit(racine, rel_sur)}, {}, []
    sur = surcharge(modele.charge_gabarit(racine), reglage)
    nouveau = _json(sur) if sur else None
    if nouveau != lus[rel_sur]:
        apres[rel_sur] = nouveau
    if not esp32:
        return lus, apres, signaux, resolu["texte"]
    octets, eol, lignes = age._lit_cenv(racine)
    lus[fbi.FICHIER_CENV] = octets
    ini = fbi.lit_sections(racine)
    installes = _installes(racine, ini, lus)
    dossier = fbe.dossier_carte(env)
    rel_auto, rel_qr = dossier + "/autoexec.be", dossier + "/" + FICHIER_CARTE
    lus[rel_qr] = age._lit(racine, rel_qr)
    deja = env in installes
    if page_carte or deja:
        if lus[rel_auto] is None:
            raise ValueError(f"{rel_auto} absent : rien n'est écrit")
        apres_installes = (installes - {env}) | ({env} if page_carte else set())
        apres_lignes = lignes
        if page_carte != deja:
            apres_lignes = _assure_liste(racine, lignes)
            if deja:
                apres_lignes = age._retire(racine, apres_lignes, env, solides=SOLIDES, marque=MARQUE)
            apres_lignes = _exclut(racine, apres_lignes, apres_installes)
            if page_carte:
                if fbe._exclude_solidifies(age._ini(racine, apres_lignes), env):
                    apres_lignes = age._solidifie(racine, apres_lignes, env, solides=SOLIDES, marque=MARQUE)
                else:
                    signaux.append("qrcodePage.be reste sur le FS (custom_files_exclude_solidified n'est pas ON) : non solidifié")
        final = _controle(racine, apres_lignes, apres_installes)
        if apres_lignes != lignes:
            apres[fbi.FICHIER_CENV] = eol.join(apres_lignes).encode("utf-8", errors="surrogateescape")
        auto = age._autoexec(age._texte(lus[rel_auto]), page_carte, ligne=LIGNE_AUTOEXEC).encode("utf-8", errors="surrogateescape")
        if auto != lus[rel_auto]:
            apres[rel_auto] = auto
        if age._noms(final, env, fbe.SOLIDIFY) != age._noms(ini, env, fbe.SOLIDIFY):
            signaux.append("firmware à recompiler par la page Build (custom_berry_solidify change)")
        if fbi.FICHIER_CENV in apres or rel_auto in apres:
            signaux.append("banc_demarrage.py à lancer (jamais --enregistre automatique)")
    qr = _json(modele.fichier_carte(racine, reglage, resolu)) if page_carte else None
    if qr != lus[rel_qr]:
        apres[rel_qr] = qr
    if rel_qr in apres or rel_auto in apres:
        signaux.append("FS de la carte à reconstruire et téléverser")
    return lus, apres, signaux, resolu["texte"]


def prevoit(racine, env, reglage, page_carte):
    """{"fichiers": [{"chemin", "avant", "apres"}] (None = absent), "empreinte", "signaux"} sans rien ecrire.
    ValueError / LookupError : refus, avec le motif."""
    lus, apres, signaux, texte = _calcule(racine, env, reglage, page_carte)
    return {"fichiers": age._fichiers(lus, apres), "signaux": signaux,
            "empreinte": age._empreinte(lus, [env, reglage, bool(page_carte), texte])}


def ecrit(racine, env, reglage, page_carte, empreinte_lue, builds_en_cours):
    """Chemins ecrits. RuntimeError : build en cours ou indetectable, depot ou demande changes depuis `prevoit`."""
    age._refuse_build(builds_en_cours)
    lus, apres, _, texte = _calcule(racine, env, reglage, page_carte)
    if age._empreinte(lus, [env, reglage, bool(page_carte), texte]) != empreinte_lue:
        raise RuntimeError("dépôt ou réglage modifiés depuis le diff : refaire le diff, rien n'est écrit")
    for rel, octets in apres.items():             # la Transaction ne cree pas les dossiers (cartes/ au premier reglage)
        if octets is not None:
            (Path(racine) / rel).parent.mkdir(parents=True, exist_ok=True)
    return age._ecrit_transaction(racine, apres, "etiquettes-qr") if apres else []


def _calcule_gabarit(racine, gabarit):
    erreurs = modele.valide_reglage(gabarit, racine)
    if erreurs:
        raise ValueError("gabarit invalide : " + " ; ".join(erreurs))
    rel = modele.GABARIT.as_posix()
    lus = {rel: age._lit(racine, rel)}
    nouveau = _json(gabarit)
    return lus, ({rel: nouveau} if nouveau != lus[rel] else {})


def prevoit_gabarit(racine, gabarit):
    lus, apres = _calcule_gabarit(racine, gabarit)
    return {"fichiers": age._fichiers(lus, apres), "empreinte": age._empreinte(lus, ["gabarit", gabarit])}


def ecrit_gabarit(racine, gabarit, empreinte_lue, builds_en_cours):
    age._refuse_build(builds_en_cours)
    lus, apres = _calcule_gabarit(racine, gabarit)
    if age._empreinte(lus, ["gabarit", gabarit]) != empreinte_lue:
        raise RuntimeError("gabarit modifié depuis le diff : refaire le diff, rien n'est écrit")
    return age._ecrit_transaction(racine, apres, "etiquettes-qr-gabarit") if apres else []


def _calcule_exclusions(racine):
    octets, eol, lignes = age._lit_cenv(racine)
    lus = {fbi.FICHIER_CENV: octets}
    installes = _installes(racine, fbi.lit_sections(racine), lus)
    apres_lignes = _exclut(racine, _assure_liste(racine, lignes), installes)
    _controle(racine, apres_lignes, installes)
    apres = {fbi.FICHIER_CENV: eol.join(apres_lignes).encode("utf-8", errors="surrogateescape")} if apres_lignes != lignes else {}
    return lus, apres


def prevoit_exclusions(racine):
    """Liste `etiquette_qr` dans [berry_commun] et page exclue de tout env qui ne l'affiche pas (A6) : {"fichiers", "empreinte"}."""
    lus, apres = _calcule_exclusions(racine)
    return {"fichiers": age._fichiers(lus, apres), "empreinte": age._empreinte(lus, ["exclusions"])}


def ecrit_exclusions(racine, empreinte_lue, builds_en_cours):
    age._refuse_build(builds_en_cours)
    lus, apres = _calcule_exclusions(racine)
    if age._empreinte(lus, ["exclusions"]) != empreinte_lue:
        raise RuntimeError("cenv ou autoexec modifiés depuis le diff : rien n'est écrit")
    return age._ecrit_transaction(racine, apres, "etiquettes-qr-exclusions") if apres else []


# --- impressions ------------------------------------------------------------------------------------------------------

def lit_impressions(racine):
    try:
        d = json.loads((Path(racine) / IMPRESSIONS).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _ecrit_impressions(racine, d):
    chemin = Path(racine) / IMPRESSIONS
    tmp = chemin.with_suffix(".tmp")
    tmp.write_bytes(_json(dict(sorted(d.items()))))
    os.replace(tmp, chemin)                        # atomique : jamais de fichier a moitie ecrit


def note_impression(racine, textes, taille_mm):
    """`textes` : {env: texte imprime}. Garde l'empreinte, la date et la taille, jamais le texte.
    Rend les notes remplacees {env: note precedente | None}, pour qu'une annulation les remette."""
    d = lit_impressions(racine)
    date = datetime.datetime.now().isoformat(timespec="seconds")
    avant = {}
    for env, texte in textes.items():
        env = modele._env_valide(env)
        avant[env] = d.get(env)
        d[env] = {"empreinte": modele.empreinte(texte), "date": date, "taille_mm": taille_mm}
    _ecrit_impressions(racine, d)
    return avant


def annule_impression(racine, env, precedente=None):
    """Retire la note de `env`, ou remet `precedente` (rendue par note_impression) si la carte avait deja ete imprimee."""
    d = lit_impressions(racine)
    env = modele._env_valide(env)
    if precedente is not None:
        d[env] = precedente
    elif d.pop(env, None) is None:
        return
    _ecrit_impressions(racine, d)
