r"""Banc de la carte d'AFFICHAGE des debits (carte tasmota32s3-bureau-ecran-debits-pac) : banc_ecran_debits.be, puis temoins
sur des copies du module des debits, du generique d'ecran, du driver et de l'interface HASPmota.

    python outils_docs/scripts_python/berry/banc_ecran_debits.py

Code de sortie 0 si tout est vert. Ne teste pas la vraie carte : ni le releve ModBus, ni le push, ni HASPmota/LVGL reels
(objets de pages.jsonl simules), ni l'expandeur I2C 0x24 reel (sens du PWM), ni le rendu sur l'ecran (essais sur cartes du
plan debits-deux-cartes, A6 et A8). Les entrees analogiques sont posees a la main comme les range modBus_TasmotaSlaveModBus
(banc_test_modbus.py couvre le releve groupe et la repartition du push).
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
BERRY = RACINE / "lib/libesp32/berry/berry.exe"
BANC = "outils_docs/scripts_python/berry/banc_ecran_debits.be"
CARTE = RACINE / "data/bureau/tasmota32s3-ecran-debits-pac"
MODULE = CARTE / "ecranDebitsFonctions.be"
DRIVER = CARTE / "controleEcranDebits.be"
INTERFACE = CARTE / "ecranHaspmota.be"
GENERIQUE = CARTE / "ecranFonctions.be"
VERT = "BANC_ECRAN_DEBITS: OK"
PAGES = CARTE / "pages.jsonl"
ECRAN_JSON = RACINE / "outils_docs/atelier_ecrans/cartes/tasmota32s3-bureau-ecran-debits-pac/ecran.json"
CONF_LV = RACINE / "tasmota/lvgl_berry/tasmota_lv_conf.h"

# Chaque mutant doit rendre le banc rouge : (nom, texte du module, remplacement). Module des debits ecranDebitsFonctions.be :
MUTANTS = [
    ("centiemes pris pour des L/min", "v == nil ? nil : v / 100.0", "v == nil ? nil : v / 1.0"),
    ("etatConstate ignore", 'e.find("etatConstate") != "valide"', "false"),
    ("fraicheur d'une seule fenetre", 'now - t > 2 * ecranDebitsFonctions.reglage("fenetre")', 'now - t > ecranDebitsFonctions.reglage("fenetre")'),
    ("fraicheur jamais controlee", 'now - t > 2 * ecranDebitsFonctions.reglage("fenetre")', "false"),
    ("fraicheur trop lache (3 fenetres)", 'now - t > 2 * ecranDebitsFonctions.reglage("fenetre")', 'now - t > 3 * ecranDebitsFonctions.reglage("fenetre")'),
    ("sentinelle affichee comme un debit", "v != modbusFonctions.SENTINELLE_UINT32", "true"),
    ("fenetre sans ses bornes", "    var b = ecranDebitsFonctions.BORNES.find(cle)\n", "    var b = nil\n"),
    ("bit muet decale", "muets.push(w != nil && (w & (1 << i)) != 0)", "muets.push(w != nil && (w & (1 << (i + 1))) != 0)"),
    ("bit imprecis decale", "imprecis.push(w != nil && (w & (1 << (6 + i))) != 0)", "imprecis.push(w != nil && (w & (1 << (7 + i))) != 0)"),
    ("mot d'etats perime cru", 'return {"frais": w != nil,', 'return {"frais": true,'),
    ("voie muette non signalee", 'if (muet)    return {"debit": "muet", "unite": "", "part": "", "barre": 0, "etat": "muet"}    end', ""),
    ("voie inconnue affichee 0", 'if (q == nil)    return {"debit": "-,--", "unite": "L/min", "part": "", "barre": 0, "etat": "inconnu"}    end',
     "if (q == nil)    q = 0.0    end"),
    ("voie a l'arret affichee normale", 'if (q <= 0)    return {"debit": "0,00", "unite": "L/min", "part": "arrêt", "barre": 0, "etat": "arret"}    end', ""),
    ("imprecis non colore", 'imprecis ? "imprecis" : "normal"', '"normal"'),
    ("point decimal au lieu de la virgule", 'string.tr(string.format(fmt, q), ".", ",")', "string.format(fmt, q)"),
    ("total partiel non marque", '(tt[1] < ecranDebitsFonctions.NB_VOIES ? " (partiel)" : "")', '""'),
    ("total sans voie connue", 'var total = "Total inconnu"', 'var total = "Total 0,0 L/min"'),
    ("barre en valeur absolue", "int(q * 100 / max + 0.5)", "int(q * 100 / 5 + 0.5)"),
    ("nom du persist ignore", 'str(ent.find("nom", "Débit " + str(i + 1)))', '"Débit " + str(i + 1)'),
    ("age du premier releve, pas du plus recent", "(t == nil || c > t)", "t == nil"),
    ("releve date du futur compte", "c <= now &&", ""),
    ("pastille toujours verte", '? "vert" : "muet"', '? "vert" : "vert"'),
    ("releve jamais en minutes", "age < 120 ?", "true ?"),
    ("message fenetre a chaque seconde", "if (toutes && !ecranDebitsFonctions.toutesInconnues)", "if (toutes)"),
    ("message fenetre des le demarrage", "ecranDebitsFonctions.toutesInconnues = true   #", "ecranDebitsFonctions.toutesInconnues = false   #"),
    ("message fenetre en erreur", '(ReglageEcranDebits fenetre) ?", LOG_LEVEL_DEBUG)', '(ReglageEcranDebits fenetre) ?", LOG_LEVEL_ERREUR)'),
    ("message fenetre jamais re-arme", "    ecranDebitsFonctions.toutesInconnues = toutes\n",
     "    ecranDebitsFonctions.toutesInconnues = ecranDebitsFonctions.toutesInconnues || toutes\n"),
    ("modele seulement avec un ecran",
     '    var m = ecranDebitsFonctions.modele(tasmota.rtc()["local"])\n    if (ecranFonctions.interface != nil)    ecranFonctions.interface.affiche(m)    end',
     '    if (ecranFonctions.interface != nil)    ecranFonctions.interface.affiche(ecranDebitsFonctions.modele(tasmota.rtc()["local"]))    end'),
    ("historique : inconnu trace a 0", "cent.push(q == nil ? nil :", "cent.push(q == nil ? 0 :"),
    ("axe sans minimum de 10 L/min", "hm < 1000 ? 1000 : hm", "hm"),
    ("axe non arrondi", "((ecranFonctions.histoMax() + 199) / 200) * 200", "ecranFonctions.histoMax()"),
    ("fenetre 1 acceptee", '"fenetre": [2, 60, 10, "s"]', '"fenetre": [1, 60, 10, "s"]'),
    ("bouton sans retour dans les bornes", "n < b[0] ? b[0] : (n > b[1] ? b[1] : n)", "n"),
    ("pwmInverse invalide accepte", 'if (arg != "ON" && arg != "OFF")', "if (false)"),
    ("pwmInverse non reapplique", "            persist.save(true)\n            ecranFonctions.etatVeille = nil\n", "            persist.save(true)\n"),
    ("objets neufs non remplis au demarrage", "    ecranDebitsFonctions.ecran()\n    return true", "    return true"),
]
# Temoins du generique d'ecran ecranFonctions.be
MUTANTS_GENERIQUE = [
    ("polices jamais rangees au demarrage", "    ecranFonctions.rangePolices()                # avant l'interface", "    # avant l'interface"),
    ("polices rangees hors de /sd/polices", 'ecranFonctions.POLICES = "/sd/polices/"', 'ecranFonctions.POLICES = "/polices/"'),
    ("dossier des polices jamais cree", "            path.mkdir(ecranFonctions.POLICES[0 .. -2])\n", ""),
    ("/sd jamais cree (carte sans SD)", '            path.mkdir("/sd")\n', ""),
    ("tous les fichiers de la racine pris pour des polices", 'string.endswith(n, ".ttf", true)', "true"),
    ("reglage illisible accepte", 'return (type(v) == "int" && v >= b[0] && v <= b[1]) ? v : b[2]', "return v"),
    ("reglage hors bornes accepte", "v >= b[0] && v <= b[1]", "true"),
    ("bloc du persist ignore", "return (b != nil && modules.contains(b)) ? modules[b] : {}", "return {}"),
    ("borne basse d'un reglage oubliee", "n < b[0] || n > b[1]", "n > b[1]"),
    ("veille sans borne haute", '"veille": [0, 120, 5, "min"]', '"veille": [0, 100000, 5, "min"]'),
    ("reglage non sauve", "    persist.save(true)   # true : modif imbriquee, save() seul n'ecrit rien\n", ""),
    ("reglage non reapplique", "    ecranFonctions.etatVeille = nil\n    return true", "    return true"),
    ("pwmInverse absent = OFF", 'find("pwmInverse", "ON") != "OFF"', 'find("pwmInverse", "OFF") == "ON"'),
    ("extinction coupe aussi l'alimentation de la dalle (EXIO6)", "ecranFonctions.ETEINT = 0xDB", "ecranFonctions.ETEINT = 0x9B"),
    ("tactile laisse en reset (EXIO1)", "ecranFonctions.ALLUME = 0xDF", "ecranFonctions.ALLUME = 0xDD"),
    ("extinction par le PWM", "ok = w.write(x, 0x03, ecranFonctions.ETEINT, 1)", "ok = w.write(x, 0x05, 255, 1)"),
    ("PWM non borne (extremes)", "        r = r < 5 ? 5 : (r > 97 ? 97 : r)\n", ""),
    ("sens du PWM ignore", "ecranFonctions.pwmInverse() ? 100 - pct : pct", "pct"),
    ("gradation a 25 %", "ecranFonctions.GRADATION = 10", "ecranFonctions.GRADATION = 25"),
    ("veille 0 assombrit quand meme", "if (v > 0 && ms >= v)", "if (ms >= v)"),
    ("extinction 0 eteint quand meme", "(x > 0 && ms >= v + x)", "(ms >= v + x)"),
    ("I2C ecrit a chaque appel", "    if (cible == ecranFonctions.etatVeille)    return    end\n", ""),
    ("erreur I2C repetee a chaque essai", "        if (!ecranFonctions.panne)\n            ecranFonctions.panne = true\n", "        if (true)\n            ecranFonctions.panne = true\n"),
    ("echec I2C jamais reessaye (etat memorise quand meme)", "    if (ecranFonctions.lumiere(pct))\n", "    ecranFonctions.etatVeille = cible\n    if (ecranFonctions.lumiere(pct))\n"),
    ("reessai a chaque tic de 250 ms", "    if (a != nil && t >= a && t - a < ecranFonctions.REESSAI)    return    end\n", ""),
    ("reessai jamais temporise (delai 0)", "ecranFonctions.REESSAI = 10000", "ecranFonctions.REESSAI = 0"),
    ("retablissement I2C en erreur", 'luminosite " + str(pct) + " % appliquee !", LOG_LEVEL_DEBUG)', 'luminosite " + str(pct) + " % appliquee !", LOG_LEVEL_ERREUR)'),
    ("retablissement I2C en info", 'luminosite " + str(pct) + " % appliquee !", LOG_LEVEL_DEBUG)', 'luminosite " + str(pct) + " % appliquee !", LOG_LEVEL_INFO)'),
    ("panne jamais effacee", "            ecranFonctions.panne = false\n", ""),
    ("echec I2C sans erreur", 'nouvel essai toutes les 10 s !", LOG_LEVEL_ERREUR)', 'nouvel essai toutes les 10 s !", LOG_LEVEL_DEBUG)'),
    ("persist ecrit a chaque appui", "        tasmota.remove_timer(ecranFonctions.ID_SAUVE)\n        tasmota.set_timer(ecranFonctions.DELAI_SAUVE, ecranFonctions.sauve, ecranFonctions.ID_SAUVE)\n    else\n        persist.save(true)\n    end",
     "        persist.save(true)\n    else\n        persist.save(true)\n    end"),
    ("timer empile a chaque appui (sans remove_timer)", "        tasmota.remove_timer(ecranFonctions.ID_SAUVE)\n", ""),
    ("delai du persist trop court (1 s)", "ecranFonctions.DELAI_SAUVE = 3000", "ecranFonctions.DELAI_SAUVE = 1000"),
    ("timer sans identifiant fixe", "ecranFonctions.sauve, ecranFonctions.ID_SAUVE)", "ecranFonctions.sauve, str(tasmota.millis()))"),
    ("commande differee (ecriture jamais faite)", "    else\n        persist.save(true)\n    end", "    else\n        0\n    end"),
    ("rappel du timer sans ecriture", "    import persist\n    persist.save(true)   # true : modif imbriquee, save() seul n'ecrit rien\nend", "    import persist\nend"),
    ("nom d'etat inconnu ignore en silence", 'raise "attribute_error", "ecranFonctions n\'a pas de " + str(nom)', "return false"),
    ("voile jamais pose", "ecranFonctions.poseVoile(cible < 100)", "ecranFonctions.poseVoile(false)"),
    ("voile hors de layer_sys", "lv.obj(lv.layer_sys())", "lv.obj(nil)"),
    ("voile non cliquable", "            p.set_clickable(true)\n", ""),
    ("veille sans ecran demarre", "    if (ecranFonctions.interface == nil)    return 0    end\n", ""),
    ("interface retenue malgre un echec", "if (itf == nil || !itf.demarre())    return false    end", "if (itf == nil)    return false    end\n    itf.demarre()"),
    ("interface compilee (.bec) ignoree", 'path.exists("/" + n + ".bec") || ', ""),
    ("interface en .be ignoree", ' || path.exists("/" + n + ".be")', ""),
    ("derniere interface retenue au lieu de la premiere", "return demarrage.importeUn(presents[0])", "return demarrage.importeUn(presents[-1])"),
    ("aucune interface sans erreur", 'ecran noir !", LOG_LEVEL_ERREUR)', 'ecran noir !", LOG_LEVEL_DEBUG)'),
    ("deux interfaces sans ligne info", 'retenue (custom_interface_ecran du cenv) !", LOG_LEVEL_INFO)', 'retenue (custom_interface_ecran du cenv) !", LOG_LEVEL_DEBUG)'),
    ("historique : pas de 1 s", "t - a < ecranFonctions.HISTO_PAS", "t - a < 1000"),
    ("historique sans limite", "        l.remove(0)\n", ""),
    ("points de l'historique non comptes", "    ecranFonctions.points = ecranFonctions.points + 1\n", ""),
]
# Temoins de l'interface ecranHaspmota.be
MUTANTS_INTERFACE = [
    ("chemin de pages.jsonl hors de /json/", 'ecranHaspmota.PAGES = "/json/pages.jsonl"', 'ecranHaspmota.PAGES = "/pages.jsonl"'),
    ("ecran absent : pas de test d'affichage", "if (!display.started())", "if (false)"),
    ("tout reecrit chaque seconde", "    if (ecranHaspmota.cache.find(cle) == val)    return    end\n", ""),
    ("cache garde sur des objets neufs", "        ecranHaspmota.cache = {}    # objets neufs : tout reecrire\n", ""),
    ("bouton sur l'appui (down)", '    if (valeur != "up")    return    end\n', ""),
    ("bouton + qui diminue", '"p3b24": ["fenetre", 1]', '"p3b24": ["fenetre", -1]'),
    ("regles des boutons non declarees", '            tasmota.add_rule("hasp#" + id + "#event", ecranHaspmota.bouton, "ecranHaspmota")\n', ""),
    ("series sur l'axe secondaire", "lv.CHART_AXIS_PRIMARY_Y))    end", "lv.CHART_AXIS_SECONDARY_Y))    end"),
    ("pastilles des points gardees", "    o.set_style_size(0, 0, lv.PART_INDICATOR)\n", ""),
    ("historique entier repousse a chaque seconde", 'var n = m["points"] - ecranHaspmota.points', 'var n = m["points"]'),
    ("trou de la courbe trace a 0", "v == nil ? lv.CHART_POINT_NONE : v", "v == nil ? 0 : v"),
    ("axe de la courbe fige", '        o.set_axis_range(lv.CHART_AXIS_PRIMARY_Y, 0, m["courbeMax"])\n', ""),
    ("bouton de la page courante fige", "var actif = haspmota.lvh_page_cur_idx == n", "var actif = n == 1"),
    ("barre imprecise en bleu", 'v["etat"] == "imprecis" ? c["imprecis"] : c["bleu"]', 'c["bleu"]'),
    ("nom jamais colore", 'var nom = (v["etat"] == "normal" || v["etat"] == "arret") ? c["normal"] : col', 'var nom = c["normal"]'),
    ("page Courbes sans debit", '        e("p2b" + str(b + 3), "text", v["debit"])\n', ""),
    ("page Reglages sans luminosite", '    e("p3b43", "text", r["luminosite"])\n', ""),
]
# Temoins du driver controleEcranDebits.be
MUTANTS_DRIVER = [
    ("commande non declaree", 'tasmota.add_cmd("ReglageEcranDebits", ecranDebitsFonctions.reglageEcranDebits)', ""),
    ("bloc du persist non pose", '        ecranFonctions.bloc = "ecranDebits"    # reglages de l\'ecran : modules.ecranDebits du persist\n', ""),
    ("interface non chargee", '            ecranDebitsFonctions.demarreEcran(ecranFonctions.charge(["ecranHaspmota", "ecranLvgl"]))\n', ""),
    ("LVGL prioritaire quand les deux sont la", '["ecranHaspmota", "ecranLvgl"]', '["ecranLvgl", "ecranHaspmota"]'),
    ("ecran non rafraichi chaque seconde", "            ecranDebitsFonctions.ecran()\n            self.retabli", "            0\n            self.retabli"),
    ("log info dans every_second", "            ecranDebitsFonctions.ecran()\n            self.retabli",
     "            ecranDebitsFonctions.ecran()\n            ecranDebitsFonctions.log('ECRAN_DEBITS: tic !', LOG_LEVEL_INFO)\n            self.retabli"),
    ("every_250ms sans try", "        try\n            ecranFonctions.suitVeille()", "        if true\n            ecranFonctions.suitVeille()"),
    ("erreur du driver a chaque tic", "        if (self.echecs.find(cle) == msg)    return    end\n", ""),
    ("message change ignore (erreur memorisee une fois)", "        self.echecs[cle] = msg\n", ""),
    # pas « 0 && f(...) » en instruction : le berry.exe des bancs boucle dessus (constate le 2026-11-11)
    ("retablissement jamais signale", 'ecranDebitsFonctions.log("CONTROLE_ECRAN_DEBITS: " + texte + " retabli !", LOG_LEVEL_DEBUG)', "0"),
    ("retablissement en erreur", 'texte + " retabli !", LOG_LEVEL_DEBUG)', 'texte + " retabli !", LOG_LEVEL_ERREUR)'),
    ("retablissement repete a chaque tic", "        self.echecs.remove(cle)\n", ""),
    ("veille non suivie", "        ecranFonctions.suitVeille()\n", ""),
]


def lance_berry(dossier, module="-", driver="-", interface="-", generique="-"):
    args = [str(BERRY), BANC, str(dossier), str(module), str(driver), str(interface), str(generique)]
    try:
        r = subprocess.run(args, cwd=RACINE, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                           stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return "BLOQUE : berry.exe arrete apres 120 s"    # jamais le mot du vert : un mutant qui boucle compte rouge
    return r.stdout + r.stderr


def fautes_polices(pages, conf, carte):
    """Fautes de police de pages.jsonl : chaque text_font est soit une taille de robotocondensed COMPILEE
    (`#define ROBOTOCONDENSED_REGULAR_<n>_LATIN1 1` de tasmota_lv_conf.h, sinon parse_font de HASPmota cherche roboto.ttf a la
    racine et garde la police du theme), soit "A:sd/polices/<nom>.ttf-<n>" dont la TTF est dans le dossier de la carte (rangee
    au demarrage par ecranFonctions.rangePolices ; sans / apres A: : lvbe_fopen l'ajoute)."""
    compilees = {int(n) for n in re.findall(r"^#define ROBOTOCONDENSED_REGULAR_(\d+)_LATIN1\s+1\b", conf, re.M)}
    fautes = []
    for i, l in enumerate(pages.splitlines(), 1):
        f = json.loads(l).get("text_font") if l.strip() else None
        if isinstance(f, int) and f not in compilees:
            fautes.append(f"ligne {i} : taille {f} non compilee")
        elif isinstance(f, str):
            m = re.fullmatch(r"A:sd/polices/([^/]+\.ttf)-(\d+)", f)
            if not (m and (carte / m.group(1)).is_file()):
                fautes.append(f"ligne {i} : {f} (forme ou TTF absente du dossier de la carte)")
    return fautes


def controle_polices(tmp):
    pages = PAGES.read_text(encoding="utf-8")
    conf = CONF_LV.read_text(encoding="utf-8", errors="replace")
    fautes = fautes_polices(pages, conf, CARTE)
    ttf = sum('"text_font":"A:sd/polices/' in l for l in pages.splitlines())
    print(f"--- polices de pages.jsonl : {ttf} objets en TTF, fautes : {fautes or 'aucune'}")
    ok = not fautes and ttf > 0
    (tmp / "sans_ttf").mkdir()
    for nom, args in [
        ("taille 36 pretendue compilee", (pages.replace('"A:sd/polices/RobotoCondensed-Regular.ttf-36"', "36"), conf, CARTE)),
        ("chemin A:/sd/ (double / dans lv_zip_ufsp)", (pages.replace('"A:sd/polices/', '"A:/sd/polices/'), conf, CARTE)),
        ("TTF absente du dossier de la carte", (pages, conf, tmp / "sans_ttf")),
        ("taille 24 non compilee (tasmota_lv_conf.h relu)", (pages, conf.replace("ROBOTOCONDENSED_REGULAR_24_LATIN1  1",
                                                                                  "ROBOTOCONDENSED_REGULAR_24_LATIN1  0"), CARTE)),
    ]:
        rouge = bool(fautes_polices(*args))
        print(f"  {'OK   ' if rouge else 'ECHEC'} polices : {nom}")
        ok = ok and rouge
    return ok


def ecarts_modele(lues, section):
    """Cles rendues par ecranDebitsFonctions.modele() (ligne MODELE_CLES du .be) contre la section `modele` de ecran.json."""
    return [f"manque dans ecran.json : {c}" for c in sorted(lues - section)] + [f"en trop dans ecran.json : {c}" for c in sorted(section - lues)]


def longueurs_decrites(modele):
    """{liste: longueur} d'une section modele : `voies[].debit` -> `voies[]`, une liste feuille -> sa cle."""
    return {(x["cle"].split("[]")[0] + "[]" if "[]" in x["cle"] else x["cle"]): x["longueur"] for x in modele if "longueur" in x}


def controle_modele(sortie):
    m = re.search(r"^MODELE_CLES: (.+)$", sortie, re.M)
    lues = set(m.group(1).split(",")) if m else set()
    n = re.search(r"^MODELE_LONGUEURS: (.+)$", sortie, re.M)
    rendues = {k: int(v) for k, v in (e.split("=") for e in n.group(1).split(","))} if n else None
    modele = json.loads(ECRAN_JSON.read_text(encoding="utf-8"))["modele"]
    section = [x["cle"] for x in modele]
    ecarts = ecarts_modele(lues, set(section))
    if rendues != longueurs_decrites(modele):
        ecarts.append(f"longueurs : rendues {rendues}, decrites {longueurs_decrites(modele)}")
    print(f"--- section modele de ecran.json : {len(lues)} cles rendues, {len(section)} decrites, ecarts : {ecarts or 'aucun'}")
    ok = bool(lues) and not ecarts and len(section) == len(set(section))
    faux = longueurs_decrites([{**x, "longueur": 5} if "longueur" in x else x for x in modele])
    rouge = rendues != faux
    print(f"  {'OK   ' if rouge else 'ECHEC'} modele : longueur de liste fausse dans la section")
    ok = ok and rouge
    for nom, section_t in [("cle retiree de la section", set(section) - {"voies[].debit"}),
                           ("cle inventee dans la section", set(section) | {"voies[].couleur"}),
                           ("modele non rendu (ligne MODELE_CLES absente)", set(section))]:
        rouge = bool(ecarts_modele(set() if "non rendu" in nom else lues, section_t))
        print(f"  {'OK   ' if rouge else 'ECHEC'} modele : {nom}")
        ok = ok and rouge
    return ok


def temoins(tmp, source, mutants, genre, lance):
    texte = source.read_text(encoding="utf-8").replace("\r\n", "\n")
    ok = True
    for i, (nom, avant, apres) in enumerate(mutants):
        if texte.count(avant) != 1:
            print(f"  ECHEC temoin « {nom} » : texte absent ou ambigu ({genre})")
            ok = False
            continue
        d = tmp / f"{genre}{i}"
        d.mkdir()
        copie = d / "mutant.be"
        copie.write_text(texte.replace(avant, apres), encoding="utf-8")
        rouge = VERT not in lance(d, copie)
        print(f"  {'OK   ' if rouge else 'ECHEC'} {genre} : {nom}")
        ok = ok and rouge
    return ok


def main():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        (tmp / "banc").mkdir()
        sortie = lance_berry(tmp / "banc")
        print("\n".join(l for l in sortie.splitlines() if not l.startswith(("  OK", "MODELE_"))))
        print(f"  ({sum(l.startswith('  OK') for l in sortie.splitlines())} verifications OK)")
        ok = VERT in sortie
        ok = controle_polices(tmp) and ok
        ok = controle_modele(sortie) and ok
        print("--- Temoins (chaque mutant doit etre rouge)")
        ok = temoins(tmp, MODULE, MUTANTS, "module", lambda d, c: lance_berry(d, c)) and ok
        ok = temoins(tmp, DRIVER, MUTANTS_DRIVER, "driver", lambda d, c: lance_berry(d, "-", c)) and ok
        ok = temoins(tmp, INTERFACE, MUTANTS_INTERFACE, "interface", lambda d, c: lance_berry(d, "-", "-", c)) and ok
        ok = temoins(tmp, GENERIQUE, MUTANTS_GENERIQUE, "generique", lambda d, c: lance_berry(d, "-", "-", "-", c)) and ok
    print("BANC_ECRAN_DEBITS (enveloppe):", "VERT" if ok else "ROUGE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
