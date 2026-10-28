"""Suite du banc de la voie B (test_synchro_fork_fusion.py, deja a sa limite de taille) : cas de la relecture
finale. Code de sortie 0 = vert. Memes regles : FAUX depot en dossier temporaire, jamais le vrai, jamais le reseau.
Cas : journal non ecrit (signale), push arrete au delai (DELAI_PUSH minuscule), `--numstat` restreint aux chemins
en conflit, /commit-journal sur le faux depot (le vrai depot garde son HEAD).
"""

import subprocess
import sys
import tempfile
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import test_synchro_fork_fusion as base  # noqa: E402  (verifie, ECHECS, MODELE, un_cas, SANS, conflit...)
import faux_depot_synchro as fd  # noqa: E402
import synchro_fork_assistant as asst  # noqa: E402
import synchro_fork_fusion as fu  # noqa: E402
import synchro_fork_web as web  # noqa: E402
import synchronise_fork_tasmota as sft  # noqa: E402

verifie, SANS = base.verifie, base.SANS


def preparation_merge(d, t):
    fd.commit_amont(d, {"a.txt": "a2\n"}, "Amont: titre")
    fd.git(t, "fetch", "-q", "upstream")
    fu.lance_merge(t, SANS)


def journal_non_ecrit(d, t):
    preparation_merge(d, t)
    journal_casse = Path(t) / "journal_dossier"
    journal_casse.mkdir()                                  # un dossier a la place du fichier : l'ecriture echoue (OSError)
    texte = fu.termine(t, SANS, historique=journal_casse)
    verifie("n'a pas pu être écrit" in texte and texte.startswith("Merge commité"), True,
            "journal_non_ecrit : merge commite, journal non ecrit signale")


def journal_ecrit(d, t):
    preparation_merge(d, t)
    verifie("n'a pas pu" in fu.termine(t, SANS), False, "journal_ecrit : aucun avertissement quand le journal est ecrit")


def push_delai(d, t):
    fd.commit_local(t, {"b.txt": "b\n"}, "local non pousse")
    avant, fu.DELAI_PUSH = fu.DELAI_PUSH, 0.001
    try:
        base.refuse(lambda: fu.pousse(t), RuntimeError, "push_delai : push arrete au delai", contient="n'a pas fini")
    finally:
        fu.DELAI_PUSH = avant
    verifie(fd.git(t, "rev-list", "--count", "origin/development..HEAD"), "1", "push_delai : rien de perdu, commit local intact")


def numstat_restreint(d, t):
    base.conflit(d, t)
    appels, vrai = [], asst._git

    def espion(racine, *args, delai=None):
        appels.append(args)
        return vrai(racine, *args, delai=delai)
    asst._git = espion
    try:
        fu.lance_merge(t, SANS)
    finally:
        asst._git = vrai
    numstat = [a for a in appels if "--numstat" in a]
    verifie([a[a.index("--") + 1:] for a in numstat if "--" in a], [("commun.txt",)],
            "numstat_restreint : `git diff --numstat` limite aux chemins en conflit")


class SessionInerte:
    def en_cours(self):
        return False


def commit_journal_faux_depot(d, t):
    journal = Path(t) / sft.HISTORIQUE_REL
    fd.commit_local(t, {sft.HISTORIQUE_REL: "j\n"}, "journal")
    journal.write_text("j\nsuite\n", encoding="utf-8")
    reel = lambda: subprocess.run(["git", "rev-parse", "HEAD"], cwd=sft.REPO, capture_output=True, text=True).stdout  # noqa: E731
    avant = reel()
    r = web.traite_post("/commit-journal", {}, SessionInerte(), racine=t)
    verifie(("docs: synchro du fork" in r["commit"], fd.git(t, "log", "-1", "--format=%s")),
            (True, "docs: synchro du fork"), "commit_journal : commite dans le faux depot (racine)")
    verifie(reel(), avant, "commit_journal : le vrai depot n'a pas bouge")


def principal():
    cas = [("journal_non_ecrit", journal_non_ecrit), ("journal_ecrit", journal_ecrit), ("push_delai", push_delai),
           ("numstat_restreint", numstat_restreint), ("commit_journal", commit_journal_faux_depot)]
    with tempfile.TemporaryDirectory() as modele:
        fd.cree(Path(modele))
        base.MODELE["dossier"] = Path(modele)
        for nom, scenario in cas:
            base.un_cas(nom, scenario)
    if base.ECHECS:
        print(f"\n{len(base.ECHECS)} ECHEC(S)")
        sys.exit(1)
    print("\nTout est vert.")


if __name__ == "__main__":
    principal()
