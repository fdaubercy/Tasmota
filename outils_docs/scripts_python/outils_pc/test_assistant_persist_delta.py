"""Banc de assistant_persist_delta (ecart ligne a ligne applique a une zone). Code de sortie 0 = vert.

Le .h reel est lu en lecture seule ; aucune de ses lignes n'est affichee (il contient des mots de passe).
"""

import os
import re
import sys
from pathlib import Path

ECHECS = []
RACINE = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")))


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def aller_retour_h(d):
    import fichiers_berry_creation as c
    lignes = (RACINE / "tasmota" / "user_config_override.h").read_text(encoding="utf-8").splitlines(keepends=True)
    bornes = None
    for l in lignes:
        m = re.match(r" {8}#(?:el)?if\b.*?defined\(\s*(\w+)\s*\)", l)
        bornes = m and c._section_h(lignes, m.group(1))
        if bornes:
            break
    if not bornes:
        verifie("absente", "trouvee", "aller_retour : section .h reelle")
        return
    reel = lignes[bornes[0]:bornes[2]]
    cle = [l.rstrip() for l in reel]
    sur = [i for i in range(1, len(reel) - 1) if cle[i] and all(cle.count(cle[k]) == 1 for k in (i - 1, i, i + 1))]
    choix = []
    for i in sur:
        if not choix or i - choix[-1] >= 3:
            choix.append(i)
    if len(choix) < 3:
        verifie(len(choix), ">= 3", "aller_retour : lignes uniques disponibles")
        return
    i0, i1, i2 = choix[:3]
    b = list(reel)
    b[i0] = reel[i0].rstrip("\r\n") + " //x" + reel[i0][len(reel[i0].rstrip("\r\n")):]
    b.insert(i1 + 1, "        // ligne ajoutee par le banc\n")
    del b[i2 + 1]                       # i2 decale de 1 par l'insertion
    aller, refus = d.applique_lignes(reel, reel, b)
    verifie((aller == b, refus), (True, []), "aller_retour : A -> B")
    retour, refus = d.applique_lignes(aller, b, reel)
    verifie((retour == reel, refus), (True, []), "aller_retour : B -> A redonne le reel")


def principal():
    import assistant_persist_delta as d

    a = ["l1\n", "l2\n", "l3\n"]
    reel = ["l1\r\n", "main\n", "l2 \n", "l3\n"]

    verifie(d.applique_lignes(reel, a, a), (reel, []), "ecart_vide")
    r, refus = d.applique_lignes(reel, a, ["l1\n", "l2\n", "l3 bis\n"])
    verifie(r, ["l1\r\n", "main\n", "l2 \n", "l3 bis\n"], "ligne_ajoutee_a_la_main_gardee : texte")
    verifie(r[0] is reel[0], True, "ligne_ajoutee_a_la_main_gardee : lignes hors bloc identiques")
    verifie(refus, [], "ligne_ajoutee_a_la_main_gardee : aucun refus")
    verifie(d.applique_lignes(reel, a, ["l1\n", "neuf\n", "l2\n", "l3\n"])[0], ["l1\r\n", "neuf\n", "main\n", "l2 \n", "l3\n"],
            "insert_apres : pose apres l'ancre de a")
    verifie(d.applique_lignes(reel, a, ["neuf\n"] + a)[0], ["neuf\n"] + reel, "insert_en_tete")
    verifie(d.applique_lignes(reel, a, a + ["fin\n"])[0], reel + ["fin\n"], "insert_en_fin")
    verifie(d.applique_lignes(reel, [], ["x\n"])[0], reel + ["x\n"], "insert_a_vide : apres la fin de reel")
    verifie(d.applique_lignes(reel, a, ["l1\n", "l3\n"]), (["l1\r\n", "main\n", "l3\n"], []), "delete")
    verifie(d.applique_lignes(reel, a, ["l1\n", "L2\n", "l3\n"])[0], ["l1\r\n", "main\n", "L2\n", "l3\n"], "replace")

    r, refus = d.applique_lignes(["l1\n", "l3\n"], a, ["l1\n", "l2 bis\n", "l3\n"])
    verifie((r, len(refus), "l2" in refus[0] if refus else None), (["l1\n", "l3\n"], 1, True), "bloc_introuvable : refuse et cite")
    r, refus = d.applique_lignes(["l2\n", "x\n", "l2\n"], ["l2\n"], ["l2 bis\n"])
    verifie((len(refus), r), (1, ["l2\n", "x\n", "l2\n"]), "bloc_ambigu : refuse")
    r, refus = d.applique_lignes(["l1\n", "x\n", "l1\n"], ["l1\n"], ["l1\n", "n\n"])
    verifie(len(refus), 1, "insert_ancre_ambigue : refuse")
    r, refus = d.applique_lignes(["z\n"], a, a + ["n\n"])
    verifie(len(refus), 1, "insert_ancre_absente : refuse")
    r, refus = d.applique_lignes(["l1\n", "main\n", "l2\n", "l3\n"], a, ["l1\n", "n\n", "l2\n", "m\n", "l3\n"])
    verifie((r, refus), (["l1\n", "n\n", "main\n", "l2\n", "m\n", "l3\n"], []), "deux_blocs : indices non decales")
    r, refus = d.applique_lignes(["l1\n", "l2\n"], ["l1\n", "l2\n"], ["l1\n", "n\n", "m\n", "l2\n"])
    verifie((len(refus), r), (0, ["l1\n", "n\n", "m\n", "l2\n"]), "insert_multiligne")

    aller_retour_h(d)
    print("\nVERT" if not ECHECS else f"\nROUGE : {len(ECHECS)} echec(s)")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(principal())
