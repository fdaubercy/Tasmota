"""JSON modele du persist (assistant de creation, spec 2026-10-27 §5.1 et §5.4) : lecture et couverture du parc.

Le modele `outils_docs/schemas/modele_persist.json` decrit tout `_persist.json` du parc ; l'assistant (page 7900) en
tire le persist, l'autoexec, la section du cenv et la section `#elif` du .h d'une nouvelle carte. Ce module le LIT
et le COMPARE aux persists du depot ; il n'ecrit rien.

FORME DU MODELE (contrat partage par les actions A1 a A6)
---------------------------------------------------------
  version         1.
  socle           arbre complet d'un persist, dans l'ordre des cles du parc (diverses, serveur, template, modules,
                  drivers), toutes les cles avec leur valeur par defaut (la valeur commune du parc quand elle existe).
                  Gabarits : "{{lieu}}", "{{nom}}", "{{nom_lisible}}", "{{hostname}}", "{{topic}}", "{{groupe}}"
                  (= tasmotas/<lieu>), "{{ip}}", "{{passerelle}}", "{{reseau1}}", "{{reseau2}}", "{{id}}",
                  "{{ip_maitre}}", "{{type_esp}}", "{{heure}}", "{{ssid_ap}}". Une chaine qui vaut EXACTEMENT
                  "{{id}}" est remplacee par l'entier. template.GPIO vaut [] : le generateur le remplit de 1, sur la
                  longueur puces.<p>.gpio. Secrets : "@secret:wifi1", "@secret:wifi2", "@secret:mqtt", "@secret:ap",
                  "@secret:ftp" (valeur reprise cote serveur, jamais dans le modele).
  roles           {"autonome"|"maitre"|"esclave": {"<chemin.pointe>": valeur}}.
  puces           {"ESP32"|"ESP32S3"|"ESP32P4": {gpio, historique, prefixe_env, h, ajouts}} ; h = lignes du gabarit
                  de la section `#elif` du .h (variables {{env}}, {{define}} et celles du socle ; mots de passe
                  {{@wifi1}}, {{@wifi2}}, {{@ap}}) ; ajouts = {"<chemin.pointe>": valeur}.
  blocs           liste ordonnee (ordre des questions) de {id, libelle, aide, puces, dependances, actif, inactif,
                  solidify, exclude_si_inactif, autoexec, h}. autoexec = [{rang, appel, modules, condition, groupe}],
                  appel parmi importe | compile | charge | leds | historique ; condition = chemin du bloc du persist
                  dont "activation" doit valoir "ON" (demarrage.be), null = toujours. h = lignes du .h propres au
                  bloc (USE_MODBUS, USE_I2C, USE_SHUTTER...), reprises des sections #elif reelles : ajoutees en fin
                  de la section #elif de la carte quand le bloc est coche (A4), dedoublonnees (ruban et ledRGB
                  portent tous deux USE_WS2812) ; [] si le bloc n'a pas de define. Ces lignes ne figurent PAS dans
                  puces.<p>.h (Ruling 6) ; la partie « post-process » commune du .h en tire les defines derives
                  (USE_MODBUS -> USE_MODBUS_BRIDGE, USE_RTC_CHIPS -> USE_DS3231, USE_SHUTTER -> SHUTTER_SUPPORT...).
  socle_autoexec  {entete: [lignes de commentaire], entrees: [meme forme]} ; seul le socle a l'appel compileSocle.
  metier          {gabarit, cles_propres, controle, fonctions, autoexec} : gabarit de modules.<metier> a
                  environnement vide ; cles_propres = cles de premier niveau propres a une carte, hors couverture
                  (voir plus bas) ; lignes des squelettes controle{{Metier}}.be et {{metier}}Fonctions.be ; lignes
                  d'autoexec du bloc principal (compile au rang 900, chargeFichier au rang 999). Variables {{metier}},
                  {{Metier}}.
  cenv            lignes du gabarit de la section [env:...] ; {{env}}, {{base}}, {{define}}, {{dossier}},
                  {{solidify}} et {{exclude}} (une valeur par ligne, alignees sous la premiere).
  a_completer     chemins ajoutes par la fusion automatique (A6), a relire : vide dans un modele relu.

Ordre d'application (generateur, A2) : socle, puis roles[role], puis puces[puce].ajouts, puis, pour chaque bloc
PERMIS pour la puce, actif ou inactif selon la reponse (un bloc interdit pour la puce n'applique rien). Une valeur
null retire la cle du persist. Une cle absente du socle est ajoutee en fin de son objet parent. Les entrees
d'autoexec sont triees par rang ; deux entrees consecutives de meme appel et meme condition peuvent etre fusionnees
en une ligne (dedoublonnee), comme `demarrage.charge([...])` de la cuve ; un module requis par un bloc actif n'est
jamais exclu, meme s'il figure dans exclude_si_inactif d'un bloc inactif.

CHEMINS ET COUVERTURE (decision 1 du controleur, 2026-10-27)
------------------------------------------------------------
Un chemin est le tuple des cles jusqu'a une feuille (valeur non objet, ou objet vide). Deux reductions :
  - dans un `environnement`, un element `xxxN` dont le parent commence par `xxx` (pinsSDs/pinsSD4, relais/relai2,
    TasmotaSlaveModBus/TasmotaSlaveModBus1, VRs/VR1...) devient `xxx#` : les elements numerotes ont une forme
    commune. Les noms qui ne suivent pas ce motif (ADS1115, voies/A0, VR1/relais1) restent tels quels ;
  - sous `modules`, toute cle autre que `activation` (le bloc metier, dont le nom varie) devient `*`, et la
    comparaison s'arrete aux cles de premier niveau du bloc metier (name, activation, reglage, log, logs,
    environnement...) et aux NOMS des groupes de son environnement (boutons, relais...). Le contenu des elements
    `xxxN.*` et les sous-cles (logs.*, dimensions.*) relevent de l'editeur d'elements (A7).
Seules les cles de premier niveau listees EXPLICITEMENT dans metier.cles_propres (["dimensions"] : la cuve) echappent
a la couverture dans ecarts() ; toute autre cle de premier niveau absente du gabarit metier (une future
modules.cuve.seuilX) sort dans « nouvelles », meme portee par une seule carte (Ruling 1 precise, tour de correction 1).
Les environnements des DRIVERS restent couverts en entier.
"""

import json
import re
from pathlib import Path

FICHIER_MODELE = "outils_docs/schemas/modele_persist.json"
CLES_MODELE = ("version", "socle", "roles", "puces", "blocs", "socle_autoexec", "metier", "cenv", "a_completer")
SUFFIXE = re.compile(r"^(.*\D)\d+$")          # xxxN : racine (finit par un non-chiffre) + numero


def charge_modele(racine):
    """Le modele lu ; ValueError("modele_persist.json ligne L : ...") s'il est illisible ou incomplet."""
    chemin = Path(racine) / FICHIER_MODELE
    try:
        texte = chemin.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"modele_persist.json illisible : {exc.strerror or exc}") from exc
    try:
        modele = json.loads(texte)
    except json.JSONDecodeError as exc:
        raise ValueError(f"modele_persist.json ligne {exc.lineno} : {exc.msg}") from exc
    if not isinstance(modele, dict):
        raise ValueError("modele_persist.json : un objet JSON est attendu")
    manquantes = [c for c in CLES_MODELE if c not in modele]
    if manquantes:
        raise ValueError(f"modele_persist.json : cle(s) manquante(s) : {', '.join(manquantes)}")
    if modele["version"] != 1:
        raise ValueError(f"modele_persist.json : version {modele['version']!r} inconnue (1 attendue)")
    return modele


# ---- Chemins -----------------------------------------------------------------------------------------------
def _feuilles(donnees, chemin):
    if isinstance(donnees, dict) and donnees:
        for cle, valeur in donnees.items():
            yield from _feuilles(valeur, chemin + (cle,))
    else:
        yield chemin, donnees


def reduit(brut):
    """Chemin brut -> chemin compare (reductions xxxN -> xxx# et modules.*, voir l'en-tete)."""
    brut = tuple(brut)
    if brut[:1] == ("modules",) and len(brut) >= 2 and brut[1] != "activation":
        brut = ("modules", "*") + brut[2:]
        brut = brut[:4] if len(brut) > 3 and brut[2] == "environnement" else brut[:3]
    sortie, dans_env = [], False
    for i, cle in enumerate(brut):
        m = SUFFIXE.match(cle) if dans_env else None
        if m and brut[i - 1].startswith(m.group(1)):
            cle = m.group(1) + "#"
        sortie.append(cle)
        dans_env = dans_env or cle == "environnement"
    return tuple(sortie)


def chemins(donnees, prefixe=()):
    """Ensemble des chemins feuilles (reduits) de `donnees`, places sous `prefixe` (tuple de cles)."""
    return {reduit(c) for c, _ in _feuilles(donnees, tuple(prefixe))}


def _valeurs(donnees):
    """{chemin reduit: [valeurs]} (valeurs des feuilles, plusieurs pour un xxx#)."""
    res = {}
    for c, v in _feuilles(donnees, ()):
        res.setdefault(reduit(c), []).append(v)
    return res


def _pointes(table):
    """Chemins d'une table {"a.b.c": valeur} (roles, ajouts, actif, inactif) ; null = retrait, pas un chemin."""
    res = set()
    for cle, valeur in table.items():
        if valeur is not None:
            res |= chemins(valeur, tuple(cle.split(".")))
    return res


def chemins_modele(modele):
    """Chemins decrits par le modele : socle, roles, puces.*.ajouts, blocs.*.actif/inactif et gabarit metier."""
    res = chemins(modele["socle"])
    for role in modele.get("roles", {}).values():
        res |= _pointes(role)
    for puce in modele.get("puces", {}).values():
        res |= _pointes(puce.get("ajouts", {}))
    for bloc in modele.get("blocs", []):
        res |= _pointes(bloc.get("actif", {})) | _pointes(bloc.get("inactif", {}))
    res |= chemins(modele.get("metier", {}).get("gabarit", {}), ("modules", "*"))
    return res


# ---- Parc ----------------------------------------------------------------------------------------------------
def persists_du_depot(racine):
    """[(chemin relatif, donnees ou None, erreur)] des data/*/*/_persist.json hors *sauvegarde*, tries."""
    racine = Path(racine)
    res = []
    for f in sorted(racine.glob("data/*/*/_persist.json")):
        rel = f.relative_to(racine).as_posix()
        if "sauvegarde" in rel.lower():
            continue
        try:
            res.append((rel, json.loads(f.read_text(encoding="utf-8-sig")), ""))
        except (OSError, ValueError) as exc:
            res.append((rel, None, f"{type(exc).__name__} : {exc}"))
    return res


def _cle_propre(chemin, cles_propres):
    """modules.*.<cle> listee dans metier.cles_propres : hors couverture (liste explicite, jamais deduite du parc)."""
    return len(chemin) == 3 and chemin[:2] == ("modules", "*") and chemin[2] in cles_propres


def _constante(valeur):
    """Valeur du socle comparable au parc : ni gabarit, ni secret, ni objet."""
    if isinstance(valeur, dict):
        return False
    return not (isinstance(valeur, str) and ("{{" in valeur or valeur.startswith("@secret:")))


def ecarts(racine, modele):
    """{nouvelles: {chemin: [cartes]}, disparues: [chemin], divergentes: {chemin: {modele, parc}},
    illisibles: [fichier]} ; chemin = cles jointes par des points (modules.*.name, ...TasmotaSlaveModBus#.id).
      - nouvelles : chemins du parc absents du modele, sauf modules.*.<cle> de metier.cles_propres ;
      - disparues : chemins du modele presents dans aucun persist ;
      - divergentes : constante du SOCLE differente de la valeur commune a TOUS les persists lisibles. Les gabarits
        ({{...}}), les secrets (@secret:*) et tout chemin sous `modules` sont ignores : le nom du bloc metier y est
        reduit a `*` et ses chemins sont tronques (logs, environnement.boutons...), si bien que la « valeur » d'un
        tel chemin est un objet propre a chaque carte, pas un defaut comparable ; le gabarit metier est d'ailleurs
        hors socle (le socle ne porte que modules.activation, ignore avec le reste)."""
    cles_propres = modele.get("metier", {}).get("cles_propres", [])
    parc, valeurs, illisibles, lus = {}, {}, [], 0
    for rel, donnees, _ in persists_du_depot(racine):
        if donnees is None:
            illisibles.append(rel)
            continue
        lus += 1
        carte = Path(rel).parent.name
        for c, vs in _valeurs(donnees).items():
            parc.setdefault(c, set()).add(carte)
            valeurs.setdefault(c, []).append([json.dumps(v, sort_keys=True, ensure_ascii=False) for v in vs])
    decrits = chemins_modele(modele)
    nouvelles = {".".join(c): sorted(cartes) for c, cartes in parc.items()
                 if c not in decrits and not _cle_propre(c, cles_propres)}
    disparues = sorted(".".join(c) for c in decrits if c not in parc)
    divergentes = {}
    for c, vs in _valeurs(modele["socle"]).items():
        if c[:1] == ("modules",) or len(vs) != 1 or not _constante(vs[0]) or c not in parc:
            continue
        observees = {v for liste in valeurs[c] for v in liste}
        if len(valeurs[c]) == lus and len(observees) == 1:
            commune = json.loads(next(iter(observees)))
            if commune != vs[0]:
                divergentes[".".join(c)] = {"modele": vs[0], "parc": commune}
    return {"nouvelles": dict(sorted(nouvelles.items())), "disparues": disparues,
            "divergentes": dict(sorted(divergentes.items())), "illisibles": illisibles}
