r"""Banc de la page /energie PILOTEE PAR SA DESCRIPTION (plan energie-atelier A3) : rendu dans Chrome.

    python outils_docs/scripts_python/berry/banc_energie_description.py

Code de sortie 0 si tout est vert. La page (css, html, js reels) est servie par les outils de banc_energie.py avec une description
(`/energie?f=description`) et des archives (`f=mois`) fabriquees ici. La page SANS description (celle d'aujourd'hui) est jugee par
banc_energie.py ; la validation par test_energie_rendu.mjs. Ne teste pas la vraie carte (ni routes Berry, ni RAM).
"""
import json
import re
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import banc_energie as B
from banc_cuve_page import BUDGET_MS, DELAI_S, trouve_navigateur

BASE = {"aujourdhui": "2026-11-02", "prix": [["2026-10-01", 2000]], "wCourant": 1000, "courbe": [],
        "etat": {"m": "2026-11", "j": "2026-11-02", "l": 1793577600 + 10 * 3600, "w": 1000,
                 "h": [0] * 24, "he": [0] * 24, "d": [0] * 31, "de": [0] * 31, "a": []}}
DIRECT = {"p": 750, "i": 3.25, "f": 0.87, "hz": 50}


def el(type, titre, source, **kw):
    return {"type": type, "titre": titre, "source": source, "couleur": "#4a9eda", "largeur": "demi", "hauteur": "petite", **kw}


def desc(*elements):
    return json.dumps({"version": 1, "elements": list(elements)}, ensure_ascii=False, separators=(",", ":"))


def rendu(nav, tmp, nom, donnees, description, direct=DIRECT, mois=None, js=None):
    dom, _ = B.scenario(nav, tmp, nom, B.page_html(js), donnees, direct, description=description, mois=mois)
    return dom


def vers_json(dom, ident):
    return json.loads(B.attribut(dom, ident, "data-valeurs") or "null")


def note(dom):
    return B.texte(dom, "e_note")


def mesure_390(nav, tmp, nom, donnees, description, css=None):
    """Page au corps NON contraint dans un cadre de 390 px (Chrome sans fenetre ne descend pas sous 500 px), mesuree quand data-pret est pose :
    (scrollWidth, largeur du cadre, colonnes) ; None si la mesure n'a pas eu lieu."""
    srv, _ = B.serveur(B.page_html(css_modifie=css, corps="margin:0"), donnees, DIRECT, description=description)
    r = subprocess.run([nav, "--headless=new", "--disable-gpu", "--no-first-run", "--lang=fr-FR", f"--user-data-dir={tmp / ('profil_' + nom)}",
                        f"--virtual-time-budget={BUDGET_MS}", "--dump-dom", f"http://127.0.0.1:{srv.server_address[1]}/capture?w=390"], capture_output=True, timeout=DELAI_S)
    srv.shutdown()
    m = re.search(r'data-mesure="(\d+)/(\d+)/(\d+)"', r.stdout.decode("utf-8", "replace"))
    return tuple(int(x) for x in m.groups()) if m else None


DESC_390 = desc(el("valeur", "M" * 40, {"direct": "Power"}, unite="W"), el("cadran", "Facteur", {"direct": "Factor"}, min=0, max=1),
                el("barres", "Heures", {"flash": "heure", "grandeur": "kWh"}, largeur="pleine", hauteur="moyenne"),
                el("courbe", "Puissance", {"flash": "minutes"}, largeur="pleine", hauteur="grande"))


def partie(nav, tmp):
    ok = True
    d = B.complet(BASE)
    e = d["etat"]
    e["d"] = [10 * (i + 1) for i in range(31)]
    oct_ = {"d": [7 * (i + 1) for i in range(31)], "de": [i for i in range(31)]}
    sept = {"d": [3 * (i + 1) for i in range(30)] + [0], "de": [0] * 31}

    print("--- Description modifiee : ordre, couleur, hauteur, total, demi-cercle")
    dom = rendu(nav, tmp, "ordre", d, desc(
        el("barres", "Cout par heure", {"flash": "heure", "grandeur": "euros"}, couleur="#ff0000", largeur="pleine", hauteur="grande", total=True),
        el("valeur", "Puissance", {"direct": "Power"}, couleur="#00aa00", unite="W"),
        el("demi-cercle", "Facteur", {"direct": "Factor"}, min=0, max=1)))
    ok &= B.juge("graphique en premier", True, 0 <= dom.find('id="e_g0"') < dom.find('id="e_el1"') < dom.find('id="e_el2"'))
    ok &= B.juge("barres des euros", e["he"], vers_json(dom, "e_g0"))
    ok &= B.juge("couleur des barres", True, 'fill="#ff0000"' in dom)
    ok &= B.juge("hauteur grande", True, bool(re.search(r'id="e_g0"[^>]*viewBox="0 0 320 140"', dom) or re.search(r'viewBox="0 0 320 140"[^>]*id="e_g0"', dom)))
    ok &= B.juge("pleine largeur", True, "e_pleine" in dom and "e_h_grande" in dom)
    ok &= B.juge("total : kWh et euros dans le titre", "2,68 kWh · 0,08 €", B.texte(dom, "e_t0"))
    ok &= B.juge("total en Wh et dix-milliemes", ("2676", "756"), (B.attribut(dom, "e_t0", "data-wh"), B.attribut(dom, "e_t0", "data-euros")))
    ok &= B.juge("couleur de la valeur", True, "00aa00" in dom.lower())
    ok &= B.juge("valeur", "750", B.texte(dom, "e_v1"))
    ok &= B.juge("demi-cercle : arc au facteur", ("87 100", "40"), (B.attribut(dom, "e_a2", "stroke-dasharray"), B.attribut(dom, "e_a2", "stroke-width")))

    print("--- Jour : mois decale, mois fixe, archive effacee")
    mois = {"2026-10": oct_, "2026-09": sept}
    dom = rendu(nav, tmp, "decalage", d, desc(
        el("barres", "Octobre", {"flash": "jour", "grandeur": "kWh", "decalage": 1}, largeur="pleine", hauteur="moyenne"),
        el("courbe", "Septembre", {"flash": "jour", "grandeur": "kWh", "mois": "2026-09"}, largeur="pleine", hauteur="moyenne")), mois=mois)
    ok &= B.juge("decalage 1 = octobre (31 jours)", oct_["d"], vers_json(dom, "e_g0"))
    ok &= B.juge("mois fixe = septembre (30 jours)", sept["d"][:30], vers_json(dom, "e_g1"))
    dom = rendu(nav, tmp, "purge", d, desc(
        el("barres", "Aout", {"flash": "jour", "grandeur": "kWh", "mois": "2026-08"}, largeur="pleine", hauteur="moyenne"),
        el("valeur", "Puissance", {"direct": "Power"}, unite="W")), mois={})
    ok &= B.juge("archive effacee dite", True, "archive effacée" in dom)
    ok &= B.juge("la page continue (tuile tracee)", "750", B.texte(dom, "e_v1"))
    ok &= B.juge("aucune ligne de repli", None, note(dom) or None)

    print("--- An : la plus ancienne annee, partielle, est marquee")
    an = B.complet(BASE)
    an["etat"]["a"] = [[f"2025-{m:02d}", m * 1000, m * 100] for m in range(3, 13)] + [[f"2026-{m:02d}", m * 2000, m * 200] for m in range(1, 12)]
    dom = rendu(nav, tmp, "an", an, desc(el("barres", "Par annee", {"flash": "an", "grandeur": "kWh"}, largeur="pleine", hauteur="moyenne")))
    ok &= B.juge("deux annees civiles", [sum(m * 1000 for m in range(3, 13)), sum(m * 2000 for m in range(1, 12))], vers_json(dom, "e_g0"))
    ok &= B.juge("2025 marquee partielle", True, ">2025*<" in dom and "année partielle" in dom)
    ok &= B.juge("2026 non marquee", True, ">2026<" in dom)

    print("--- Repli : 5 000 octets, JSON tronque, ancien firmware, element ou version refuses")
    defaut = desc(el("valeur", "Puissance", {"direct": "Power"}, unite="W"))
    dom = rendu(nav, tmp, "gros", d, defaut + " " * (5000 - len(defaut)))
    ok &= B.juge("5 000 octets : repli dit", True, (note(dom) or "").startswith("Description ignorée") and "octets" in (note(dom) or ""))
    ok &= B.juge("5 000 octets : page d'aujourd'hui", d["etat"]["h"], vers_json(dom, "e_g4"))
    dom = rendu(nav, tmp, "tronque", d, defaut[:-6])
    ok &= B.juge("JSON tronque : repli dit", True, "tronqué" in (note(dom) or ""))
    ok &= B.juge("JSON tronque : page d'aujourd'hui", d["etat"]["h"], vers_json(dom, "e_g4"))
    dom = rendu(nav, tmp, "html", d, "<!doctype html><html><body>page</body></html>")
    ok &= B.juge("ancien firmware (HTML en 200) : repli dit", True, "Description ignorée" in (note(dom) or ""))
    dom = rendu(nav, tmp, "absente", d, None)
    ok &= B.juge("description absente : dite", "Description absente : disposition par défaut.", note(dom))
    dom = rendu(nav, tmp, "element", d, desc(el("valeur", "Puissance", {"direct": "Power"}, unite="W"), el("zigzag", "Autre", {"direct": "Power"})))
    ok &= B.juge("element refuse : dit, l'autre garde sa place", ("Élément 2 ignoré : type inconnu", "750"), (note(dom), B.texte(dom, "e_v0")))
    dom = rendu(nav, tmp, "version", d, defaut.replace('"version":1', '"version":2'))
    ok &= B.juge("version 2 : toute la description ecartee", True, "Description ignorée : version" in (note(dom) or "") and vers_json(dom, "e_g4") == d["etat"]["h"])

    print("--- Champ direct absent ou present hors p/i/f/hz")
    dom = rendu(nav, tmp, "absent", d, desc(el("valeur", "Hier", {"direct": "Yesterday"}, unite="kWh"), el("valeur", "Tension", {"direct": "Voltage"}, unite="V"),
                                            el("valeur", "Aujourd'hui", {"direct": "Today"}, unite="kWh")), direct={**DIRECT, "Voltage": 230.44, "Today": 1.2345})
    ok &= B.juge("Yesterday absent : « -- »", "--", B.texte(dom, "e_v0"))
    ok &= B.juge("Voltage present", "230,4", B.texte(dom, "e_v1"))
    ok &= B.juge("Today present (3 decimales)", "1,234", B.texte(dom, "e_v2"))

    print("--- Telephone 390 px")
    mesure = mesure_390(nav, tmp, "390", d, DESC_390)
    ok &= B.juge("mesure faite apres data-pret", True, mesure is not None)
    ok &= B.juge("cadre de 390 px", 390, mesure and mesure[1])
    ok &= B.juge("une colonne", 1, mesure and mesure[2])
    ok &= B.juge("aucun defilement horizontal (scrollWidth <= largeur)", True, bool(mesure) and mesure[0] <= mesure[1])
    return ok


def temoins(nav, tmp):
    """Chaque mutant doit rendre rouge le test qu'il vise (le rendu reste servi par le vrai energie.js, copie mutee)."""
    ok = True
    js = (B.RACINE / "data/sd/js/energie.js").read_text(encoding="utf-8")
    d = B.complet(BASE)
    print("--- Temoins (doivent etre rouges)")
    oct_ = {"d": [7 * (i + 1) for i in range(31)], "de": [0] * 31}
    sept = {"d": [3 * (i + 1) for i in range(30)] + [0], "de": [0] * 31}
    mois = {"2026-10": oct_, "2026-09": sept}
    tuiles = desc(el("valeur", "Puissance", {"direct": "Power"}, unite="W"), el("zigzag", "Autre", {"direct": "Power"}))
    ordre = desc(el("barres", "Cout par heure", {"flash": "heure", "grandeur": "euros"}, couleur="#ff0000", largeur="pleine", hauteur="grande", total=True),
                 el("demi-cercle", "Facteur", {"direct": "Factor"}, min=0, max=1))
    purge = desc(el("barres", "Aout", {"flash": "jour", "grandeur": "kWh", "mois": "2026-08"}))
    mutants = [
        ("borne des octets levee", "if (n > OCTETS)", "if (false)", "gros", d, desc(el("valeur", "P", {"direct": "Power"})) + " " * 5000,
         lambda dom: "octets" in (note(dom) or "")),
        ("JSON tronque accepte comme illisible sans le dire", "JSON illisible ou tronqué", "JSON illisible", "tronque", d, desc(el("valeur", "P", {"direct": "Power"}))[:-6],
         lambda dom: "tronqué" in (note(dom) or "")),
        ("version non controlee", "d.version !== 1", "false", "version", d, desc(el("valeur", "P", {"direct": "Power"})).replace('"version":1', '"version":2'),
         lambda dom: "version" in (note(dom) or "")),
        ("element refuse ecarte toute la description", r"var q = /^element (\d+) : /.exec(x);", "var q = null;", "element", d, tuiles,
         lambda dom: (note(dom) or "").startswith("Élément 2 ignoré") and B.texte(dom, "e_v0") == "750"),
        ("couleur des barres ignoree", "<rect fill='\" + c +", "<rect fill='\" + BLEU +", "couleur", d, ordre, lambda dom: 'fill="#ff0000"' in dom),
        ("hauteur grande ignoree", "grande: 140", "grande: 90", "hauteur", d, ordre, lambda dom: 'viewBox="0 0 320 140"' in dom),
        ("total sans euros", "' · ' + euros(somme(s.E))", "''", "total", d, ordre, lambda dom: B.texte(dom, "e_t0") == "2,68 kWh · 0,08 €"),
        ("demi-cercle dessine comme un cadran", "(dem ? 40 : 9)", "9", "demi", d, ordre, lambda dom: B.attribut(dom, "e_a1", "stroke-width") == "40"),
        ("decalage ignore", "(s.decalage || 0)", "0", "decalage", d, desc(el("barres", "Octobre", {"flash": "jour", "grandeur": "kWh", "decalage": 1})),
         lambda dom: vers_json(dom, "e_g0") == oct_["d"]),
        ("mois fixe ignore", "if (s.mois) return s.mois;", "", "fixe", d, desc(el("courbe", "Septembre", {"flash": "jour", "grandeur": "kWh", "mois": "2026-09"})),
         lambda dom: vers_json(dom, "e_g0") == sept["d"][:30]),
        ("archive effacee non dite", "'archive effacée'", "''", "purge", d, purge, lambda dom: "archive effacée" in dom),
        ("partielle jamais marquee", "r.part = 0;", "", "an", {**B.complet(BASE), "etat": {**d["etat"], "a": [["2025-03", 1, 1], ["2026-01", 2, 2]]}},
         desc(el("barres", "An", {"flash": "an", "grandeur": "kWh"})), lambda dom: ">2025*<" in dom),
        ("annees non civiles", ".slice(-2);", ".slice(-3);", "ans", {**B.complet(BASE), "etat": {**d["etat"], "a": [["2024-12", 1, 1], ["2025-03", 1, 1], ["2026-01", 2, 2]]}},
         desc(el("barres", "An", {"flash": "an", "grandeur": "kWh"})), lambda dom: len(vers_json(dom, "e_g0")) == 2),
        ("champ direct absent affiche 0", "t = '--'", "t = '0'", "absent", d, desc(el("valeur", "Hier", {"direct": "Yesterday"}, unite="kWh")),
         lambda dom: B.texte(dom, "e_v0") == "--"),
    ]
    for nom, avant, apres, scen, donnees, description, juge in mutants:
        assert avant in js, nom
        dom = rendu(nav, tmp, "t_" + scen, donnees, description, mois=mois, js=js.replace(avant, apres))
        rouge = bool(dom) and not juge(dom)
        print(f"  {'OK   ' if rouge else 'ECHEC'} {nom}")
        ok &= rouge
    css = (B.RACINE / "data/sd/css/energie.css").read_text(encoding="utf-8")
    rouge = True
    for nom, avant, apres, juge in [
            ("une colonne sous 600 px retiree", "max-width:599px", "max-width:1px", lambda m: m[2] == 1),
            ("largeur fixe de 500 px sur les elements", ".e_el{min-width:0;overflow-wrap:anywhere}", ".e_el{width:500px}", lambda m: m[0] <= m[1]),
            ("min-width:0 et retour a la ligne retires", ".e_el{min-width:0;overflow-wrap:anywhere}", ".e_el{}", lambda m: m[0] <= m[1])]:
        assert avant in css, nom
        m = mesure_390(nav, tmp, "t390", d, DESC_390, css=css.replace(avant, apres))
        r = m is not None and not juge(m)
        print(f"  {'OK   ' if r else 'ECHEC'} {nom} : {m}")
        rouge &= r
    return ok and rouge


def main():
    nav = trouve_navigateur()
    if nav is None:
        print("ECHEC : aucun navigateur, rendu non verifie")
        return 1
    tmp = Path(tempfile.mkdtemp(prefix="banc_energie_desc_"))
    try:
        ok = partie(nav, tmp)
        ok = temoins(nav, tmp) and ok
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("BANC_ENERGIE_DESCRIPTION: " + ("OK" if ok else "ECHEC"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
