"""Ecriture de l'ecran d'une carte dans le depot (plan atelier-ecrans A8, spec § 5.5).

Une description, trois fichiers ecrits ensemble : `outils_docs/atelier_ecrans/cartes/<env>/ecran.json`, et dans le
dossier de la carte `pages.jsonl` (HASPmota) et `ecranLvgl.be` (LVGL pur) ; `build/interface_ecran.py` reste seul juge
de ce qui part sur le FS. Ordre : `prevu` (diff + empreinte des fichiers lus) puis `ecrit` (refus si un build tourne,
si un fichier a change depuis le diff, ou si ecran.json a change depuis le chargement de la page), en une
`fichiers_berry_sauvegarde.Transaction` (atomique, copie horodatee).
"""
import hashlib

import atelier_ecrans_catalogue as cat
import atelier_ecrans_description as aed
import atelier_ecrans_haspmota as ah
import atelier_ecrans_lvgl as al
import atelier_graphiques_televerse as agt
import fichiers_berry_etat as fbe
import fichiers_berry_sauvegarde as fbs
import fichiers_berry_ini as fbi
from pathlib import Path

INTERFACE = "custom_interface_ecran"


def _texte(octets):
    return None if octets is None else octets.decode("utf-8", errors="replace")


def _lit(racine, rel):
    p = Path(racine) / rel
    return p.read_bytes() if p.is_file() else None


def chemins(env):
    dossier = fbe.dossier_carte(env)
    return {"ecran.json": f"{aed.DOSSIER}/{env}/ecran.json", "pages.jsonl": f"{dossier}/pages.jsonl",
            "ecranLvgl.be": f"{dossier}/ecranLvgl.be"}


def erreurs(desc, catalogue):
    """Messages du validateur ; une description de forme inattendue (listes, cles absentes) donne un message, pas une exception."""
    try:
        return aed.valide(desc, catalogue)
    except (AttributeError, TypeError, KeyError, ValueError) as e:
        return [f"description mal formee : {type(e).__name__} : {e}"]


def generes(desc, catalogue):
    """{nom: octets} des trois fichiers ; ValueError si la description est refusee par le validateur ou le generateur."""
    erreurs_ = erreurs(desc, catalogue)
    if erreurs_:
        raise ValueError("description refusee : " + " ; ".join(erreurs_[:5]))
    return {"ecran.json": aed.texte(desc).encode("utf-8"), "pages.jsonl": ah.genere(desc, catalogue).encode("utf-8"),
            "ecranLvgl.be": al.genere(desc, catalogue).encode("utf-8")}


def empreinte(lus):
    h = hashlib.sha256()
    for rel in sorted(lus):
        h.update(rel.encode("utf-8") + b"\0" + (b"-" if lus[rel] is None else hashlib.sha256(lus[rel]).digest()))
    return h.hexdigest()


def _calcule(racine, env, desc, extra=None):
    """(lus, apres) : fichiers lus (rel -> octets | None) et fichiers a ecrire (seulement ceux qui changent)."""
    if not isinstance(desc, dict):
        raise ValueError("description : objet attendu")
    noms = chemins(env)
    apres = {noms[n]: o for n, o in generes(desc, cat.charge(racine)).items()}
    apres.update(extra or {})
    lus = {rel: _lit(racine, rel) for rel in apres}
    for rel, avant in lus.items():           # core.autocrlf : garder les fins de ligne du fichier deja la
        if avant is not None and b"\r\n" in avant and b"\r\n" not in apres[rel]:
            apres[rel] = apres[rel].replace(b"\n", b"\r\n")
    return lus, {rel: o for rel, o in apres.items() if lus[rel] != o}


def prevu(racine, env, desc, extra=None):
    """{"fichiers": [{"rel", "avant", "apres"}] (fichiers qui changent), "empreinte"} : rien n'est ecrit."""
    lus, apres = _calcule(racine, env, desc, extra)
    return {"fichiers": [{"rel": rel, "avant": _texte(lus[rel]), "apres": _texte(apres[rel])} for rel in sorted(apres)],
            "empreinte": empreinte(lus)}


def refuse_build(builds_en_cours):
    builds = builds_en_cours()
    if builds is None:
        raise RuntimeError("impossible de savoir si un build tourne : ecriture refusee")
    if builds:
        raise RuntimeError("un build est en cours (" + ", ".join(builds) + ") : ecriture refusee")


def ecrit(racine, env, desc, empreinte_lue, empreinte_description, builds_en_cours, extra=None, nature="atelier-ecrans"):
    """{"ecrits": [rel...], "empreinte_description"} ; RuntimeError (rien n'est ecrit) : build en cours, fichiers changes
    depuis `prevu`, ecran.json change depuis le chargement de la page (`empreinte_description`, None = absent alors)."""
    refuse_build(builds_en_cours)
    rel_desc = chemins(env)["ecran.json"]
    actuel = _lit(racine, rel_desc)
    if (None if actuel is None else aed.empreinte(actuel)) != empreinte_description:
        raise RuntimeError("ecran.json modifie sur le disque depuis le chargement de la page : recharger la carte, rien n'est ecrit")
    lus, apres = _calcule(racine, env, desc, extra)
    if empreinte(lus) != empreinte_lue:
        raise RuntimeError("fichiers modifies depuis le diff : refaire le diff, rien n'est ecrit")
    if apres:
        for rel in apres:                    # carte sans ecran.json encore : son dossier de l'atelier
            (Path(racine) / rel).parent.mkdir(parents=True, exist_ok=True)
        with fbs.Transaction(racine, nature) as tr:
            for rel in sorted(apres):
                tr.ecrit(rel, apres[rel])
    nouveau = _lit(racine, rel_desc)
    return {"ecrits": sorted(apres), "empreinte_description": None if nouveau is None else aed.empreinte(nouveau)}


def interface(racine, env):
    ini = fbi.lit_sections(racine)
    section = ini.definie_dans(env, INTERFACE)
    morceaux = ini.sections[section][INTERFACE].morceaux if section else []
    return (morceaux[0][1].strip() or None) if morceaux else None


def url_build(racine, env):
    """Lien vers la page Build (onglet Fichiers) avec le fichier de l'interface envoyee ; les deux si elle est inconnue."""
    i = interface(racine, env)
    fichiers = ["pages.jsonl"] if i == "haspmota" else ["ecranLvgl.be"] if i == "lvgl" else ["pages.jsonl", "ecranLvgl.be"]
    return agt.url(env, fichiers, True)
