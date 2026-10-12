r"""Genere le schema JSON des `_persist.json` des cartes ESP32 — par INFERENCE.

UTILISATION
-----------
  python genere_schema_persist.py                  genere outils_docs/schemas/persist.schema.json
                                                   et affiche le rapport des incoherences
  python genere_schema_persist.py --rapport r.txt  ecrit aussi le rapport dans r.txt
  python genere_schema_persist.py --sortie s.json  autre destination pour le schema
  python genere_schema_persist.py --valide [f ...] valide des persists contre le schema
                                                   (sans fichier : tous ceux du depot) ;
                                                   code de sortie 1 s'il y a des erreurs

A QUOI SERT LE SCHEMA
---------------------
Branche dans les reglages VS Code (`json.schemas` sur `data/**/_persist.json`), il donne
l'autocompletion et SOULIGNE : (a) une cle presente dans les autres cartes mais absente
ici, (b) une valeur du mauvais type, (c) une faute dans un vocabulaire ferme
("On" au lieu de "ON", "debug " au lieu de "debug"...).
Ce script ne touche PAS aux reglages VS Code et n'ecrit rien sous data/.

REGLE `required` (cles fixes)
-----------------------------
Une cle est `required` dans son objet parent si elle est presente dans AU MOINS 50 % des
exemplaires de ce parent ET dans au moins 2 exemplaires. Les « exemplaires » sont les
objets parents rencontres dans les persists (un par fichier, ou un par bloc pour un
dictionnaire a cles variables). Le rapport liste chaque cle « presente dans X sur Y »
quand X < Y, requise ou non, avec les cartes ou elle manque.
Cela traduit la regle du 2026-10-06 : une nouvelle cle s'ajoute a CHAQUE persist qui
porte le bloc concerne.

EXCEPTIONS A `required`
-----------------------
  - Enfants directs de `drivers`, `modules`, `environnement` : leur presence depend du
    materiel de la carte (Ethernet, ADS1115...), jamais requis (le rapport les marque
    « bloc materiel »). Leurs cles INTERNES, elles, suivent la regle.
  - Sous-schemas FUSIONNES (blocs de dictionnaire variable, groupes a suffixe numerique,
    et tout ce qui en descend) : requis seulement si presente dans 100 % des exemplaires
    (>= 2), car on y melange des blocs de natures differentes (ledLink n'a pas d'id).

DICTIONNAIRES A CLES VARIABLES (jamais de `required` sur leurs cles)
--------------------------------------------------------------------
  - cles qui ne different que par un suffixe numerique (pinsI2S1, pinsI2S2... ;
    TasmotaSlaveModBus / TasmotaSlaveModBus1) : `patternProperties` `^racine\d*$`,
    des que leur presence varie d'un exemplaire a l'autre (ou si elles sont 4 ou plus) ;
  - objets dont les valeurs-objets ont la meme forme (>= 3 valeurs, ressemblance moyenne
    des jeux de cles >= 0.7) ET dont les cles ne sont pas les memes partout (noms de
    modules, de peripheriques...) : `additionalProperties` avec un sous-schema fusionne.
En cas de doute : pas de `required`.

VOCABULAIRES FERMES (`enum` seulement si TOUTES les valeurs observees y sont)
-----------------------------------------------------------------------------
  - `activation` : ON / OFF (et toute cle dont les valeurs observees sont toutes ON/OFF) ;
  - `log`, `general` : seuils de module de data/fs/logFonctions.be
    (erreur, info, debug, detail) ;
  - `serie`, `web`, `mqtt`, `syslog` sous `profils` : seuils de sortie
    (aucun, erreur, info, debug, detail).
Une valeur hors vocabulaire dans les donnees n'est pas imposee : elle est signalee.

TYPES
-----
Une cle de types differents selon les fichiers recoit un tableau de types et le rapport
le signale. `additionalProperties` reste autorise partout sur les objets fixes.

PREREQUIS
---------
Python 3.8+, bibliotheque standard seule (le validateur integre couvre type, enum,
required, properties, patternProperties, additionalProperties, items).
"""
import argparse
import json
import re
import subprocess
import sys
from itertools import combinations
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
SCHEMA_DEFAUT = RACINE / "outils_docs" / "schemas" / "persist.schema.json"
SEUIL_REQUIS = 0.5     # part minimale d'exemplaires du parent portant la cle
MIN_REQUIS = 2         # et nombre minimal d'exemplaires
SEUIL_FORME = 0.7      # ressemblance moyenne pour un dictionnaire de blocs de meme forme
BLOCS_MATERIEL = ("drivers", "modules", "environnement")   # enfants nommes par le materiel : jamais requis

NIVEAUX_MODULE = ["erreur", "info", "debug", "detail"]
NIVEAUX_SORTIE = ["aucun", "erreur", "info", "debug", "detail"]
ON_OFF = ["ON", "OFF"]
SORTIES = ("serie", "web", "mqtt", "syslog")

DESCRIPTIONS = {
    "activation": "ON ou OFF : active ou non ce bloc.",
    "log": "Seuil de log du module : erreur, info, debug ou detail (charte data/fs/logFonctions.be).",
    "general": "Seuil de log de la cible 'general' : erreur, info, debug ou detail.",
    "profil": "Nom du profil de logs actif (cle de `profils`).",
    "profils": "Profils de logs : seuil de chaque sortie (serie, web, mqtt, syslog).",
    "nbLogsFiles": "Nombre de fichiers de log conserves.",
    "name": "Nom d'affichage du bloc.",
    "reglage": "Reglage libre du bloc (ON/OFF le plus souvent).",
    "id": "Identifiant ModBus / reseau de la carte.",
    "pin": "Numero de GPIO (-1 = non affecte).",
    "environnement": "Peripheriques et broches du bloc (cles variables selon la carte).",
    "telePeriod": "Periode de telemetrie en secondes.",
    "debit": "Debit (bauds).",
    "template": "Template Tasmota de la carte.",
    "mdp": "Mot de passe.",
}


# --------------------------------------------------------------------- lecture
def liste_persists():
    """Persists suivis par git (hors dossiers « sauvegarde »), chemins absolus."""
    try:
        sortie = subprocess.check_output(["git", "ls-files"], cwd=RACINE).decode("utf-8")
        noms = [n for n in sortie.splitlines()]
    except Exception:
        noms = [str(p.relative_to(RACINE)).replace("\\", "/") for p in RACINE.glob("data/**/_persist.json")]
    return [RACINE / n for n in noms if n.endswith("_persist.json") and "sauvegarde" not in n.lower()]


def charge(chemin):
    with open(chemin, encoding="utf-8-sig") as f:
        return json.load(f)


def nom_carte(chemin):
    return Path(chemin).parent.name


# ------------------------------------------------------------------- inference
def type_json(v):
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, int):
        return "integer"
    if isinstance(v, float):
        return "number"
    if isinstance(v, str):
        return "string"
    if v is None:
        return "null"
    return "array" if isinstance(v, list) else "object"


def racine_cle(cle):
    return re.sub(r"\d+$", "", cle)


def ressemblance(jeux):
    """Moyenne des Jaccard de tous les couples de jeux de cles."""
    couples = list(combinations(jeux, 2))
    if not couples:
        return 1.0
    return sum((len(a & b) / len(a | b)) if (a | b) else 1.0 for a, b in couples) / len(couples)


def liste_cartes(labels, limite=6):
    u = sorted(set(labels))
    return ", ".join(u[:limite]) + (f" (+{len(u) - limite})" if len(u) > limite else "")


class Inference:
    def __init__(self):
        self.rapport = []   # (categorie, texte)

    def note(self, categorie, texte):
        self.rapport.append((categorie, texte))

    # instances : liste de (etiquette, valeur)
    def infere(self, instances, chemin, cle, parent_cle=None, strict=False):
        types = {type_json(v) for _, v in instances}
        if "integer" in types and "number" in types:
            types.discard("integer")
        schema = {}
        ordre = ["null", "boolean", "integer", "number", "string", "array", "object"]
        tri = [t for t in ordre if t in types]
        schema["type"] = tri[0] if len(tri) == 1 else tri
        if len(tri) > 1:
            detail = "; ".join(f"{t}: {liste_cartes([e for e, v in instances if type_json(v) == t or (t == 'number' and type_json(v) == 'integer')])}"
                               for t in tri)
            self.note("TYPES", f"{chemin or '(racine)'} : types differents selon les fichiers ({detail})")
        if cle in DESCRIPTIONS and cle != "name":
            schema["description"] = DESCRIPTIONS[cle]
        elif cle == "name":
            schema["description"] = DESCRIPTIONS["name"]
        chaines = [v for _, v in instances if isinstance(v, str)]
        if chaines:
            self.enum(schema, instances, chaines, chemin, cle, parent_cle)
        objets = [(e, v) for e, v in instances if isinstance(v, dict)]
        if objets:
            self.objet(schema, objets, chemin, cle, strict)
        tableaux = [(e, v) for e, v in instances if isinstance(v, list)]
        if tableaux:
            elems = [(e, x) for e, v in tableaux for x in v]
            if elems:
                schema["items"] = self.infere(elems, chemin + "[]", None, strict=strict)
        return schema

    def enum(self, schema, instances, chaines, chemin, cle, parent_cle):
        vocab = None
        if cle == "activation":
            vocab = ON_OFF
        elif cle in ("log", "general"):
            vocab = NIVEAUX_MODULE
        elif cle in SORTIES and "profils" in chemin.split("."):
            vocab = NIVEAUX_SORTIE
        elif cle and len(chaines) >= 2 and set(chaines) <= set(ON_OFF) and len(chaines) == len(instances):
            vocab = ON_OFF
        if vocab is None:
            return
        hors = sorted({v for v in chaines if v not in vocab})
        if hors:
            fautifs = [e for e, v in instances if isinstance(v, str) and v in hors]
            self.note("ENUM", f"{chemin} : valeurs hors vocabulaire {hors} (attendu {vocab}) dans {liste_cartes(fautifs)} -> enum NON impose")
        else:
            schema["enum"] = vocab

    def objet(self, schema, objets, chemin, cle_parent, strict):
        n = len(objets)
        cles = {}   # cle -> [(etiquette, valeur)]
        for e, d in objets:
            for k, v in d.items():
                cles.setdefault(k, []).append((e, v))
        fixes = dict(cles)
        schema_pp, additional = {}, None

        # 1. blocs de meme forme a cles variables (noms de modules, de peripheriques)
        blocs = [k for k, lst in cles.items() if all(isinstance(v, dict) for _, v in lst)]
        if len(blocs) >= 3 and any(len(cles[k]) < n for k in cles):
            jeux = [frozenset(v.keys()) for k in blocs for _, v in cles[k]]
            if ressemblance(jeux) >= SEUIL_FORME:
                inst = [(f"{e}:{k}", v) for k in blocs for e, v in cles[k]]
                additional = self.infere(inst, chemin + ".*", None, strict=True)
                self.note("DICO", f"{chemin or '(racine)'} : dictionnaire de blocs de meme forme (cles : {', '.join(blocs)})")
                for k in blocs:
                    fixes.pop(k)

        # 2. cles qui ne different que par un suffixe numerique
        if additional is None:
            groupes = {}
            for k in fixes:
                groupes.setdefault(racine_cle(k), []).append(k)
            for rac, ks in groupes.items():
                if len(ks) < 2 or not any(re.search(r"\d$", k) for k in ks):
                    continue
                presences = {frozenset(k for k in ks if k in d) for _, d in objets}
                if len(presences) > 1 or len(ks) >= 4:
                    inst = [x for k in ks for x in cles[k]]
                    schema_pp[f"^{re.escape(rac)}\\d*$"] = self.infere(inst, f"{chemin}.{rac}*", None, strict=True)
                    self.note("DICO", f"{chemin or '(racine)'} : cles a suffixe numerique {rac}* ({', '.join(sorted(ks))})")
                    for k in ks:
                        fixes.pop(k)

        props, requis = {}, []
        for k, lst in fixes.items():
            chem = f"{chemin}.{k}" if chemin else k
            props[k] = self.infere(lst, chem, k, parent_cle=cle_parent, strict=strict)
            x = len(lst)
            seuil = 1.0 if strict else SEUIL_REQUIS
            if cle_parent not in BLOCS_MATERIEL and x * 1.0 / n >= seuil and x >= MIN_REQUIS:
                requis.append(k)
            if x < n:
                manque = [e for e, d in objets if k not in d]
                statut = "REQUIS" if k in requis else ("bloc materiel" if cle_parent in BLOCS_MATERIEL else "optionnel")
                self.note("MANQUE", f"{chem} : presente dans {x} exemplaire(s) sur {n} [{statut}]"
                                    + (f" ; absente de : {liste_cartes(manque)}" if manque else ""))
        if props:
            schema["properties"] = props
        if requis:
            schema["required"] = requis
        if schema_pp:
            schema["patternProperties"] = schema_pp
        schema["additionalProperties"] = additional if additional is not None else True


def genere(persists):
    inf = Inference()
    instances = [(nom_carte(p), charge(p)) for p in persists]
    corps = inf.infere(instances, "", None)
    schema = {"$schema": "http://json-schema.org/draft-07/schema#",
              "title": "Persist des cartes ESP32 (fork Tasmota)",
              "description": ("Genere par outils_docs/scripts_python/berry/genere_schema_persist.py a partir de "
                              f"{len(persists)} persists. Cle `required` si presente dans >= 50 % des exemplaires "
                              "du parent et au moins 2. Ne pas editer a la main : regenerer.")}
    schema.update(corps)
    return schema, inf.rapport


def texte_rapport(rapport, persists):
    titres = {"TYPES": "Types differents selon les fichiers", "ENUM": "Valeurs hors vocabulaire",
              "MANQUE": "Cles absentes de certaines cartes (X < Y)", "DICO": "Objets traites comme dictionnaires a cles variables"}
    lignes = [f"Persists lus ({len(persists)}) :"] + [f"  - {p.relative_to(RACINE).as_posix()}" for p in persists]
    for cat in ("MANQUE", "ENUM", "TYPES", "DICO"):
        items = sorted(t for c, t in rapport if c == cat)
        lignes += ["", f"== {titres[cat]} ({len(items)}) =="] + (["  " + t for t in items] or ["  (aucun)"])
    return "\n".join(lignes)


# ------------------------------------------------------------------ validateur
TYPES_PY = {"string": str, "boolean": bool, "array": list, "object": dict, "null": type(None)}


def verifie_type(v, t):
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, TYPES_PY[t])  # un bool n'est ni str, ni list, ni dict : pas d'ambiguite


def valide(v, s, chemin="$"):
    """Generateur d'erreurs (texte). Sous-ensemble de draft-07 suffisant pour ce schema."""
    t = s.get("type")
    if t is not None:
        ts = t if isinstance(t, list) else [t]
        if not any(verifie_type(v, x) for x in ts):
            yield f"{chemin} : type {type_json(v)} (attendu {'/'.join(ts)})"
            return
    if "enum" in s and v not in s["enum"]:
        yield f"{chemin} : valeur {v!r} hors de {s['enum']}"
    if isinstance(v, dict):
        for k in s.get("required", []):
            if k not in v:
                yield f"{chemin} : cle requise manquante '{k}'"
        props, pats, add = s.get("properties", {}), s.get("patternProperties", {}), s.get("additionalProperties", True)
        for k, val in v.items():
            vus = False
            if k in props:
                vus = True
                yield from valide(val, props[k], f"{chemin}.{k}")
            for pat, sub in pats.items():
                if re.search(pat, k):
                    vus = True
                    yield from valide(val, sub, f"{chemin}.{k}")
            if not vus:
                if add is False:
                    yield f"{chemin} : cle non autorisee '{k}'"
                elif isinstance(add, dict):
                    yield from valide(val, add, f"{chemin}.{k}")
    if isinstance(v, list) and "items" in s:
        for i, x in enumerate(v):
            yield from valide(x, s["items"], f"{chemin}[{i}]")


# ------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description="Genere / applique le schema des _persist.json (voir l'en-tete du script).")
    ap.add_argument("--sortie", default=str(SCHEMA_DEFAUT), help="fichier schema (defaut : outils_docs/schemas/persist.schema.json)")
    ap.add_argument("--rapport", help="ecrit aussi le rapport dans ce fichier")
    ap.add_argument("--valide", nargs="*", metavar="FICHIER", help="valide ces persists (sans valeur : tous) au lieu de generer")
    a = ap.parse_args()
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if a.valide is not None:
        schema = json.loads(Path(a.sortie).read_text(encoding="utf-8"))
        fichiers = [Path(f) for f in a.valide] or liste_persists()
        total = 0
        for f in fichiers:
            erreurs = list(valide(charge(f), schema))
            total += len(erreurs)
            print(f"{'OK ' if not erreurs else 'KO '} {f.parent.name} : {len(erreurs)} erreur(s)")
            for e in erreurs:
                print("     " + e)
        return 1 if total else 0

    persists = liste_persists()
    if not persists:
        print("Aucun _persist.json trouve.", file=sys.stderr)
        return 2
    schema, rapport = genere(persists)
    sortie = Path(a.sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    txt = texte_rapport(rapport, persists)
    print(txt)
    print(f"\nSchema ecrit : {sortie} ({sortie.stat().st_size} octets)")
    if a.rapport:
        Path(a.rapport).write_text(txt + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
