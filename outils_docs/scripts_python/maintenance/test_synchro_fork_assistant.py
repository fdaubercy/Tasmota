"""Banc de l'analyse de l'assistant de synchro du fork (synchro_fork_assistant.py). Code de sortie 0 = vert.

Chaque cas travaille sur un FAUX depot (faux_depot_synchro : amont et origin nus, clone de travail) dans un
dossier temporaire : jamais le vrai depot, jamais le reseau.
Cas : a jour, avance seule, non pousses seuls, retard sans recouvrement, deux cotes sans conflit, conflit,
non pousses imposant la voie B, arbre sale classe, autre branche, fetch impossible, adaptateur de commits,
trois voies hors liste, une seule etape courante.
Temoin : une analyse qui ignore `non_pousses` dans la regle de voie DOIT faire echouer `non_pousses_force_b`.
"""

import sys
import tempfile
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import faux_depot_synchro as fd  # noqa: E402
import synchro_fork_assistant as asst  # noqa: E402

ECHECS = []
LIGNES = [f"ligne {i}\n" for i in range(1, 11)]


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def commun_ligne(n, texte):
    """Contenu de commun.txt dont la ligne n (1..10) est remplacee."""
    lignes = list(LIGNES)
    lignes[n - 1] = texte + "\n"
    return "".join(lignes)


def ids(a):
    return [e["id"] for e in a["etapes"]]


def nb_courantes(a):
    return sum(1 for e in a["etapes"] if e["statut"] == "courante")


MODELE = {}


def un_cas(nom, preparation, controle):
    """Copie du faux depot modele -> preparation(dossier, travail) -> analyse -> controle(a, travail)."""
    with tempfile.TemporaryDirectory() as tmp:
        dossier = Path(tmp)
        travail = fd.copie(MODELE["dossier"], dossier)
        preparation(dossier, travail)
        a = asst.analyse(travail, fetch=True)
        controle(a, travail)
        verifie(nb_courantes(a) <= 1, True, f"{nom} : au plus une etape courante")


def a_jour(d, t):
    pass


def c_a_jour(a, t):
    verifie((a["voie"], a["etapes"], a["erreur"]), ("", [], ""), "a_jour : voie vide, aucune etape")


def avance_seule(d, t):
    fd.commit_local(t, {"b.txt": "b\n"}, "local")
    fd.git(t, "push", "-q", "origin", "development")


def c_avance_seule(a, t):
    verifie((a["retard"], a["non_pousses"], a["etapes"]), (0, 0, []), "avance_seule : retard 0, rien a pousser")


def non_pousses_seuls(d, t):
    fd.commit_local(t, {"b.txt": "b\n"}, "local")


def c_non_pousses_seuls(a, t):
    verifie(ids(a), ["pousser"], "non_pousses_seuls : seule l'etape pousser")
    verifie(a["etapes"][0]["statut"], "courante", "non_pousses_seuls : pousser est courante")


def retard_sans_recouvrement(d, t):
    fd.commit_amont(d, {"a.txt": "a2\n"}, "amont a")


def c_retard_sans_recouvrement(a, t):
    verifie(a["voie"], "A", "retard_sans_recouvrement : voie A")
    verifie(a["touches_deux"], [], "retard_sans_recouvrement : rien des deux cotes")
    verifie(a["prevision"], {"possible": True, "conflits": []}, "retard_sans_recouvrement : prevision propre")
    verifie(a["touches_amont"], ["a.txt"], "retard_sans_recouvrement : touche par l'amont")
    verifie(ids(a), ["nouveautes", "prevision", "synchro_a"], "retard_sans_recouvrement : etapes")
    verifie([e["statut"] for e in a["etapes"]], ["faite", "faite", "courante"],
            "retard_sans_recouvrement : statuts (infos faites, synchro_a courante)")


def deux_cotes_sans_conflit(d, t):
    fd.commit_amont(d, {"commun.txt": commun_ligne(1, "amont")}, "amont l1")
    fd.commit_local(t, {"commun.txt": commun_ligne(5, "local")}, "local l5")
    fd.git(t, "push", "-q", "origin", "development")


def c_deux_cotes_sans_conflit(a, t):
    verifie(a["touches_deux"], ["commun.txt"], "deux_cotes_sans_conflit : touches_deux")
    verifie(a["prevision"]["conflits"], [], "deux_cotes_sans_conflit : pas de conflit")
    verifie(a["voie"], "A", "deux_cotes_sans_conflit : voie A")
    verifie("deux_cotes" in ids(a), True, "deux_cotes_sans_conflit : etape deux_cotes presente")
    verifie([e["statut"] for e in a["etapes"] if e["id"] == "deux_cotes"], ["faite"],
            "deux_cotes_sans_conflit : informative (faite)")


def conflit(d, t):
    fd.commit_amont(d, {"commun.txt": commun_ligne(3, "amont")}, "amont l3")
    fd.commit_local(t, {"commun.txt": commun_ligne(3, "local")}, "local l3")
    fd.git(t, "push", "-q", "origin", "development")


def c_conflit(a, t):
    verifie(a["prevision"]["conflits"], ["commun.txt"], "conflit : fichier en conflit")
    verifie(a["voie"], "B", "conflit : voie B")
    verifie("fusion_b" in ids(a) and "synchro_a" not in ids(a), True, "conflit : fusion_b et pas synchro_a")


def non_pousses_force_b(d, t):
    fd.commit_amont(d, {"a.txt": "a2\n"}, "amont a")
    fd.commit_local(t, {"b.txt": "b\n"}, "local non pousse")


def c_non_pousses_force_b(a, t):
    verifie(a["prevision"]["conflits"], [], "non_pousses_force_b : sans conflit")
    verifie(a["voie"], "B", "non_pousses_force_b : voie B malgre l'absence de conflit")
    verifie(ids(a)[-2:], ["fusion_b", "pousser"], "non_pousses_force_b : fusion_b puis pousser")
    verifie([e["statut"] for e in a["etapes"] if e["id"] == "pousser"], ["attente"],
            "non_pousses_force_b : pousser en attente")


def arbre_sale(d, t):
    fd.commit_amont(d, {"a.txt": "a2\n"}, "amont a")
    (t / "a.txt").write_text("modif locale\n", encoding="utf-8")
    (t / "tasmota").mkdir()
    fd.commit_local(t, {"tasmota/user_config_override.h": "x\n"}, "ajoute le .h")
    fd.git(t, "push", "-q", "origin", "development")
    (t / "tasmota" / "user_config_override.h").write_text("y\n", encoding="utf-8")
    (t / "intrus.txt").write_text("non suivi\n", encoding="utf-8")


def c_arbre_sale(a, t):
    par_chemin = {f["chemin"]: f for f in a["fichiers"]}
    verifie(par_chemin["a.txt"]["classe"], "amont", "arbre_sale : a.txt touche par l'amont")
    verifie(par_chemin["tasmota/user_config_override.h"]["build"], True, "arbre_sale : fichier reecrit par le build")
    verifie(par_chemin["tasmota/user_config_override.h"]["classe"], "libre", "arbre_sale : classe libre")
    verifie(a["non_suivis"], 1, "arbre_sale : un non suivi compte, non liste")
    statuts = {e["id"]: e["statut"] for e in a["etapes"]}
    verifie(statuts["arbre"], "courante", "arbre_sale : etape arbre courante")
    verifie(statuts["synchro_a"], "attente", "arbre_sale : synchro_a en attente")


def autre_branche(d, t):
    fd.git(t, "switch", "-q", "-c", "essai")


def c_autre_branche(a, t):
    verifie(a["branche"], "essai", "autre_branche : branche lue")
    verifie("branche" in ids(a), True, "autre_branche : etape branche presente")


def fetch_impossible(d, t):
    fd.git(t, "remote", "set-url", "upstream", str(d / "n_existe_pas.git"))


def c_fetch_impossible(a, t):
    verifie(a["erreur"] != "", True, "fetch_impossible : erreur renseignee")
    verifie([i for i in ids(a) if i in ("synchro_a", "fusion_b", "pousser")], [],
            "fetch_impossible : aucune etape modifiante")


def accents_et_espaces(d, t):
    fd.commit_amont(d, {fd.FICHIER_ACCENT: "x2\n"}, "amont accent")
    fd.commit_local(t, {fd.FICHIER_ACCENT: "x3\n"}, "local accent")


def c_accents_et_espaces(a, t):
    verifie(a["touches_amont"], [fd.FICHIER_ACCENT], "accents : chemin accentue lu en clair (amont)")
    verifie(a["touches_deux"], [fd.FICHIER_ACCENT], "accents : chemin accentue lu en clair (deux cotes)")


def commits_adaptateur(d, t):
    fd.commit_amont(d, {"a.txt": "a2\n"}, "Berry: fix")
    fd.commit_amont(d, {"a.txt": "a3\n"}, "Rien de special")


def c_commits_adaptateur(a, t):
    c = asst.commits_locaux(t)
    verifie([x[1] for x in c], ["Berry: fix", "Rien de special"], "commits_adaptateur : ordre d'arrivee")
    verifie("berry" in c[0][2], True, "commits_adaptateur : mot saillant berry")
    verifie((len(c[0][0]), c[1][2]), (9, []), "commits_adaptateur : sha court, pas de mot")
    verifie([x["saillant"] for x in a["commits"]], [True, False], "commits_adaptateur : drapeau saillant")


def journal(d, t):
    fd.commit_local(t, {"outils_docs/HISTORIQUE_SYNCHRO_FORK.md": "j\n"}, "journal")
    fd.git(t, "push", "-q", "origin", "development")
    (t / "outils_docs" / "HISTORIQUE_SYNCHRO_FORK.md").write_text("j2\n", encoding="utf-8")


def c_journal2(a, t):
    verifie(a["journal_modifie"], True, "journal : modifie")
    verifie(ids(a), ["journal"], "journal : etape journal seule")
    verifie(a["fichiers"], [], "journal : exclu de la liste des fichiers")


def trois_voies(d, t):
    fd.commit_amont(d, {"commun.txt": commun_ligne(3, "amont")}, "amont l3")
    fd.commit_local(t, {"commun.txt": commun_ligne(3, "local")}, "local l3")


def c_trois_voies(a, t):
    try:
        asst.trois_voies(t, "a.txt", ["commun.txt"])
        verifie("pas d'erreur", "ValueError", "trois_voies_hors_liste : ValueError")
    except ValueError:
        verifie(True, True, "trois_voies_hors_liste : ValueError")
    r = asst.trois_voies(t, "commun.txt", ["commun.txt"])
    verifie(("+local" in r["mien"], "+amont" in r["amont"]), (True, True), "trois_voies : mien et amont")
    verifie("+amont" in r["mien"], False, "trois_voies : le diff « mien » ne contient pas l'amont")


def principal():
    cas = [("a_jour", a_jour, c_a_jour), ("avance_seule", avance_seule, c_avance_seule),
           ("non_pousses_seuls", non_pousses_seuls, c_non_pousses_seuls),
           ("retard_sans_recouvrement", retard_sans_recouvrement, c_retard_sans_recouvrement),
           ("deux_cotes_sans_conflit", deux_cotes_sans_conflit, c_deux_cotes_sans_conflit),
           ("conflit", conflit, c_conflit), ("non_pousses_force_b", non_pousses_force_b, c_non_pousses_force_b),
           ("arbre_sale", arbre_sale, c_arbre_sale), ("autre_branche", autre_branche, c_autre_branche),
           ("fetch_impossible", fetch_impossible, c_fetch_impossible),
           ("accents", accents_et_espaces, c_accents_et_espaces),
           ("commits_adaptateur", commits_adaptateur, c_commits_adaptateur),
           ("journal", journal, c_journal2), ("trois_voies", trois_voies, c_trois_voies)]
    with tempfile.TemporaryDirectory() as modele:
        fd.cree(Path(modele))
        MODELE["dossier"] = Path(modele)
        for nom, prep, ctrl in cas:
            print(f"-- {nom}")
            un_cas(nom, prep, ctrl)
    if ECHECS:
        print(f"\n{len(ECHECS)} ECHEC(S)")
        sys.exit(1)
    print("\nTout est vert.")


if __name__ == "__main__":
    principal()
