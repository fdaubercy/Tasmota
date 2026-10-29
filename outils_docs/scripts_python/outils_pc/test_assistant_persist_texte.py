"""Banc de assistant_persist_texte (ecart et edition d'un JSON dans son texte). Code de sortie 0 = vert.

Les vrais _persist.json sont lus en lecture seule ; rien n'est affiche de leur contenu.
"""

import json
import os
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


def tout(texte, ops, libelle):
    """applique + json.loads valide ; rend le nouveau texte."""
    import assistant_persist_texte as t
    r = t.applique(texte, ops)
    try:
        json.loads(r)
    except ValueError:
        verifie("invalide", "valide", libelle + " : json.loads")
    return r


def principal():
    import assistant_persist_texte as t

    # ---- remplace : seuls les octets de la valeur changent ----
    base = '{\n\t"a": "x",\n\t"n": 12,\n\t"l": [1, 2],\n\t"z": true\n}'
    for cle, v, vieux in (("a", "yy", '"x"'), ("n", 7, "12"), ("l", [3], "[1, 2]")):
        av = {"a": "x", "n": 12, "l": [1, 2]}
        r = tout(base, t.ecart(av, {**av, cle: v}), "remplace")
        i = base.index(vieux)
        verifie((r[:i], r[len(r) - (len(base) - i - len(vieux)):]), (base[:i], base[i + len(vieux):]), f"remplace_{cle} : octets hors valeur intacts")
        verifie(json.loads(r)[cle], v, f"remplace_{cle} : valeur")

    # ---- ajoute : indentation et fins de ligne du fichier ----
    tab = '{\r\n\t"a": 1,\r\n\t"o": {\r\n\t\t"b": 2\r\n\t}\r\n}'
    r = tout(tab, [(("o", "c"), "ajoute", "v")], "ajoute_tab_crlf")
    verifie(r, '{\r\n\t"a": 1,\r\n\t"o": {\r\n\t\t"b": 2,\r\n\t\t"c": "v"\r\n\t}\r\n}', "ajoute_tab_crlf : texte")
    esp = '{\n    "a": 1\n}'
    r = tout(esp, [(("d",), "ajoute", {"x": 1, "y": [2]})], "ajoute_4_espaces_lf")
    verifie(r, '{\n    "a": 1,\n    "d": {\n        "x": 1,\n        "y": [\n            2\n        ]\n    }\n}', "ajoute_4_espaces_lf : texte")
    r = tout('{\n    "a": 1,\n    "o": {}\n}', [(("o", "k"), "ajoute", 1)], "ajoute_objet_vide")
    verifie(r, '{\n    "a": 1,\n    "o": {\n        "k": 1\n    }\n}', "ajoute_objet_vide : texte")

    # ---- retire : virgules ----
    trois = '{\n\t"a": 1,\n\t"b": 2,\n\t"c": 3\n}'
    verifie(tout(trois, [(("c",), "retire", None)], "retire_dernier"), '{\n\t"a": 1,\n\t"b": 2\n}', "retire_dernier")
    verifie(tout(trois, [(("b",), "retire", None)], "retire_milieu"), '{\n\t"a": 1,\n\t"c": 3\n}', "retire_milieu")
    verifie(tout(trois, [(("a",), "retire", None)], "retire_premier"), '{\n\t"b": 2,\n\t"c": 3\n}', "retire_premier")
    verifie(json.loads(tout('{\n\t"a": 1\n}', [(("a",), "retire", None)], "retire_seul")), {}, "retire_seul")
    verifie(tout(trois, [(("zz",), "retire", None)], "retire_absent"), trois, "retire_absent : ignore")

    # ---- objet parcouru : cle absente du modele conservee ----
    txt = '{\n\t"a": {\n\t\t"b": {\n\t\t\t"c": 1,\n\t\t\t"propre": "p"\n\t\t}\n\t}\n}'
    ops = t.ecart({"a": {"b": {"c": 1}}}, {"a": {"b": {"c": 2}}})
    verifie(ops, [(("a", "b", "c"), "remplace", 2)], "objet_parcouru : ecart")
    r = tout(txt, ops, "objet_parcouru")
    verifie(json.loads(r), {"a": {"b": {"c": 2, "propre": "p"}}}, "objet_parcouru : propre gardee")

    # ---- ecart : ordre et nature ----
    verifie(t.ecart({"x": 1, "y": 2}, {"n": 0, "x": 3}),
            [(("n",), "ajoute", 0), (("x",), "remplace", 3), (("y",), "retire", None)], "ecart : ordre b puis retraits")
    verifie(t.ecart({"l": [1]}, {"l": [1]}), [], "ecart : liste egale")
    verifie(t.ecart({"l": {"a": 1}}, {"l": [1]}), [(("l",), "remplace", [1])], "ecart : dict -> liste en bloc")

    # ---- remplace d'une cle absente = ajoute ; parent absent = LookupError ----
    verifie(json.loads(t.applique(trois, [(("q",), "remplace", 9)]))["q"], 9, "remplace absent -> ajoute")
    try:
        t.applique(trois, [(("nul", "q"), "ajoute", "MOTDEPASSE")])
        verifie("rien", "LookupError", "parent absent")
    except LookupError as e:
        verifie(("nul.q" in str(e), "MOTDEPASSE" in str(e)), (True, False), "parent absent : chemin nomme, jamais la valeur")
    verifie(t.ecart_applicable(trois, [(("nul", "q"), "ajoute", 1), (("a",), "remplace", 1)]), ["nul.q"], "ecart_applicable")

    # ---- aller-retour ----
    a = {"a": 1, "o": {"b": "x", "l": [1, 2]}}
    b = {"a": 2, "o": {"b": "x", "l": [1, 2], "n": {"k": True}}, "z": "é"}
    for libelle, txt in (("tab", '{\n\t"a": 1,\n\t"o": {\n\t\t"b": "x",\n\t\t"l": [1, 2]\n\t}\n}'),
                         ("crlf4", '{\r\n    "a": 1,\r\n    "o": {\r\n        "b": "x",\r\n        "l": [1, 2]\r\n    }\r\n}')):
        aller = tout(txt, t.ecart(a, b), "aller_retour_" + libelle)
        verifie(t.applique(aller, t.ecart(b, a)), txt, "aller_retour_" + libelle)

    # ---- accents non echappes ----
    r = t.applique('{\n\t"a": 1\n}', [(("m",), "ajoute", "é")])
    verifie(('"é"' in r, "\\u" in r), (True, False), "accents : gardes non echappes")

    # ---- vrais persists : aucun ecart = octets identiques ----
    n = 0
    for p in sorted((RACINE / "data").glob("*/*/_persist.json")):
        if "sauvegarde" in p.parent.name:
            continue
        txt = p.read_bytes().decode("utf-8-sig")
        n += 1
        if t.applique(txt, []) != txt:
            verifie("different", "identique", f"vrai persist #{n}")
    verifie(n > 0, True, f"vrais_persists : {n} fichiers lus, applique(t, []) identique")

    print(f"\n{len(ECHECS)} echec(s)")
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(principal())
