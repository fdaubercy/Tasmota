#!/usr/bin/env python3
"""Banc de reprise_limite.py : faux Claude, temps simule, verrous en dossier temporaire ; aucun appel a Claude.

    python .claude/hooks/test_reprise_limite.py

Code de sortie 0 = vert, 1 = rouge. Ne prouve PAS qu'une vraie limite declenche le hook : seul un vrai depassement le peut.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reprise_limite as r                                         # noqa: E402

ECHECS = []
LIMITE = (1, "You've hit your usage limit, resets 3pm")
SESSION = "1c5db414-cc78-413b-a9a2-07ff42318ece"


def verifie(ok, libelle):
    print(("OK   " if ok else "KO   ") + libelle)
    if not ok:
        ECHECS.append(libelle)


def joue(reponses):
    """Rend (resultat, tentatives, secondes dormies) ; la derniere reponse se repete."""
    t, vus = [0.0], []

    def dort(s):
        t[0] += s

    def lance(*a):
        vus.append(a)
        return reponses[min(len(vus), len(reponses)) - 1]

    return r.veille(SESSION, ".", "auto", lance=lance, dort=dort, horloge=lambda: t[0], journal=lambda m: None), len(vus), t[0]


def main():
    res, n, s = joue([LIMITE, LIMITE, (0, "fait")])
    verifie(res == "repris" and n == 3, "limite, limite, succes : reprise a la 3e tentative")
    verifie(s == 3 * r.ATTENTE_S, "attend AVANT chaque tentative")
    res, n, _ = joue([(0, "fait")])
    verifie(res == "repris" and n == 1, "succes direct : une seule tentative (temoin)")
    res, n, _ = joue([(1, "authentication failed")])
    verifie(res == "abandon" and n == 3, "autre echec : abandon apres 3, sans insister")
    res, n, _ = joue([(1, "panne"), (1, "panne"), LIMITE, (1, "panne"), (1, "panne"), (0, "ok")])
    verifie(res == "repris" and n == 6, "une limite remet a zero les autres echecs")
    res, n, s = joue([LIMITE])
    verifie(res == "delai" and s >= r.DUREE_MAX_S and n == r.DUREE_MAX_S // r.ATTENTE_S, "limite sans fin : s'arrete au delai, pas de boucle infinie")

    vus = []
    demarre = lambda *a: vus.append(a)                               # noqa: E731
    entree = {"session_id": SESSION, "cwd": str(Path.cwd()), "permission_mode": "acceptEdits"}
    verifie(r.hook(json.dumps(entree), demarre) == "acceptEdits" and vus[0][0] == SESSION, "hook : veille demarree dans le mode de la conversation")
    verifie(r.hook(json.dumps({**entree, "permission_mode": "bypassPermissions"}), demarre) == "auto", "bypassPermissions jamais repris")
    verifie(r.hook(json.dumps({**entree, "permission_mode": "default"}), demarre) == "auto", "mode default -> auto (sans invite possible)")
    avant = len(vus)
    verifie(r.hook("{pas du json", demarre) is None, "entree illisible : rien")
    verifie(r.hook(json.dumps({**entree, "session_id": "a & calc"}), demarre) is None, "session suspecte : refusee")
    verifie(r.hook(json.dumps({**entree, "cwd": "Z:/absent"}), demarre) is None, "dossier absent : refuse")
    verifie(len(vus) == avant, "aucune veille demarree pour une entree refusee")

    # Sessions en double (2026-11-13) : une conversation ouverte dans un onglet n'est jamais reprise par -p
    t, vus, tenue = [0.0], [], [3]                                   # tenue par un onglet pendant 3 controles

    def occupee():
        tenue[0] -= 1
        return 4242 if tenue[0] >= 0 else None

    def dort(s):
        t[0] += s
    res = r.veille(SESSION, ".", "auto", lance=lambda *a: vus.append(a) or (0, "fait"), dort=dort,
                   horloge=lambda: t[0], journal=lambda m: None, occupee=occupee)
    verifie(res == "repris" and len(vus) == 1 and t[0] == 4 * r.ATTENTE_S,
            "conversation ouverte dans un onglet : aucune reprise tant qu'il la tient, reprise apres sa fermeture")
    vus.clear()
    res = r.veille(SESSION, ".", "auto", lance=lambda *a: vus.append(a) or (0, "fait"), dort=lambda s: None,
                   horloge=lambda: 0.0, journal=lambda m: None, reprise=lambda: True)
    verifie(res == "deja_repris" and not vus, "conversation reprise ailleurs (vraie reponse) : veille arretee, rien lance")

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        f = d / "t.jsonl"
        erreur = {"type": "assistant", "isApiErrorMessage": True, "error": "rate_limit"}
        f.write_text(json.dumps({"type": "assistant", "message": {}}) + "\n", encoding="utf-8")
        repris = r.surveille_transcript(f)
        verifie(not repris(), "transcript inchange : pas repris")
        with open(f, "a", encoding="utf-8") as fl:
            fl.write(json.dumps({"type": "user"}) + "\n" + json.dumps(erreur) + "\n")
        verifie(not repris(), "message retape pendant la limite (erreur de limite seule) : pas repris")
        with open(f, "a", encoding="utf-8") as fl:
            fl.write(json.dumps({"type": "assistant", "message": {"content": []}}) + "\n")
        verifie(repris(), "vraie reponse apres la limite : reprise detectee")
        verifie(not r.surveille_transcript(None)(), "transcript introuvable : pas de garde (temoin)")

        reg = d / "sessions"
        reg.mkdir()
        (reg / "10.json").write_text(json.dumps({"pid": 10, "sessionId": SESSION, "kind": "interactive"}), encoding="utf-8")
        (reg / "11.json").write_text(json.dumps({"pid": 11, "sessionId": "autre-session-000"}), encoding="utf-8")
        (reg / "12.json").write_text("{illisible", encoding="utf-8")
        verifie(r.session_ouverte(SESSION, reg, lambda p: p == 10) == 10, "registre : processus vivant qui tient la conversation trouve")
        verifie(r.session_ouverte(SESSION, reg, lambda p: False) is None, "registre : processus mort ignore")
        verifie(r.session_ouverte("autre-session-111", reg, lambda p: True) is None, "registre : autre conversation ignoree")
        verifie(r.session_ouverte(SESSION, d / "absent", lambda p: True) is None, "registre absent : rien")

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        verifie(r.prend_verrou(SESSION, d, lambda p: True), "verrou libre : pris")
        verifie(not r.prend_verrou(SESSION, d, lambda p: True), "veille vivante : seconde refusee")
        verifie(r.prend_verrou(SESSION, d, lambda p: False), "veille morte : verrou repris")
    print("\n" + ("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
