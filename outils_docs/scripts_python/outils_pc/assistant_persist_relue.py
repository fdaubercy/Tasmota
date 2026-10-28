"""Bouton « Relue » de la page Assistant persist : retire UN chemin de a_completer du modele (diff + empreinte + ecriture,
comme la mise a jour du modele). Sorti de assistant_persist_modele.py pour rester sous 500 lignes."""

import copy
import json

import assistant_persist_modele as apm


# ---- « Relue » : retire UN chemin de a_completer (meme schema que la mise a jour : diff, empreinte, ecriture) -------
def valeur_affichee(modele, chemin):
    """Defaut du modele pour un chemin a completer, en texte ; "***" s'il porte un secret ; "" si introuvable."""
    cle = tuple(c.replace("#", "1") for c in chemin.split("."))
    cherche = [(modele["metier"]["gabarit"], cle[2:])] if cle[:2] == ("modules", "*") else [(modele["socle"], cle)]
    cherche += [(p.get("ajouts", {}), (".".join(cle),)) for p in modele.get("puces", {}).values()]
    for arbre, suite in cherche:
        try:
            valeur = apm._sous(arbre, suite)
        except (KeyError, TypeError):
            continue
        return "***" if apm.porte_secret(valeur) else json.dumps(valeur, ensure_ascii=False)
    return ""


def _relue(racine, chemin):
    "(neuf, diff, empreinte) : modele sans `chemin` dans a_completer ; ValueError (-> 400) s'il n'y est pas."
    modele = apm.charge_modele(racine)
    if not isinstance(chemin, str) or chemin not in apm.a_completer(modele):
        raise ValueError(f"cle a completer inconnue : {chemin!r}")
    neuf = copy.deepcopy(modele)
    neuf["a_completer"].remove(chemin)
    return (neuf,) + apm._diff(racine, modele, neuf)


def propose_relue(racine, chemin):
    "{diff, empreinte} du retrait de `chemin` de a_completer. Rien n'est ecrit."
    return dict(zip(("diff", "empreinte"), _relue(racine, chemin)[1:]))


def applique_relue(racine, chemin, empreinte):
    "Ecrit le retrait si l'empreinte est celle du diff vu ; RuntimeError (-> 409) sinon."
    neuf, _, attendue = _relue(racine, chemin)
    if empreinte != attendue:
        raise RuntimeError("le modele a change depuis le diff : refaire « Relue »")
    apm.ecrit_modele(racine, neuf, apm.NATURE_MAJ)
    return {"applique": True, "relue": chemin}
