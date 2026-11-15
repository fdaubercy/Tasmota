"""Banc de fils_github.py, sans reseau (faux gh). Code de sortie 0 = vert.
Lancer : python .claude/hooks/test_fils_github.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fils_github as F

ISSUE = {"depot": "o/r", "type": "issues", "numero": 7}
DISC = {"depot": "o/r", "type": "discussions", "numero": 9}
echecs = 0


def verifie(nom, ok):
    global echecs
    print(("ok     " if ok else "ECHEC  ") + nom)
    echecs += 0 if ok else 1


def faux(coms_issue, fermee=False, disc=None):
    def appel(args):
        if args[0] == "repos/o/r/issues/7":
            return {"state": "closed" if fermee else "open"}
        if args[0].startswith("repos/o/r/issues/7/comments"):
            return [{"user": {"login": a}, "created_at": d, "body": "Thanks, **fixed** in\n> quote\n```c\nx\n```\n" + "y" * 300}
                    for a, d in coms_issue]
        if args[0] == "graphql":
            return disc
        return None
    return appel


def discussion(noeuds, closed=False, answer=None):
    return {"data": {"repository": {"discussion": {"closed": closed, "answer": answer, "comments": {"nodes": noeuds}}}}}


etat = {}
verifie("premier releve : memorise sans notifier",
        F.releve([ISSUE], etat, "moi", faux([("a", "2026-11-01T00:00:00Z")])) == [] and etat["fils"][F.url(ISSUE)]["vues"] == 1)
m = F.releve([ISSUE], etat, "moi", faux([("a", "2026-11-01"), ("moi", "2026-11-02"), ("b", "2026-11-03T10:00:00Z")]))
verifie("une nouvelle reponse d'un autre : signalee, auteur et date", len(m) == 1 and "1 nouvelle" in m[0][1] and "b le 2026-11-03" in m[0][1])
verifie("extrait : Markdown aplati, citation et code retires, 200 car. au plus",
        m[0][2].startswith("Thanks, fixed in [code] yyy") and len(m[0][2]) == 200 and m[0][2].endswith("…"))
verifie("ma propre reponse ne compte pas", etat["fils"][F.url(ISSUE)]["vues"] == 2)
verifie("rien de neuf : silence", F.releve([ISSUE], etat, "moi", faux([("a", "1"), ("moi", "2"), ("b", "3")])) == [])
m = F.releve([ISSUE], etat, "moi", faux([("a", "1"), ("b", "3")], fermee=True))
verifie("fil ferme : signale une fois", len(m) == 1 and "ferme" in m[0][1])
verifie("... pas deux fois", F.releve([ISSUE], etat, "moi", faux([("a", "1"), ("b", "3")], fermee=True)) == [])
verifie("releve en echec : etat garde, silence", F.releve([ISSUE], etat, "moi", lambda a: None) == [] and etat["fils"][F.url(ISSUE)]["vues"] == 2)

etat = {}
n1 = [{"author": {"login": "x"}, "createdAt": "2026-11-15T01:00:00Z", "replies": {"nodes": []}}]
F.releve([DISC], etat, "moi", faux([], disc=discussion(n1)))
n2 = [{"author": {"login": "x"}, "createdAt": "2026-11-15T01:00:00Z",
       "replies": {"nodes": [{"author": {"login": "y"}, "createdAt": "2026-11-16T02:00:00Z"},
                             {"author": {"login": "moi"}, "createdAt": "2026-11-16T03:00:00Z"}]}}]
m = F.releve([DISC], etat, "moi", faux([], disc=discussion(n2)))
verifie("discussion : reponse imbriquee d'un autre comptee, la mienne non", len(m) == 1 and "y le 2026-11-16" in m[0][1])
m = F.releve([DISC], etat, "moi", faux([], disc=discussion(n2, answer={"id": "A"})))
verifie("discussion : solution marquee signalee", len(m) == 1 and "solution" in m[0][1])
verifie("discussion illisible : None", F.reponses(DISC, "moi", lambda a: {"data": None}) is None)
verifie("URL acceptee", bool(F.RE_URL.match("https://github.com/arendst/Tasmota/discussions/25280")))
verifie("URL refusee (pull)", not F.RE_URL.match("https://github.com/arendst/Tasmota/pull/1"))

verifie("traduction sans programme claude : texte d'origine", F.traduis("Hello", programme=os.devnull + "_absent") == "Hello")
verifie("traduction d'un extrait vide : rien a faire", F.traduis("") == "")

print("TEST_FILS_GITHUB:", "OK" if echecs == 0 else f"ECHEC ({echecs})")
sys.exit(1 if echecs else 0)
