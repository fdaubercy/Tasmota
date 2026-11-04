#!/usr/bin/env python3
"""Banque de commandes de l'onglet « autoexec.bat » (plan autoexec-bat, A4) : commandes proposees et commandes perso
(« Tes commandes »), toutes des modeles a champs types. Fichier : outils_docs/schemas/banque_autoexec.json
({"entrees": [...]}).
  charge(racine)                          [entree] ; fichier absent ou invalide : ValueError qui cite le fichier
  rend(entree, valeurs)                   la ligne produite ; ValueError motivee sur une valeur invalide
  valide_entree(entree)                   entree normalisee ; ValueError motivee
  ajoute(racine, entree, builds_en_cours) entree "perso" datee du jour, ecrite en Transaction("banque-autoexec")
Entree : nom, categorie, description, modele (« Timer{n} {...} » : {cle} = champ), champs [{cle, type, libelle, defaut,
choix?, min?, max?}], origine (proposee|perso), ajoutee (AAAA-MM-JJ). Au moins un champ ; chaque {cle} du modele est un
champ et chaque champ sert dans le modele (les accolades du JSON, `{"Enable"`, ne sont pas des champs).
Types de champ (valeur de la page : nombre ou texte, les deux acceptes) :
  texte   une ligne (ni saut de ligne ni retour chariot : un texte ne peut pas ajouter une commande), insere tel quel
  nombre  entier ou decimal, dans min/max s'ils sont donnes ; booleen refuse
  liste   une valeur de `choix` (textes, ou [{valeur, libelle}] : Action d'un Timer 0=Eteindre 1=Allumer 2=Basculer
          3=Clignoter ou Regle si USE_RULES, xdrv_09_timers.ino)
  heure   HH:MM de 00:00 a 23:59
  jours   7 caracteres 0/1, dimanche en premier (« SMTWTFS », xdrv_09_timers.ino : 0 ou - = inactif, autre = actif ;
          seuls 0 et 1 sont acceptes ici)
  relais  entier >= 1 (Output d'un Timer : 1..16, borne haute laissee a `max` du champ)
Secrets : une entree dont le modele repond a autoexec_analyse.SECRETS ne peut pas porter de valeur par defaut (la
banque est versionnee ; le secret se saisit dans la page, qui le masque). Banc : test_autoexec_banque.py.
"""

import datetime
import json
import re
from pathlib import Path

import autoexec_analyse as aa
import fichiers_berry_sauvegarde as fbs

FICHIER = "outils_docs/schemas/banque_autoexec.json"
TYPES = ("texte", "nombre", "liste", "heure", "jours", "relais")
ORIGINES = ("proposee", "perso")
HEURE = re.compile(r"([01]\d|2[0-3]):[0-5]\d")
JOURS = re.compile(r"[01]{7}")
CHAMP = re.compile(r"\{([A-Za-z_]\w*)\}")
CLES_ENTREE = {"nom", "categorie", "description", "modele", "champs", "origine", "ajoutee"}
CLES_CHAMP = {"cle", "type", "libelle", "defaut", "choix", "min", "max"}


def _nombre(valeur, champ):
    if isinstance(valeur, bool):
        raise ValueError(f"{champ['libelle']} : un nombre est attendu")
    try:
        n = float(valeur)
    except (TypeError, ValueError):
        raise ValueError(f"{champ['libelle']} : « {valeur} » n'est pas un nombre") from None
    if n != n or n in (float("inf"), float("-inf")):
        raise ValueError(f"{champ['libelle']} : « {valeur} » n'est pas un nombre")
    return int(n) if n == int(n) and "." not in str(valeur) else n


def _borne(n, champ, bas, haut):
    if not (haut is None or n <= haut) or not (bas is None or n >= bas):
        raise ValueError(f"{champ['libelle']} : {n} hors de {bas if bas is not None else '…'} à {haut if haut is not None else '…'}")


def _valeur(champ, brut):
    """Texte a inserer pour `brut` selon le type du champ ; ValueError motivee."""
    type_, nom = champ["type"], champ["libelle"]
    if type_ == "texte":
        texte = str(brut)
        if "\n" in texte or "\r" in texte:
            raise ValueError(f"{nom} : pas de saut de ligne")
        return texte
    if type_ in ("nombre", "relais"):
        n = _nombre(brut, champ)
        if type_ == "relais" and (n != int(n) or n < 1):
            raise ValueError(f"{nom} : un numéro de relais entier, 1 au moins")
        _borne(n, champ, champ.get("min"), champ.get("max"))
        return str(n)
    texte = str(brut)
    if type_ == "heure":
        if not HEURE.fullmatch(texte):
            raise ValueError(f"{nom} : « {texte} » n'est pas une heure HH:MM de 00:00 à 23:59")
        return texte
    if type_ == "jours":
        if not JOURS.fullmatch(texte):
            raise ValueError(f"{nom} : 7 chiffres 0 ou 1, dimanche en premier (« {texte} »)")
        return texte
    valeurs = [str(c["valeur"] if isinstance(c, dict) else c) for c in champ["choix"]]
    if texte not in valeurs:
        raise ValueError(f"{nom} : « {texte} » n'est pas dans les choix ({', '.join(valeurs)})")
    return texte


def rend(entree, valeurs):
    """Ligne produite : chaque {cle} du modele remplacee par la valeur validee (celle de `valeurs`, sinon le defaut)."""
    par_cle = {}
    for champ in entree["champs"]:
        brut = valeurs.get(champ["cle"], champ.get("defaut"))
        if brut is None or brut == "" and champ["type"] != "texte":
            raise ValueError(f"{champ['libelle']} : valeur manquante")
        par_cle[champ["cle"]] = _valeur(champ, brut)
    return CHAMP.sub(lambda m: par_cle.get(m.group(1), m.group(0)), entree["modele"])


def _texte(entree, cle):
    v = entree.get(cle)
    if not isinstance(v, str) or (cle != "description" and not v.strip()) or "\n" in v or "\r" in v:
        raise ValueError(f"{cle} : un texte d'une ligne{' non vide' if cle != 'description' else ''} est attendu")
    return v


def _champ(c):
    if not isinstance(c, dict) or set(c) - CLES_CHAMP:
        raise ValueError(f"champ invalide : {c!r}")
    c = dict(c)
    for cle in ("cle", "libelle"):
        c[cle] = _texte(c, cle)
    if not re.fullmatch(r"[A-Za-z_]\w*", c["cle"]):
        raise ValueError(f"cle de champ invalide : {c['cle']}")
    if c.get("type") not in TYPES:
        raise ValueError(f"{c['cle']} : type inconnu « {c.get('type')} » ({', '.join(TYPES)})")
    if c["type"] == "liste":
        if not isinstance(c.get("choix"), list) or not c["choix"]:
            raise ValueError(f"{c['cle']} : une liste demande des choix")
        for ch in c["choix"]:
            if not (isinstance(ch, str) or (isinstance(ch, dict) and set(ch) == {"valeur", "libelle"})):
                raise ValueError(f"{c['cle']} : choix invalide {ch!r}")
    elif "choix" in c:
        raise ValueError(f"{c['cle']} : des choix seulement pour une liste")
    for cle in ("min", "max"):
        if cle in c:
            if c["type"] not in ("nombre", "relais"):
                raise ValueError(f"{c['cle']} : {cle} seulement pour un nombre")
            c[cle] = _nombre(c[cle], c)
    if c.get("defaut") is not None and c["defaut"] != "":
        _valeur(c, c["defaut"])                          # un defaut doit passer la validation de son propre champ
    c.setdefault("defaut", None)
    return c


def valide_entree(entree):
    """Entree normalisee (copie) ; ValueError motivee."""
    if not isinstance(entree, dict) or set(entree) != CLES_ENTREE:
        manque = sorted(CLES_ENTREE - set(entree)) if isinstance(entree, dict) else []
        raise ValueError(f"entrée invalide : clés attendues {sorted(CLES_ENTREE)}" + (f", manque {manque}" if manque else ""))
    e = {cle: _texte(entree, cle) for cle in ("nom", "categorie", "description", "modele")}
    champs = entree["champs"]
    if not isinstance(champs, list) or not champs:
        raise ValueError("une commande demande au moins un champ")
    e["champs"] = [_champ(c) for c in champs]
    cles = [c["cle"] for c in e["champs"]]
    if len(cles) != len(set(cles)):
        raise ValueError("deux champs portent la même clé")
    utilises = set(CHAMP.findall(e["modele"]))
    if utilises - set(cles):
        raise ValueError(f"le modèle cite {sorted(utilises - set(cles))}, qui ne sont pas des champs")
    if set(cles) - utilises:
        raise ValueError(f"champs jamais utilisés par le modèle : {sorted(set(cles) - utilises)}")
    if entree["origine"] not in ORIGINES:
        raise ValueError(f"origine « {entree['origine']} » : proposee ou perso")
    e["origine"] = entree["origine"]
    if not isinstance(entree["ajoutee"], str) or not re.fullmatch(r"\d{4}-\d\d-\d\d", entree["ajoutee"]):
        raise ValueError("ajoutee : une date AAAA-MM-JJ")
    try:
        datetime.date.fromisoformat(entree["ajoutee"])
    except ValueError:
        raise ValueError("ajoutee : une date AAAA-MM-JJ réelle") from None
    e["ajoutee"] = entree["ajoutee"]
    if aa.SECRETS.search(e["modele"]) and any(c["defaut"] not in (None, "") for c in e["champs"]):
        raise ValueError("une commande à secret n'a pas de valeur par défaut : le secret se saisit dans la page")
    return e


def _entrees(texte, source):
    try:
        entrees = [valide_entree(e) for e in json.loads(texte)["entrees"]]
    except (ValueError, KeyError, TypeError) as erreur:
        raise ValueError(f"{source} invalide : {erreur}") from None
    noms = [e["nom"].casefold() for e in entrees]
    if len(noms) != len(set(noms)):
        raise ValueError(f"{source} invalide : un nom est en double")
    return entrees


def charge(racine):
    chemin = Path(racine) / FICHIER
    try:
        texte = chemin.read_text(encoding="utf-8")
    except OSError as erreur:
        raise ValueError(f"{FICHIER} illisible : {erreur}") from None
    return _entrees(texte, FICHIER)


def ajoute(racine, entree, builds_en_cours):
    builds = builds_en_cours()
    if builds is None:
        raise RuntimeError("impossible de savoir si un build tourne : ecriture refusee")
    if builds:
        raise RuntimeError("un build est en cours (" + ", ".join(builds) + ") : ecriture refusee")
    entree = valide_entree(dict(entree, origine="perso", ajoutee=datetime.date.today().isoformat()))
    existantes = charge(racine)
    nom = entree["nom"].casefold()
    if nom in {e["nom"].casefold() for e in existantes}:
        raise ValueError(f"« {entree['nom']} » existe déjà dans la banque")
    texte = json.dumps({"entrees": existantes + [entree]}, ensure_ascii=False, indent=1) + "\n"
    with fbs.Transaction(racine, "banque-autoexec") as tr:
        tr.ecrit(FICHIER, texte.encode("utf-8"))
    return entree
