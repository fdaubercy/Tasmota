"""Regroupement par BLOC du manifeste des fichiers d'un env, pour la page « Fichiers Berry par env » (lecture seule).

Le manifeste = la liste `blocs` de outils_docs/schemas/modele_persist.json (lue par verifie_manifeste, qui developpe
aussi les references `${berry_commun.x}`). Un fichier .be qui est dans un ou plusieurs blocs va dans le groupe de ces blocs :
deux blocs qui portent les memes fichiers (ruban et ledRGB : ledsFonctions + controleLeds) donnent UN groupe « ruban, ledRGB ».
Un fichier dans aucun bloc n'a pas de groupe : la page le range sous « Sans bloc » (socle, fichiers propres a la carte, amont).

Rien n'est ecrit, et seuls id, libelle, chemins .be et cout partent vers la page : jamais le reste du modele, qui porte des secrets.
La page insere les textes par textContent. Le JS de dessin des colonnes est ici (JS) : fichiers_berry_page.py reste sous 500 lignes.
Banc : test_fichiers_berry_blocs.py.
"""

import sys
from pathlib import Path

import verifie_manifeste as vm

DOSSIER_MESURE = Path(__file__).resolve().parents[1] / "berry"


def _cout_bloc(racine, fichiers):
    sys.path.insert(0, str(DOSSIER_MESURE))     # exception a la regle du meme dossier : mesure_binomes est dans berry/
    try:
        import mesure_binomes
    finally:
        sys.path.pop(0)
    return mesure_binomes.cout_bloc(racine, fichiers)


def groupes(racine):
    """[{"ids", "libelles", "fichiers" (chemins .be), "cout"}] dans l'ordre du manifeste ; `cout` = cout_bloc de TOUS les
    fichiers des blocs du groupe, ou None. [] si le manifeste ou le cenv est illisible : la page garde alors sa liste a plat."""
    try:
        blocs, listes = vm.lit_manifeste(racine), vm.lit_listes(racine)
    except (ValueError, OSError):
        return []
    par_bloc, _ = vm.fichiers_blocs(blocs, listes)
    libelle = {b["id"]: b.get("libelle") or b["id"] for b in blocs}
    appartient = {}                                   # fichier .be -> ids des blocs qui le portent, dans l'ordre du manifeste
    for b in blocs:
        for f in dict.fromkeys(par_bloc[b["id"]]):
            if f.endswith(".be"):
                appartient.setdefault(f, []).append(b["id"])
    res = {}
    for f, ids in appartient.items():
        g = res.setdefault(tuple(ids), {"ids": list(ids), "libelles": [libelle[i] for i in ids], "fichiers": []})
        g["fichiers"].append(f)
    try:
        for g in res.values():
            g["cout"] = _cout_bloc(racine, [f for i in g["ids"] for f in par_bloc[i]])
    except (OSError, ValueError):
        return []
    return list(res.values())


JS = r"""
// Colonne regroupee par bloc du manifeste : entrees = [{chemin, el}] ; sans etat.groupes, liste a plat comme avant.
function ko(x) { return x.toFixed(1).replace(".", ","); }
function coutBloc(c) {
  if (!c) return "coût non mesuré";
  return (c.solidifie ? ko(c.solidifie) + " Ko solidifié" : "non solidifiable") + ", " + ko(c.bec) + " Ko en .bec";
}
// Budget de RAM Berry de la puce (budget_ram_berry.pour_carte, champ budget de GET /etat) : ligne rouge s'il est depasse.
function avertitBudget(av) {
  var b = etat.budget;
  if (b && b.depasse) av.appendChild(h("div", {"class": "avert rouge", id: "budget-ram", texte: b.message}));
}
function remplitColonne(col, entrees) {
  var groupes = etat.groupes || [];
  if (!groupes.length) { entrees.forEach(function (e) { col.appendChild(e.el); }); return; }
  var vus = {};
  groupes.forEach(function (g) {
    var dedans = entrees.filter(function (e) { return g.fichiers.indexOf(e.chemin) >= 0; });
    dedans.forEach(function (e) { vus[e.chemin] = true; });
    if (!dedans.length) return;
    col.appendChild(h("div", {"class": "bloc-tete", title: g.libelles.join(", ")}, g.ids.join(", ") + " · " + coutBloc(g.cout)));
    dedans.forEach(function (e) { col.appendChild(e.el); });
  });
  var reste = entrees.filter(function (e) { return !vus[e.chemin]; });
  if (!reste.length) return;
  col.appendChild(h("div", {"class": "bloc-tete", texte: "Sans bloc"}));
  reste.forEach(function (e) { col.appendChild(e.el); });
}
"""
