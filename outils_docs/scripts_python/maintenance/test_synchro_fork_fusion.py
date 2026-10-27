"""Banc des actions de la voie B de l'assistant de synchro du fork (synchro_fork_fusion.py). Code de sortie 0 = vert.

Chaque cas travaille sur une copie du FAUX depot (faux_depot_synchro : amont et origin nus, clone de travail)
dans un dossier temporaire : jamais le vrai depot, jamais le reseau, jamais `pio`.
Cas : merge propre (2 parents, journal), mien, amont, marqueurs restants, modifie ici et supprime par l'amont,
chemin accentue, binaire, merge etranger, reprise, abandon (assistant, etranger, autre operation), avance
rapide sur origin, build en cours ou indetectable, prealables, bascule, index hors du merge, ouvre, push,
push refuse, jamais de forcage, depot introuvable (analyse en erreur).
Temoins : un « resolu » qui n'inspecte pas les marqueurs DOIT faire echouer `resolu_avec_marqueurs` ; une liste
de conflits prise dans la prevision au lieu de `--diff-filter=U` DOIT faire echouer `mien` ou `reprise`.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import faux_depot_synchro as fd  # noqa: E402
import synchro_fork_assistant as asst  # noqa: E402
import synchro_fork_fusion as fu  # noqa: E402
import synchronise_fork_tasmota as sft  # noqa: E402

ECHECS = []
LIGNES = [f"ligne {i}\n" for i in range(1, 11)]
SANS = lambda: []  # noqa: E731  (aucun build en cours)
MODELE = {}


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def refuse(fonction, exception, libelle, contient=""):
    """La fonction doit lever `exception` (dont le texte contient `contient`)."""
    try:
        fonction()
    except exception as e:
        return verifie(contient in str(e), True, libelle + (f" (texte : {e})" if contient not in str(e) else ""))
    except Exception as e:  # noqa: BLE001
        return verifie(type(e).__name__, exception.__name__, libelle)
    return verifie("pas d'erreur", exception.__name__, libelle)


def commun_ligne(n, texte):
    lignes = list(LIGNES)
    lignes[n - 1] = texte + "\n"
    return "".join(lignes)


def lit(t, chemin):
    return (Path(t) / chemin).read_text(encoding="utf-8")


def merge_head(t):
    return (asst.dossier_git(t) / "MERGE_HEAD").exists()


def marque(t):
    return (asst.dossier_git(t) / fu.MARQUE).exists()


def chemins(t):
    return [c["chemin"] for c in fu.conflits(t)]


def autre_clone_pousse(d, nom="o.txt"):
    """Un autre poste pousse sur origin : origin avance sans que le clone de travail le sache."""
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "c"
        fd.git(tmp, "clone", "-q", str(d / "origin.git"), str(clone))
        fd.git(clone, "config", "user.name", "B")
        fd.git(clone, "config", "user.email", "b@example.invalid")
        sha = fd._commit(clone, {nom: "o\n"}, "origin avance")
        fd.git(clone, "push", "-q", "origin", "development")
    return sha


def conflit(d, t, chemin="commun.txt", amont=None, local=None, titre="amont l3"):
    """Conflit de contenu sur `chemin`, le local pousse (aucun commit non pousse), upstream recupere."""
    fd.commit_amont(d, {chemin: amont or commun_ligne(3, "amont")}, titre)
    fd.commit_local(t, {chemin: local or commun_ligne(3, "local")}, "local " + chemin)
    fd.git(t, "push", "-q", "origin", "development")
    fd.git(t, "fetch", "-q", "upstream")


def merge_a_la_main(t):
    subprocess.run(["git", "merge", "upstream/development"], cwd=t, capture_output=True, env=fd.ENV)


def un_cas(nom, scenario):
    print(f"-- {nom}")
    with tempfile.TemporaryDirectory() as tmp:
        dossier = Path(tmp)
        travail = fd.copie(MODELE["dossier"], dossier)
        try:
            scenario(dossier, travail)
        except Exception as e:  # noqa: BLE001  (un cas qui plante est un echec, les suivants tournent)
            verifie(f"{type(e).__name__}: {e}"[:300], "aucune exception", f"{nom} : exception inattendue")


def merge_propre(d, t):
    fd.commit_amont(d, {"a.txt": "a2\n"}, "Amont: titre du commit propre")
    fd.git(t, "fetch", "-q", "upstream")
    fu.lance_merge(t, SANS)
    verifie((merge_head(t), marque(t), fu.conflits(t)), (True, True, []), "merge_propre : merge en cours, sans conflit")
    fu.termine(t, SANS)
    parents = fd.git(t, "log", "-1", "--format=%P").split()
    verifie(len(parents), 2, "merge_propre : commit de merge a 2 parents")
    verifie((merge_head(t), marque(t)), (False, False), "merge_propre : ni MERGE_HEAD ni marque apres termine")
    journal = lit(t, sft.HISTORIQUE_REL)
    verifie("Amont: titre du commit propre" in journal, True, "merge_propre : titre amont au journal du faux depot")
    verifie("`upstream:development` → `origin:development`" in journal, True,
            "merge_propre : remotes nommes d'apres le faux depot (pas le vrai)")
    verifie("merge local (conflits resolus)" in journal, True, "merge_propre : type de merge au journal")
    suivis = fd.git(t, "ls-files", "--", sft.HISTORIQUE_REL)
    verifie(suivis, "", "merge_propre : le journal n'est pas commite par termine")


def mien(d, t):
    conflit(d, t)
    fu.lance_merge(t, SANS)
    verifie(fu.conflits(t), [{"chemin": "commun.txt", "type": "UU", "binaire": False}], "mien : conflit UU lu")
    fu.resout(t, "commun.txt", "mien", SANS)
    verifie((lit(t, "commun.txt"), fu.conflits(t)), (commun_ligne(3, "local"), []), "mien : version locale, resolu")
    fu.termine(t, SANS)
    verifie(lit(t, "commun.txt"), commun_ligne(3, "local"), "mien : version locale apres termine")


def amont(d, t):
    conflit(d, t)
    fu.lance_merge(t, SANS)
    fu.resout(t, "commun.txt", "amont", SANS)
    verifie((lit(t, "commun.txt"), fu.conflits(t)), (commun_ligne(3, "amont"), []), "amont : version amont, resolu")


def resolu_avec_marqueurs(d, t):
    conflit(d, t)
    fu.lance_merge(t, SANS)
    verifie("<<<<<<<" in lit(t, "commun.txt"), True, "resolu_avec_marqueurs : marqueurs presents")
    refuse(lambda: fu.resout(t, "commun.txt", "resolu", SANS), RuntimeError, "resolu_avec_marqueurs : refuse")
    verifie(chemins(t), ["commun.txt"], "resolu_avec_marqueurs : toujours en conflit apres le refus")
    propre = commun_ligne(3, "fusion a la main") + "Titre\n==========\n"   # soulignement plus long qu'un marqueur
    (t / "commun.txt").write_text(propre, encoding="utf-8")
    fu.resout(t, "commun.txt", "resolu", SANS)
    verifie((fu.conflits(t), lit(t, "commun.txt")), ([], propre), "resolu_avec_marqueurs : accepte une fois propre")
    fu.termine(t, SANS)
    verifie(lit(t, "commun.txt"), propre, "resolu_avec_marqueurs : version a la main commitee")


def modifie_ici_supprime_amont(d, t):
    fd.commit_amont(d, {"a.txt": None}, "amont supprime a.txt")
    fd.commit_local(t, {"a.txt": "modifie ici\n"}, "local a.txt")
    fd.git(t, "push", "-q", "origin", "development")
    fd.git(t, "fetch", "-q", "upstream")
    fu.lance_merge(t, SANS)
    verifie(fu.conflits(t), [{"chemin": "a.txt", "type": "UD", "binaire": False}], "modifie_supprime : type UD")
    refuse(lambda: fu.resout(t, "a.txt", "mien", SANS), RuntimeError, "modifie_supprime : mien refuse")
    refuse(lambda: fu.resout(t, "a.txt", "resolu", SANS), RuntimeError, "modifie_supprime : resolu refuse")
    fu.resout(t, "a.txt", "supprimer", SANS)
    fu.termine(t, SANS)
    verifie(((t / "a.txt").exists(), fd.git(t, "ls-files", "--", "a.txt")), (False, ""),
            "modifie_supprime : fichier absent apres termine")


def garder_refuse_sur_uu(d, t):
    conflit(d, t)
    fu.lance_merge(t, SANS)
    refuse(lambda: fu.resout(t, "commun.txt", "garder", SANS), RuntimeError, "garder_uu : garder refuse sur UU")
    refuse(lambda: fu.resout(t, "commun.txt", "supprimer", SANS), RuntimeError, "garder_uu : supprimer refuse")
    refuse(lambda: fu.resout(t, "commun.txt", "inconnu", SANS), ValueError, "garder_uu : choix inconnu")
    refuse(lambda: fu.resout(t, "a.txt", "mien", SANS), ValueError, "garder_uu : chemin hors des conflits")
    refuse(lambda: fu.termine(t, SANS), RuntimeError, "garder_uu : termine refuse tant qu'un conflit reste")


def chemin_accentue(d, t):
    conflit(d, t, fd.FICHIER_ACCENT, "amont\n", "local\n")
    fu.lance_merge(t, SANS)
    verifie(chemins(t), [fd.FICHIER_ACCENT], "chemin_accentue : chemin lu en clair")
    fu.resout(t, fd.FICHIER_ACCENT, "amont", SANS)
    verifie((lit(t, fd.FICHIER_ACCENT), fu.conflits(t)), ("amont\n", []), "chemin_accentue : resolu par amont")
    fu.termine(t, SANS)
    verifie(len(fd.git(t, "log", "-1", "--format=%P").split()), 2, "chemin_accentue : merge commite")


def binaire(d, t):
    fd.commit_amont(d, {"b.bin": "\x00base"}, "amont ajoute b.bin")
    fd.git(t, "fetch", "-q", "upstream")
    fd.git(t, "merge", "-q", "--ff-only", "upstream/development")
    fd.git(t, "push", "-q", "origin", "development")
    conflit(d, t, "b.bin", "\x00amont", "\x00local")
    fu.lance_merge(t, SANS)
    verifie(fu.conflits(t), [{"chemin": "b.bin", "type": "UU", "binaire": True}], "binaire : drapeau binaire")
    refuse(lambda: fu.resout(t, "b.bin", "resolu", SANS), RuntimeError, "binaire : resolu refuse")
    fu.resout(t, "b.bin", "amont", SANS)
    verifie(((t / "b.bin").read_bytes(), fu.conflits(t)), (b"\x00amont", []), "binaire : amont pris")


def merge_etranger(d, t):
    conflit(d, t)
    merge_a_la_main(t)
    verifie(merge_head(t), True, "merge_etranger : merge lance a la main")
    refuse(lambda: fu.resout(t, "commun.txt", "mien", SANS), RuntimeError, "merge_etranger : resout refuse",
           "étranger")
    verifie("<<<<<<<" in lit(t, "commun.txt"), True, "merge_etranger : fichier non touche")
    refuse(lambda: fu.termine(t, SANS), RuntimeError, "merge_etranger : termine refuse")
    refuse(lambda: fu.lance_merge(t, SANS), RuntimeError, "merge_etranger : lance_merge refuse")
    (asst.dossier_git(t) / fu.MARQUE).write_text('{"sha": "0123456789", "commits": []}', encoding="utf-8")
    verifie(fu.merge_assistant_en_cours(t), False, "merge_etranger : marque d'un autre sha -> etranger")
    a = asst.analyse(t, fetch=False)
    verifie((a["operation"], a["merge_assistant"]), ("merge", False), "merge_etranger : analyse, merge etranger")
    verifie([e["id"] for e in a["etapes"]][:1], ["operation"], "merge_etranger : etape operation en tete")


def reprise(d, t):
    conflit(d, t)
    fd.commit_amont(d, {"a.txt": "a amont\n"}, "amont a")
    fd.commit_local(t, {"a.txt": "a local\n"}, "local a")
    fd.git(t, "push", "-q", "origin", "development")
    fd.git(t, "fetch", "-q", "upstream")
    fu.lance_merge(t, SANS)
    verifie(chemins(t), ["a.txt", "commun.txt"], "reprise : deux conflits")
    fu.resout(t, "a.txt", "mien", SANS)
    # Page fermee, serveur arrete puis relance : seule l'analyse (avec fetch) retrouve le fil.
    a = asst.analyse(t, fetch=True)
    verifie(a["merge_assistant"], True, "reprise : merge de l'assistant reconnu")
    verifie(a["conflits"], fu.conflits(t), "reprise : conflits dans l'analyse")
    verifie(chemins(t), ["commun.txt"], "reprise : seul le conflit restant (le depot fait foi)")
    statuts = {e["id"]: e["statut"] for e in a["etapes"]}
    verifie(statuts.get("fusion_b"), "courante", "reprise : fusion_b courante")
    verifie(("operation" in statuts, "arbre" in statuts), (False, False), "reprise : ni operation ni arbre")


def abandon(d, t):
    conflit(d, t)
    avant = fd.git(t, "rev-parse", "HEAD")
    fu.lance_merge(t, SANS)
    fu.abandonne(t, SANS)
    verifie((merge_head(t), marque(t), fd.git(t, "rev-parse", "HEAD")), (False, False, avant),
            "abandon : ni MERGE_HEAD ni marque, HEAD inchange")
    verifie(fd.git(t, "status", "--porcelain"), "", "abandon : arbre rendu propre")
    merge_a_la_main(t)
    fu.abandonne(t, SANS)
    verifie((merge_head(t), fd.git(t, "rev-parse", "HEAD")), (False, avant), "abandon : merge etranger abandonne")
    refuse(lambda: fu.abandonne(t, SANS), RuntimeError, "abandon : rien a abandonner")
    subprocess.run(["git", "rebase", "upstream/development"], cwd=t, capture_output=True, env=fd.ENV)
    verifie(asst.operation(t), "rebase", "abandon : autre operation en cours")
    refuse(lambda: fu.abandonne(t, SANS), RuntimeError, "abandon : refuse hors d'un merge")
    verifie(asst.operation(t), "rebase", "abandon : l'autre operation n'est pas touchee")


def ff_origin(d, t):
    fd.commit_amont(d, {"a.txt": "a2\n"}, "amont a")
    autre_clone_pousse(d)
    a = asst.analyse(t, fetch=True)
    verifie((a["retard_origin"], a["retard"]), (1, 1), "ff_origin : origin en avance d'un commit")
    refuse(lambda: fu.lance_merge(t, SANS), RuntimeError, "ff_origin : lance_merge refuse", "origin")
    verifie(merge_head(t), False, "ff_origin : aucun merge lance")
    fu.ff_origin(t, SANS)
    verifie(fd.git(t, "rev-parse", "HEAD"), fd.git(t, "rev-parse", "origin/development"), "ff_origin : avance rapide")
    fu.lance_merge(t, SANS)
    verifie(merge_head(t), True, "ff_origin : lance_merge accepte ensuite")


def build_en_cours(d, t):
    conflit(d, t)
    occupe, inconnu = (lambda: ["pio run -e x"]), (lambda: None)
    for libelle, builds in (("build", occupe), ("indetectable", inconnu)):
        texte = "impossible de vérifier" if builds is inconnu else ""
        refuse(lambda: fu.lance_merge(t, builds), RuntimeError, f"build_en_cours ({libelle}) : lance_merge", texte)
        refuse(lambda: fu.bascule(t, builds), RuntimeError, f"build_en_cours ({libelle}) : bascule", texte)
        refuse(lambda: fu.ff_origin(t, builds), RuntimeError, f"build_en_cours ({libelle}) : ff_origin", texte)
    verifie(merge_head(t), False, "build_en_cours : aucun merge lance")
    fu.lance_merge(t, SANS)
    for libelle, builds in (("build", occupe), ("indetectable", inconnu)):
        texte = "impossible de vérifier" if builds is inconnu else ""
        refuse(lambda: fu.resout(t, "commun.txt", "mien", builds), RuntimeError, f"build_en_cours ({libelle}) : resout",
               texte)
        refuse(lambda: fu.termine(t, builds), RuntimeError, f"build_en_cours ({libelle}) : termine", texte)
        refuse(lambda: fu.abandonne(t, builds), RuntimeError, f"build_en_cours ({libelle}) : abandonne", texte)
    verifie((merge_head(t), chemins(t)), (True, ["commun.txt"]), "build_en_cours : merge intact apres les refus")


def prealables(d, t):
    refuse(lambda: fu.lance_merge(t, SANS), RuntimeError, "prealables : rien a fusionner (retard 0)")
    fd.commit_amont(d, {"commun.txt": commun_ligne(1, "amont")}, "amont l1")
    fd.git(t, "fetch", "-q", "upstream")
    (t / "a.txt").write_text("sale\n", encoding="utf-8")
    refuse(lambda: fu.lance_merge(t, SANS), RuntimeError, "prealables : arbre sale refuse")
    fd.git(t, "switch", "-q", "-c", "essai")                  # la modification suit sur la nouvelle branche
    refuse(lambda: fu.bascule(t, SANS), RuntimeError, "prealables : bascule refusee sur arbre sale")
    fd.git(t, "checkout", "-q", "--", "a.txt")
    refuse(lambda: fu.lance_merge(t, SANS), RuntimeError, "prealables : autre branche refusee", "development")
    fu.bascule(t, SANS)
    verifie(fd.git(t, "rev-parse", "--abbrev-ref", "HEAD"), "development", "prealables : bascule sur development")
    journal = t / sft.HISTORIQUE_REL
    journal.parent.mkdir(parents=True, exist_ok=True)
    fd.commit_local(t, {sft.HISTORIQUE_REL: "j\n"}, "journal")
    fd.git(t, "push", "-q", "origin", "development")
    journal.write_text("j2\n", encoding="utf-8")
    fu.lance_merge(t, SANS)
    verifie(merge_head(t), True, "prealables : journal modifie seul accepte")
    (t / "a.txt").write_text("hors du merge\n", encoding="utf-8")
    fd.git(t, "add", "--", "a.txt")
    refuse(lambda: fu.termine(t, SANS), RuntimeError, "prealables : fichier indexe hors du merge refuse", "a.txt")
    fd.git(t, "restore", "--staged", "--", "a.txt")
    fu.termine(t, SANS)
    verifie(fd.git(t, "show", "--name-only", "--format=", "HEAD", "--first-parent").split(), ["commun.txt"],
            "prealables : seul le fichier du merge est commite")
    verifie(lit(t, "a.txt"), "hors du merge\n", "prealables : travail hors merge laisse sur le disque")


def ouvre(d, t):
    conflit(d, t)
    fu.lance_merge(t, SANS)
    refuse(lambda: fu.ouvre(t, "a.txt"), ValueError, "ouvre : chemin hors des conflits")
    vrai = fu.shutil.which
    fu.shutil.which = lambda nom: None
    try:
        refuse(lambda: fu.ouvre(t, "commun.txt"), RuntimeError, "ouvre : code introuvable, chemin donne",
               str(Path(t) / "commun.txt"))
    finally:
        fu.shutil.which = vrai


def push(d, t):
    fd.commit_amont(d, {"a.txt": "a2\n"}, "amont a")
    fd.git(t, "fetch", "-q", "upstream")
    fu.lance_merge(t, SANS)
    fu.termine(t, SANS)
    sha = fd.git(t, "rev-parse", "HEAD")
    sortie = fu.pousse(t)
    verifie(isinstance(sortie, str), True, "push : sortie de git rendue")
    verifie(sha in fd.git(d / "origin.git", "log", "development", "--format=%H").split(), True,
            "push : origin contient le commit de merge")


def push_refuse(d, t):
    fd.commit_amont(d, {"a.txt": "a2\n"}, "amont a")
    fd.git(t, "fetch", "-q", "upstream")
    fu.lance_merge(t, SANS)
    fu.termine(t, SANS)
    autre = autre_clone_pousse(d)
    refuse(lambda: fu.pousse(t), RuntimeError, "push_refuse : refus de git remonte")
    verifie(fd.git(d / "origin.git", "rev-parse", "development"), autre, "push_refuse : origin inchange")


def jamais_de_force():
    print("-- jamais_de_force")
    source = (ICI / "synchro_fork_fusion.py").read_text(encoding="utf-8")
    for motif in ("--force", '"-f"', "'-f'", "stash", "reset", "rebase"):
        verifie(motif in source.lower(), False, f"jamais_de_force : {motif} absent de la source")


def depot_introuvable():
    """Dossier .git introuvable : l'analyse le dit (erreur), sans etape modifiante, au lieu de « rien en cours »."""
    print("-- depot_introuvable")
    with tempfile.TemporaryDirectory() as tmp:
        refuse(lambda: asst.operation(tmp), RuntimeError, "depot_introuvable : operation leve RuntimeError")
        a = asst.analyse(tmp, fetch=False)
        verifie((a["erreur"] != "", a["etapes"]), (True, []), "depot_introuvable : analyse en erreur, aucune etape")


def principal():
    cas = [("merge_propre", merge_propre), ("mien", mien), ("amont", amont),
           ("resolu_avec_marqueurs", resolu_avec_marqueurs), ("modifie_ici_supprime_amont", modifie_ici_supprime_amont),
           ("garder_refuse_sur_uu", garder_refuse_sur_uu), ("chemin_accentue", chemin_accentue), ("binaire", binaire),
           ("merge_etranger", merge_etranger), ("reprise", reprise), ("abandon", abandon), ("ff_origin", ff_origin),
           ("build_en_cours", build_en_cours), ("prealables", prealables), ("ouvre", ouvre), ("push", push),
           ("push_refuse", push_refuse)]
    jamais_de_force()
    depot_introuvable()
    with tempfile.TemporaryDirectory() as modele:
        fd.cree(Path(modele))
        MODELE["dossier"] = Path(modele)
        for nom, scenario in cas:
            un_cas(nom, scenario)
    if ECHECS:
        print(f"\n{len(ECHECS)} ECHEC(S)")
        sys.exit(1)
    print("\nTout est vert.")


if __name__ == "__main__":
    principal()
