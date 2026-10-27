"""Generation d'une nouvelle carte a partir des reponses (assistant de creation du persist, spec 2026-10-27 §5.2).

Fonctions PURES (rien n'est ecrit) : `variables` lit le parc (maitre, passerelle), le reste ne lit que le modele
(`outils_docs/schemas/modele_persist.json`, forme decrite dans assistant_persist_modele) et les reponses.
  - persist(modele, r, vars, secrets)   ordre d'application : socle, roles[role], puces[puce].ajouts, blocs PERMIS
                                        pour la puce (actif si coche, inactif sinon), puis un bloc modules.<metier>
                                        par metier. null retire la cle ; une cle nouvelle va en fin de son parent.
                                        secrets=None : chaque "@secret:x" devient "***" (apercu de la page).
  - autoexec(modele, r)                 entrees du socle, des blocs coches, puis du metier principal ; triees par
                                        (groupe, rang) ; entrees consecutives de meme appel, meme condition et meme
                                        groupe fusionnees (modules dedoublonnes) ; une ligne vide entre les groupes.
  - listes_cenv(modele, r)              solidify = ${berry_commun.socle} + solidify des blocs coches ; exclude =
                                        exclude_si_inactif des blocs non coches, sauf les fichiers d'un bloc coche.
                                        Les modules metier ne vont dans aucune liste (spec §5.6).
  - coherence(...)                      refus (liste de messages) : voir sa docstring.
IDENTITE : les champs vides de Reponses prennent les valeurs de fichiers_berry_creation.identite_par_defaut ;
nom_template suit nom_lisible, client suit hostname et ssid_ap vaut <hostname>-GATEWAY (Ruling 8). Un RTC
(heure = "RTC") coche le bloc ds3231. Les mots de passe ne passent JAMAIS dans un message d'erreur.
"""

import copy
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import assistant_persist_modele as apm
import assistant_persist_parc as parc
import fichiers_berry_creation as fbc
import fichiers_berry_ini as fbi

RACINE = Path(__file__).resolve().parents[3]
PASSERELLE_ESCLAVE = "192.168.4.1"                  # point d'acces Range Extender du maitre
PASSERELLE_DEFAUT = "192.168.0.254"                 # si le parc n'en donne aucune
ROLES = ("autonome", "maitre", "esclave")
HEURES = ("NTP", "RTC", "UDP")
GROUPES = ("compilation", "chargement")
NOM_METIER = re.compile(r"[a-z][a-zA-Z0-9]*$")
GABARIT = re.compile(r"\{\{(\w+)\}\}")
APPEL = re.compile(r"^\s*demarrage\.(\w+)\((.*)\)\s*(#.*)?$")
CHEMINS_ID = (("serveur", "rangeExtender", "id"), ("serveur", "udp", "id"), ("serveur", "tcp", "id"),
              ("drivers", "ModBus", "id"))
# appels qui chargent un module SOLIDIFIE (demarrage.be) : leur fichier doit etre en flash
EN_FLASH = {"importe": None, "charge": None, "leds": ["controleLeds"], "historique": ["historiqueFonctions"]}


@dataclass
class Reponses:
    puce: str                 # "ESP32" | "ESP32S3" | "ESP32P4"
    base: str                 # env de base (vide -> base_par_defaut)
    lieu: str
    nom: str
    ip: str = "0.0.0.0"
    heure: str = "NTP"        # "NTP" | "RTC" | "UDP" ; RTC => DS3231 actif
    role: str = "autonome"    # "autonome" | "maitre" | "esclave"
    maitre: str = ""          # env du maitre (esclave)
    id: int = 0               # force a 0 hors esclave
    reseau1: str = ""         # autonome/maitre ; esclave -> <HOSTNAME maitre>-GATEWAY
    reseau2: str = ""         # vide -> reseau1
    topic: str = ""           # vide -> "<lieu>/<nom>"
    blocs: list = field(default_factory=list)    # ids de modele["blocs"] coches
    metiers: list = field(default_factory=list)  # noms modules.<x> ; le 1er = principal (decision 16)
    squelettes: bool = False
    define: str = ""          # vide -> fichiers_berry_creation.define(base, lieu, nom)
    # identite (Ruling 8) : vide -> identite_par_defaut / derivation (voir l'en-tete)
    hostname: str = ""
    nom_lisible: str = ""
    nom_template: str = ""    # template.NAME
    client: str = ""          # serveur.mqtt.client
    ssid_ap: str = ""         # serveur.rangeExtender.AP.SSID


# ---- Reponses et variables --------------------------------------------------------------------------------
def _prefixe(puce):
    if puce not in parc.PREFIXES:
        raise ValueError(f"puce inconnue : {puce!r}")
    return parc.PREFIXES[puce]


def _identite(r):
    defaut = fbc.identite_par_defaut(r.lieu, r.nom)
    hostname = r.hostname or defaut["PROJECT"]
    lisible = r.nom_lisible or defaut["FRIENDLY_NAME"]
    return {"hostname": hostname, "nom_lisible": lisible, "nom_template": r.nom_template or lisible,
            "client": r.client or hostname, "ssid_ap": r.ssid_ap or hostname + parc.SUFFIXE_AP,
            "topic": r.topic or defaut["MQTT_TOPIC"], "groupe": defaut["MQTT_GRPTOPIC"]}


def _env(r):
    return f"{_prefixe(r.puce)}-{r.lieu}-{r.nom}"


def _passerelle_du_parc(racine):
    """Passerelle la plus frequente des cartes non esclaves lisibles du parc."""
    compte = {}
    for _, d, _ in apm.persists_du_depot(racine):
        if not isinstance(d, dict):
            continue
        s = d.get("serveur", {})
        if s.get("rangeExtender", {}).get("id", 0) == 0 and s.get("IP", {}).get("IPGateway"):
            g = s["IP"]["IPGateway"]
            compte[g] = compte.get(g, 0) + 1
    return min(compte, key=lambda g: (-compte[g], g)) if compte else PASSERELLE_DEFAUT


def variables(racine, r):
    """Valeurs des {{...}} du modele (et env, base, define, dossier pour le cenv et le .h). ValueError si la puce,
    le role ou l'heure sont inconnus, ou si le maitre d'un esclave n'est pas un maitre du parc."""
    if r.role not in ROLES:
        raise ValueError(f"role inconnu : {r.role!r}")
    if r.heure not in HEURES:
        raise ValueError(f"reglage de l'heure inconnu : {r.heure!r}")
    prefixe = _prefixe(r.puce)
    base = r.base or parc.base_par_defaut(racine, r.puce)
    v = dict(_identite(r), lieu=r.lieu, nom=r.nom, ip=r.ip, heure=r.heure, type_esp=r.puce, ip_maitre="",
             env=_env(r), base=base, define=r.define or fbc.define(base or prefixe, r.lieu, r.nom),
             dossier=f"data/{r.lieu}/{prefixe}-{r.nom}")
    if r.role == "esclave":
        maitre = next((m for m in parc.maitres(racine) if m["env"] and m["env"] == r.maitre), None)
        if maitre is None:
            raise ValueError(f"esclave sans maitre du parc : {r.maitre!r}")
        reseau1 = maitre["hostname"] + parc.SUFFIXE_AP
        v.update(id=r.id, passerelle=PASSERELLE_ESCLAVE, ip_maitre=maitre["ip"], reseau1=reseau1,
                 reseau2=r.reseau2 or reseau1)
    else:
        v.update(id=0, passerelle=_passerelle_du_parc(racine), reseau1=r.reseau1, reseau2=r.reseau2 or r.reseau1)
    return v


def secrets_reponses(racine, r):
    """Mots de passe des reponses (assistant_persist_parc.secrets) ; ValueError qui nomme le reseau, sans valeur."""
    v = variables(racine, r)
    return parc.secrets(racine, v["reseau1"], v["reseau2"])


def _sous(obj, cles):
    for c in cles:
        obj = obj.get(c) if isinstance(obj, dict) else None
    return obj


def reponses_depuis_persist(modele, donnees, env, racine=None):
    """Reponses qui regenerent `donnees` (rejeu du parc, §7). env = <prefixe>-<lieu>-<nom>. racine (facultatif) :
    retrouve l'env du maitre d'un esclave, celui dont <HOSTNAME>-GATEWAY est son reseau1. Un bloc est coche si sa
    premiere valeur `actif` est celle du persist ; le bloc rangeExtender, seulement pour un maitre (un esclave a le
    Range Extender ON sans charger controleRangeExtender, rapport A1 n. 6). base reste vide."""
    s, d = donnees["serveur"], donnees["diverses"]
    re_, wifi = s["rangeExtender"], s["wifi"]
    puce = d["typeESP"]
    _, lieu, nom = env.split("-", 2)
    role = "esclave" if re_.get("id", 0) else ("maitre" if re_.get("activation") == "ON" else "autonome")
    maitre = ""
    if role == "esclave" and racine is not None:
        maitre = next((m["env"] for m in parc.maitres(racine)
                       if m["hostname"] + parc.SUFFIXE_AP == wifi["reseau1"]["nomReseauWifi"]), "") or ""
    blocs = []
    for b in modele["blocs"]:
        if puce not in b["puces"] or not b["actif"]:
            continue
        if b["id"] == "rangeExtender":
            coche = role == "maitre"
        else:
            cle, valeur = next(iter(b["actif"].items()))
            coche = _sous(donnees, cle.split(".")) == valeur
        if coche:
            blocs.append(b["id"])
    return Reponses(puce=puce, base="", lieu=lieu, nom=nom, ip=s["IP"]["IPAddress"],
                    heure=d["fuseauHoraire"]["typeReglageHeure"], role=role, maitre=maitre,
                    id=re_.get("id", 0) if role == "esclave" else 0, reseau1=wifi["reseau1"]["nomReseauWifi"],
                    reseau2=wifi["reseau2"]["nomReseauWifi"], topic=s["mqtt"]["topic"], blocs=blocs,
                    metiers=[k for k in donnees.get("modules", {}) if k != "activation"],
                    hostname=s["hostname"], nom_lisible=s["nom"], nom_template=donnees["template"]["NAME"],
                    client=s["mqtt"]["client"], ssid_ap=re_["AP"]["SSID"])


# ---- Persist ------------------------------------------------------------------------------------------------
def _substitue(valeur, v, secrets):
    if isinstance(valeur, dict):
        return {k: _substitue(x, v, secrets) for k, x in valeur.items()}
    if isinstance(valeur, list):
        return [_substitue(x, v, secrets) for x in valeur]
    if not isinstance(valeur, str):
        return valeur
    if valeur.startswith("@secret:"):
        return "***" if secrets is None else secrets[valeur[len("@secret:"):]]
    if valeur == "{{id}}":
        return v["id"]

    def remplace(m):
        if m.group(1) not in v:
            raise ValueError(f"gabarit inconnu dans le modele : {m.group(0)}")
        return str(v[m.group(1)])
    return GABARIT.sub(remplace, valeur)


def _pose(obj, chemin, valeur):
    cles = chemin.split(".")
    for c in cles[:-1]:
        if not isinstance(obj.get(c), dict):
            obj[c] = {}
        obj = obj[c]
    if valeur is None:
        obj.pop(cles[-1], None)
    else:
        obj[cles[-1]] = copy.deepcopy(valeur)


def blocs_coches(modele, r):
    """Ids des blocs coches (RTC -> ds3231), dans l'ordre du modele ; un id inconnu est ignore ici (coherence)."""
    voulus = set(r.blocs) | ({"ds3231"} if r.heure == "RTC" else set())
    return [b["id"] for b in modele["blocs"] if b["id"] in voulus]


def _blocs_permis(modele, r):
    coches = set(blocs_coches(modele, r))
    return [(b, b["id"] in coches) for b in modele["blocs"] if r.puce in b["puces"]]


def _vars_metier(v, metier):
    return dict(v, metier=metier, Metier=metier[:1].upper() + metier[1:])


def persist(modele, r, vars, secrets=None):
    """Le persist (dict, ordre des cles du socle) ; secrets=None -> "***" a la place de chaque mot de passe."""
    obj = _substitue(modele["socle"], vars, secrets)
    tables = [modele["roles"][r.role], modele["puces"][r.puce].get("ajouts", {})]
    tables += [b["actif"] if coche else b["inactif"] for b, coche in _blocs_permis(modele, r)]
    for table in tables:
        for chemin, valeur in table.items():
            _pose(obj, chemin, _substitue(valeur, vars, secrets))
    for metier in r.metiers:
        obj.setdefault("modules", {})[metier] = _substitue(modele["metier"]["gabarit"], _vars_metier(vars, metier),
                                                           secrets)
    return obj


def texte_persist(obj, eol):
    return json.dumps(obj, indent="\t", ensure_ascii=False).replace("\n", eol) + eol


# ---- Autoexec et listes du cenv --------------------------------------------------------------------------------
def _entrees(modele, r):
    """Entrees d'autoexec (socle, blocs coches et permis, metier principal), triees par (groupe, rang), stable."""
    entrees = list(modele["socle_autoexec"]["entrees"])
    for b, coche in _blocs_permis(modele, r):
        if coche:
            entrees += b["autoexec"]
    if r.metiers:
        mv = {"metier": r.metiers[0], "Metier": _vars_metier({}, r.metiers[0])["Metier"]}
        entrees += [_substitue(e, mv, None) for e in modele["metier"]["autoexec"]]
    for e in entrees:
        if e["groupe"] not in GROUPES:
            raise ValueError(f"groupe d'autoexec inconnu dans le modele : {e['groupe']!r}")
    return sorted(entrees, key=lambda e: (GROUPES.index(e["groupe"]), e["rang"]))


def _ligne(appel, modules, condition):
    if appel in ("compileSocle", "leds", "historique"):
        args = ""
    elif appel == "chargeFichier":
        args = ", ".join(json.dumps(x, ensure_ascii=False) for x in (modules[0], condition))
    else:
        args = json.dumps(modules, ensure_ascii=False)
        if condition is not None and appel != "importe":
            args += ", " + json.dumps(condition, ensure_ascii=False)
    return f"    demarrage.{appel}({args})"


def autoexec(modele, r):
    """Texte de l'autoexec.be (fins de ligne \\n) : entete du modele, prologue, appels, end."""
    lignes, groupe, prec = [], None, None
    for e in _entrees(modele, r):
        cle = (e["appel"], e["condition"], e["groupe"])
        if prec is not None and prec[0] == cle and e["appel"] != "chargeFichier":
            prec[1].extend(m for m in e["modules"] if m not in prec[1])
            continue
        if groupe is not None and e["groupe"] != groupe:
            lignes.append(None)
        groupe = e["groupe"]
        prec = (cle, list(dict.fromkeys(e["modules"])))
        lignes.append(prec)
    v = dict(_identite(r), env=_env(r))
    entete = [_substitue(x, v, None) for x in modele["socle_autoexec"]["entete"]]
    corps = ["" if x is None else _ligne(x[0][0], x[1], x[0][1]) for x in lignes]
    return "\n".join(entete + ["import demarrage", "if demarrage.prologue()"] + corps + ["end"]) + "\n"


def _fichiers_bloc(b):
    return set(b["solidify"]) | set(b["exclude_si_inactif"])


def listes_cenv(modele, r):
    """{"solidify": [...], "exclude": [...]} de la section cenv (voir l'en-tete)."""
    coches = set(blocs_coches(modele, r))
    solidify, requis, exclude = ["${berry_commun.socle}"], set(), []
    for b, coche in _blocs_permis(modele, r):
        if coche:
            solidify += [f for f in b["solidify"] if f not in solidify]
    for b in modele["blocs"]:
        if b["id"] in coches and r.puce in b["puces"]:
            requis |= _fichiers_bloc(b)
    for b in modele["blocs"]:
        if not (b["id"] in coches and r.puce in b["puces"]):
            exclude += [f for f in b["exclude_si_inactif"] if f not in requis and f not in exclude]
    return {"solidify": solidify, "exclude": exclude}


# ---- Coherence --------------------------------------------------------------------------------------------------
def _appels(texte):
    """[(appel, [modules], condition)] des lignes demarrage.* du texte (commentaires ignores)."""
    res = []
    for ligne in texte.splitlines():
        m = APPEL.match(ligne)
        if not m:
            continue
        chaines = re.findall(r'"([^"]*)"', m.group(2))
        if m.group(1) == "chargeFichier":
            res.append(("chargeFichier", chaines[:1], chaines[1] if len(chaines) > 1 else None))
        elif m.group(2).lstrip().startswith("["):
            liste, _, reste = m.group(2).partition("]")
            cond = re.findall(r'"([^"]*)"', reste)
            res.append((m.group(1), re.findall(r'"([^"]*)"', liste), cond[0] if cond else None))
        else:
            res.append((m.group(1), [], None))
    return res


def _en_flash(racine, solidify):
    """Fichiers de custom_berry_solidify, references ${section.option} developpees depuis le cenv."""
    ini, res = None, set()
    for valeur in solidify:
        ref = fbi.REFERENCE.match(valeur)
        if ref:
            ini = ini or fbi.lit_sections(racine)
            res |= {e.chemin for e in fbi._developpe(ini, ref.group(1), ref.group(2), [], set())}
        else:
            res.add(fbi.normalise(valeur))
    return res


def coherence(modele, r, obj, texte_autoexec, listes, racine=None):
    """Refus de coherence (liste vide = coherent), meme si le modele a ete mal edite :
      - bloc inconnu, ou non permis pour la puce (historique sur ESP32) ;
      - dependance d'un bloc coche non cochee ;
      - bloc coche dont un module manque a l'autoexec ;
      - module charge par l'autoexec present dans `exclude`, ou charge comme module solidifie (importe, charge,
        leds, historique) sans etre dans `solidify` (developpe depuis [berry_commun] du cenv de `racine`) ;
      - id different entre serveur.rangeExtender, serveur.udp, serveur.tcp et drivers.ModBus, ou id d'esclave < 1."""
    racine = RACINE if racine is None else Path(racine)
    refus, blocs = [], {b["id"]: b for b in modele["blocs"]}
    puce = modele["puces"].get(r.puce)
    coches = blocs_coches(modele, r)
    for i in [x for x in r.blocs if x not in blocs]:
        refus.append(f"bloc inconnu : {i}")
    for i in coches:
        b = blocs[i]
        if i == "historique" and puce is not None and not puce.get("historique"):
            refus.append(f"historique refuse sur {r.puce} (S3 et P4 seulement)")
        elif r.puce not in b["puces"]:
            refus.append(f"bloc {i} non permis sur {r.puce}")
        for dep in b["dependances"]:
            if dep not in coches:
                refus.append(f"bloc {i} : dependance {dep} non cochee")
    appels = _appels(texte_autoexec)
    charges = {m for _, mods, _ in appels for m in mods}
    for i in coches:
        if r.puce not in blocs[i]["puces"]:
            continue
        for e in blocs[i]["autoexec"]:
            for m in e["modules"] or [e["appel"]]:
                present = m in charges if e["modules"] else any(a == e["appel"] for a, _, _ in appels)
                if not present:
                    refus.append(f"bloc {i} actif mais {m} absent de l'autoexec")
    exclus, flash = set(map(fbi.normalise, listes["exclude"])), _en_flash(racine, listes["solidify"])
    for appel, mods, _ in appels:
        for m in mods + (EN_FLASH.get(appel) or []):
            fichier = f"data/fs/{m}.be"
            if fichier in exclus:
                refus.append(f"module {m} de l'autoexec exclu (custom_files_exclude)")
            if appel in EN_FLASH and fichier not in flash:
                refus.append(f"module {m} charge par demarrage.{appel} mais absent de la flash (custom_berry_solidify)")
    ids = [_sous(obj, c) for c in CHEMINS_ID]
    if len({json.dumps(i) for i in ids}) != 1 or not all(type(i) is int for i in ids):
        refus.append("id different entre serveur.rangeExtender, serveur.udp, serveur.tcp et drivers.ModBus : "
                     + ", ".join(map(str, ids)))
    elif r.role == "esclave" and ids[0] < 1:
        refus.append(f"id d'esclave invalide : {ids[0]} (1 au moins)")
    return list(dict.fromkeys(refus))


# ---- Squelettes -----------------------------------------------------------------------------------------------------
def squelettes(modele, metier):
    """{"controle<Metier>.be": texte, "<metier>Fonctions.be": texte} (fins de ligne \\n). ValueError si le nom
    n'est pas en camelCase [a-z][a-zA-Z0-9]* (il sert aux noms des fichiers, spec §5.6)."""
    if not NOM_METIER.match(metier or ""):
        raise ValueError(f"nom de fonction metier invalide : {metier!r} (camelCase, [a-z][a-zA-Z0-9]*)")
    v = _vars_metier({}, metier)
    m = modele["metier"]
    return {f"controle{v['Metier']}.be": "\n".join(_substitue(m["controle"], v, None)) + "\n",
            f"{metier}Fonctions.be": "\n".join(_substitue(m["fonctions"], v, None)) + "\n"}


def graphiques_initial():
    return json.dumps({"affichage": {}, "groupes": {}})
