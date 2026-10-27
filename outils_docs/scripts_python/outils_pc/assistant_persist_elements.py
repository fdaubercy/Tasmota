"""Entrees/sorties du bloc metier (assistant de creation du persist, spec 2026-10-27 decision 4, action A7).

Un bloc metier porte, dans modules.<principal>.environnement, sept GROUPES d'elements : boutons, interrupteurs, relais,
capteurs, compteurs, thermometres, analogiques. Un element est un objet {activation, nom, id, pin, type, virtuel,
relaisLie, ...} range sous la cle <singulier><N> (relai1, relai2... N = rang de l'element, a partir de 1). Le groupe
porte aussi ses propres reglages (analogiques : activation, name, valeurMin, valeurMax ; compteurs et thermometres :
affichageWebSensor). Le modele les decrit dans metier.elements :
  metier.elements.<groupe> = {singulier, gabarit (element neuf), optionnelles ({cle: defaut} des cles que le parc
                              ajoute selon la carte : idModBus, channel, nbLeds, serialNumber...), groupe (reglages du
                              groupe), h (lignes du .h, thermometres seulement : USE_DS18x20)}
`singulier` et `optionnelles` se relevent dans le parc (releve_modele) : le banc compare le modele a ce releve.
  - gabarits_elements(modele)          {groupe: copie du gabarit d'un element neuf}
  - broches_valides(puce)              GPIO de data/fs/configGlobal.be (branche typeESP de la puce), dans son ordre
  - broches_drivers(persist)           {libelle: broche} des drivers ACTIVES : ModBus RX/TX, I2C, LEDs
  - verifie_elements(puce, elements, broches_drivers)   refus : broche hors plage, broche en double (elements ACTIFS
                                       entre eux et avec les drivers), nom en double dans un groupe
  - applique(modele, obj, r)           ecrit r.elements dans le persist genere (metier principal seulement)
  - lit_elements(modele, environnement) l'inverse : (elements, reglages de groupe) d'un persist du parc
  - lignes_h(modele, r)                lignes de la section #elif du .h dues aux elements (USE_DS18x20)
La broche -1 veut dire « sans broche » : jamais hors plage, jamais en double. Un element OFF est ignore (ni plage ni
doublon) : il n'occupe pas sa broche (cuve : compteur1 OFF sur la broche RX ModBus) et le parc en garde de perimees
(differentiel ESP32 : compteur1 OFF sur GPIO40, qui n'existe pas sur ESP32).
"""

import copy
import functools
import json
import re
from collections import Counter
from pathlib import Path

GROUPES_ELEMENTS = ("boutons", "interrupteurs", "relais", "capteurs", "compteurs", "thermometres", "analogiques")
RACINE = Path(__file__).resolve().parents[3]
CONFIG_GLOBAL = "data/fs/configGlobal.be"
ORDRE_GPIO = re.compile(r'==\s*"(\w+)"\s*\)\s*\n\s*ordreGPIO\s*=\s*\[([^\]]*)\]')


def _config(modele):
    return modele["metier"]["elements"]


def gabarits_elements(modele):
    """{groupe: element neuf} (copies, dans l'ordre de GROUPES_ELEMENTS)."""
    return {g: copy.deepcopy(_config(modele)[g]["gabarit"]) for g in GROUPES_ELEMENTS}


def singulier(modele, groupe):
    return _config(modele)[groupe]["singulier"]


@functools.lru_cache(maxsize=8)
def _gpio_par_puce(chemin):
    try:
        texte = Path(chemin).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ValueError(f"{CONFIG_GLOBAL} illisible : {exc.strerror or exc}") from exc
    return {puce: [int(n) for n in re.findall(r'"GPIO(\d+)"', liste)] for puce, liste in ORDRE_GPIO.findall(texte)}


def broches_valides(puce, racine=None):
    """GPIO de la puce, dans l'ordre de configGlobal.be (ordreGPIO). ValueError si la puce n'y figure pas."""
    tables = _gpio_par_puce(str((RACINE if racine is None else Path(racine)) / CONFIG_GLOBAL))
    if puce not in tables:
        raise ValueError(f"{CONFIG_GLOBAL} : aucune liste ordreGPIO reconnue pour la puce {puce!r}")
    return list(tables[puce])


# ---- Broches des drivers --------------------------------------------------------------------------------------
def _actif(entree):
    return isinstance(entree, dict) and entree.get("activation", "ON") == "ON"


def broches_drivers(persist):
    """{libelle: broche} des drivers ACTIVES du persist (dict) : ModBus RX/TX, I2C (SDA/SCL) et LEDs. Seules les
    broches >= 0 d'entrees actives comptent."""
    drivers = persist.get("drivers", {}) if isinstance(persist, dict) else {}
    res = {}
    for nom, liste, prefixe in (("ModBus", "pinsModBus", "ModBus"), ("I2C", "pinsI2Cs", "I2C"), ("leds", "leds", "LED")):
        pilote = drivers.get(nom) if isinstance(drivers, dict) else None
        if not isinstance(pilote, dict) or not _actif(pilote):
            continue
        env = pilote.get("environnement")
        entrees = env.get(liste) if isinstance(env, dict) else None
        for cle, e in (entrees.items() if isinstance(entrees, dict) else ()):
            if _actif(e) and type(e.get("pin")) is int and e["pin"] >= 0:
                res[f"{prefixe} {e.get('nom', cle) if nom == 'I2C' else cle}"] = e["pin"]
    return res


def _broches_prises(broches_drivers):
    """{broche: libelle} depuis {libelle: broche}, {broche: libelle} ou une liste de broches."""
    if isinstance(broches_drivers, dict):
        return {(p if type(p) is int else v): (v if type(p) is int else p) for p, v in broches_drivers.items()}
    return {p: f"driver (broche {p})" for p in broches_drivers}


# ---- Verification ---------------------------------------------------------------------------------------------
def verifie_elements(puce, elements, broches_drivers, racine=None):
    """Liste des refus (vide = bon) pour elements = {groupe: [element, ...]}."""
    refus = []
    try:
        valides, erreur_plage = set(broches_valides(puce, racine)), ""
    except ValueError as exc:                       # configGlobal.be reformate : refus lisible, pas de plantage
        valides, erreur_plage = set(), str(exc)
    prises = _broches_prises(broches_drivers)
    occupees = {}
    for groupe, liste in elements.items():
        if groupe not in GROUPES_ELEMENTS:
            refus.append(f"groupe d'elements inconnu : {groupe!r}")
            continue
        noms = {}
        for rang, e in enumerate(liste, 1):
            if not isinstance(e, dict):
                refus.append(f"{groupe} #{rang} : objet attendu")
                continue
            nom = e.get("nom")
            if _actif(e) and not (isinstance(nom, str) and nom.strip()):
                refus.append(f"{groupe} #{rang} : nom vide ou non textuel")
            libelle = f"{groupe} #{rang}" + (f" « {nom} »" if isinstance(nom, str) and nom else "")
            if isinstance(nom, str) and nom:
                if nom in noms:
                    refus.append(f"{groupe} : nom « {nom} » en double (#{noms[nom]} et #{rang})")
                noms.setdefault(nom, rang)
            pin = e.get("pin", -1)
            if type(pin) is not int:
                refus.append(f"{libelle} : broche entiere attendue")
                continue
            if pin == -1 or not _actif(e):
                continue
            if erreur_plage:
                refus.append(f"{libelle} : broche {pin} non verifiable ({erreur_plage})")
                continue
            if pin < -1 or pin not in valides:
                refus.append(f"{libelle} : broche {pin} hors plage pour {puce} (data/fs/configGlobal.be)")
                continue
            if pin in prises:
                refus.append(f"{libelle} : broche {pin} deja prise par {prises[pin]}")
            elif pin in occupees:
                refus.append(f"{libelle} : broche {pin} deja prise par {occupees[pin]}")
            else:
                occupees[pin] = libelle
    return list(dict.fromkeys(refus))


# ---- Ecriture dans le persist genere ------------------------------------------------------------------------------
def applique(modele, obj, r):
    """Ecrit r.elements / r.elements_groupe dans modules.<metier principal>.environnement de `obj`. Un groupe absent
    des reponses reste celui du gabarit (comportement d'avant l'editeur)."""
    if not r.metiers or not (r.elements or r.elements_groupe):
        return
    env = obj["modules"][r.metiers[0]]["environnement"]
    for groupe in GROUPES_ELEMENTS:
        if groupe not in r.elements and groupe not in r.elements_groupe:
            continue
        ancien = env.get(groupe, {})
        sing = singulier(modele, groupe)
        reglages = {k: v for k, v in ancien.items() if not isinstance(v, dict)}
        reglages.update(r.elements_groupe.get(groupe, {}))
        if groupe in r.elements:
            liste = r.elements[groupe]
            if "activation" in reglages and "activation" not in r.elements_groupe.get(groupe, {}):
                reglages["activation"] = "ON" if any(isinstance(e, dict) and e.get("activation") == "ON" for e in liste) else "OFF"
            contenu = {f"{sing}{i}": copy.deepcopy(e) for i, e in enumerate(liste, 1)}
        else:
            contenu = {k: v for k, v in ancien.items() if isinstance(v, dict)}
        env[groupe] = dict(copy.deepcopy(reglages), **contenu)


def lit_elements(modele, environnement):
    """({groupe: [element, ...]}, {groupe: reglages du groupe}) d'un `environnement` du parc : l'inverse d'applique."""
    elements, groupes = {}, {}
    for groupe in GROUPES_ELEMENTS:
        contenu = environnement.get(groupe)
        if not isinstance(contenu, dict):
            continue
        motif = re.compile(re.escape(singulier(modele, groupe)) + r"(\d+)$")
        numerotes = sorted((int(motif.match(k).group(1)), k) for k, v in contenu.items() if isinstance(v, dict) and motif.match(k))
        elements[groupe] = [copy.deepcopy(contenu[k]) for _, k in numerotes]
        groupes[groupe] = {k: copy.deepcopy(v) for k, v in contenu.items() if not isinstance(v, dict)}
    return elements, groupes


# ---- Section du .h ----------------------------------------------------------------------------------------------------
def lignes_h(modele, r):
    """Lignes `h` du modele des groupes NON vides de r.elements (thermometres -> USE_DS18x20)."""
    res = []
    for groupe in GROUPES_ELEMENTS:
        if r.elements.get(groupe):
            res += _config(modele)[groupe].get("h", [])
    return res


# ---- Releve du parc ---------------------------------------------------------------------------------------------------
def releve_modele(racine, modele):
    """metier.elements tel que le parc le justifie : gabarit, groupe et h du modele ; singulier et optionnelles
    relevees dans les persists (valeur par defaut d'une cle optionnelle = la plus frequente, a egalite la premiere
    en ordre alphabetique de son JSON)."""
    import assistant_persist_modele as apm
    vues = {g: {} for g in GROUPES_ELEMENTS}
    sing = {}
    for _, donnees, _ in apm.persists_du_depot(racine):
        if not isinstance(donnees, dict):
            continue
        for metier, bloc in donnees.get("modules", {}).items():
            if metier == "activation" or not isinstance(bloc, dict):
                continue
            for groupe, contenu in bloc.get("environnement", {}).items():
                if groupe not in vues or not isinstance(contenu, dict):
                    continue
                for cle, e in contenu.items():
                    if isinstance(e, dict):
                        sing.setdefault(groupe, re.sub(r"\d+$", "", cle))
                        for c, v in e.items():
                            vues[groupe].setdefault(c, Counter())[json.dumps(v, ensure_ascii=False)] += 1
    res = {}
    for g in GROUPES_ELEMENTS:
        actuel = _config(modele)[g]
        opt = {c: json.loads(sorted(n.items(), key=lambda kv: (-kv[1], kv[0]))[0][0])
               for c, n in vues[g].items() if c not in actuel["gabarit"]}
        res[g] = dict(actuel, singulier=sing.get(g, actuel["singulier"]), optionnelles=opt)
    return res
