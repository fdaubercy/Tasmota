r"""Banc de la page « Systeme » des ecrans tactiles (data/fs/ecranSysteme.be, controleEcranSysteme.be, dernieres erreurs de
logFonctions.be ; plan tasks/plans/atelier-ecrans.md A19) : banc_ecran_systeme.be, relecture de la table CHAMPS par l'expression
reguliere que la page de l'atelier utilisera, puis temoins (copies modifiees du module, du driver et de logFonctions).

    python outils_docs/scripts_python/berry/banc_ecran_systeme.py

Code de sortie 0 si tout est vert. Ne teste pas une vraie carte : ni tasmota.memory, ni les reponses reelles de Status 1/2/11,
UfsSize, UfsFree, RgxClients (formes lues dans le C++ et posees a la main), ni HASPmota ou LVGL reels (interfaces simulees).
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
BERRY = RACINE / "lib/libesp32/berry/berry.exe"
BANC = "outils_docs/scripts_python/berry/banc_ecran_systeme.be"
MODULE = RACINE / "data/fs/ecranSysteme.be"
DRIVER = RACINE / "data/fs/controleEcranSysteme.be"
LOGS = RACINE / "data/fs/logFonctions.be"
VERT = "BANC_ECRAN_SYSTEME: OK"
# Une entree de CHAMPS par ligne : ["cle", "libelle", "unite", id du texte, id de la barre ou nil]
ENTREE = re.compile(r'^\s*\["(\w+)", "([^"]*)", "([^"]*)", (\d+), (\d+|nil)\],?\]?\s*$')

MUTANTS = [
    ("accent coupe en deux", "while (n > 0 && (string.byte(msg[n]) & 0xC0) == 0x80)    n -= 1    end", ""),
    ("persist absent non garde", "    if (modules == nil)    return nil    end      # persist absent : pas de page\n", ""),
    ("page ignoree", "if (p == nil || ecranSysteme.pageAffichee() != p)", "if (p == nil)"),
    ("cadence de 5 s ignoree", "    if (a != nil && t >= a && t - a < ecranSysteme.MAJ)    return    end\n", ""),
    ("lectures par commande a chaque mesure", "if (a == nil || t < a || t - a >= ecranSysteme.LENT)", "if (true)"),
    ("confirmation sautee", "if (a != nil && t >= a && t - a < ecranSysteme.CONFIRMATION)", "if (true)"),
    ("confirmation jamais close", "if (a != nil && (t < a || t - a >= ecranSysteme.CONFIRMATION))", "if (false)"),
    ("texte du bouton non rendu", "        ecranSysteme.ecris(ecranSysteme.BOUTON_REDEMARRER, \"text\", ecranSysteme.TEXTE_REDEMARRER)\n", ""),
    ("minimum non suivi", 'if (m == nil || v < m)    e["ramMin"] = v    end', 'e["ramMin"] = v'),
    ("seuil inverse", "if (s[0] < s[1])", "if (s[0] > s[1])"),
    ("orange et rouge confondus", 'x >= s[1] ? "rouge" : (x >= s[0] ? "orange" : "vert")', 'x >= s[0] ? "rouge" : "vert"'),
    ("courbe a chaque seconde", "t - a < ecranSysteme.COURBE_PAS", "t - a < 1000"),
    ("courbe sans limite", "    c.remove(0)\n", ""),
    ("map de tasmota.memory page cachee", 'var v = tasmota.memory("heap_free")', 'var v = tasmota.memory()["heap_free"]'),
    ("couleur HASPmota en entier", '? c : string.format("#%06X", c)', "? c : c"),
    ("couleur LVGL en texte", '? c : string.format("#%06X", c)', '? string.format("#%06X", c) : string.format("#%06X", c)'),
    ("verdict OTA inverse", "var possible = libre >= prog", "var possible = libre <= prog"),
    ("barre du signal en dBm", 'tasmota.wifi("quality"), w)', "w, w)"),
    ("carte SD prise pour la flash", "v = size(v) > 0 ? v[-1] : nil", "v = size(v) > 0 ? v[0] : nil"),
    ("pertes du Wi-Fi = LinkCount", 'p(r, "pertesWifi", str(v > 0 ? v - 1 : 0)', 'p(r, "pertesWifi", str(v'),
    ("GC non lance", "    tasmota.gc()\n", ""),
    ("GC sans relecture", '    tasmota.gc()\n    ecranSysteme.etat()["majA"] = nil\n', "    tasmota.gc()\n"),
    ("erreur1 = la plus vieille", "var e = l[size(l) - i]", "var e = l[i - 1]"),
    ("absent ecrit vide", 'x == nil ? "--" : x[0]', 'x == nil ? "" : x[0]'),
    ("Mo des 1000 Mo seulement", "return n >= 1024 ?", "return n >= 1048576 ?"),
    ("bouton sur l'appui (down)", '    if (valeur != "up")    return    end\n', ""),
    ("RgxClients sans range extender", 'if (isinstance(rgx, map) && rgx.find("activation", "OFF") == "ON")', "if (true)"),
    ("muets ignores", 'muets > 0 ? "rouge" : "vert")', '"vert")'),
    ("page de HASPmota prise pour LVGL", "if (ecranSysteme.estLvgl(itf))    return itf.page    end", ""),
    ("Status 1/2 relus a chaque mesure", 'if (e["fixe"] == nil)    ecranSysteme.litFixe()    end', "ecranSysteme.litFixe()"),
]
MUTANTS_DRIVER = [
    ("garde d'activation ignoree", 'if (modules.find("ecranSysteme", {}).find("activation", "OFF") == "ON")', "if (true)"),
    ("regles des boutons non posees", "        ecranSysteme.regles()      # boutons", "        #"),
    ("erreur repetee chaque seconde", "if (self.echec != msg)", "if (true)"),
    ("tic non appele", "            ecranSysteme.tic()\n", ""),
]
MUTANTS_LOGS = [
    ("erreurs non gardees", "        logFonctions.noteErreur(msg)\n", ""),
    ("6 erreurs gardees", "logFonctions.ERREURS_GARDEES = 5", "logFonctions.ERREURS_GARDEES = 6"),
    ("plus recente retiree", "    if (size(l) >= logFonctions.ERREURS_GARDEES)    l.remove(0)    end",
     "    if (size(l) >= logFonctions.ERREURS_GARDEES)    l.remove(-1)    end"),
    ("info gardee aussi", "    else\n        logFonctions.noteErreur(msg)\n    end\n    log(msg, niveau)",
     "    end\n    logFonctions.noteErreur(msg)\n    log(msg, niveau)"),
    ("heure non gardee", 'l.push([type(h) == "int" ? h : nil, msg])', "l.push([nil, msg])"),
    ("cible ecranSysteme absente", '"ecranCave", "ecranDebits", "ecranSysteme"]', '"ecranCave", "ecranDebits"]'),
    ("bloc de la cible absent", '    elif c == "ecransysteme"        bloc = (modules != nil ? modules.find("ecranSysteme") : nil)\n', ""),
]


def lance_berry(dossier, module="-", driver="-", logs="-"):
    args = [str(BERRY), BANC, str(dossier), str(module), str(driver), str(logs)]
    try:
        r = subprocess.run(args, cwd=RACINE, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                           stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return "BLOQUE : berry.exe arrete apres 120 s"    # jamais le mot du vert : un mutant qui boucle compte rouge
    return r.stdout + r.stderr


def champs(texte):
    """Entrees de ecranSysteme.CHAMPS relues comme le fera la page de l'atelier : [(cle, libelle, unite, texte, barre)]."""
    m = re.search(r"^ecranSysteme\.CHAMPS = \[\n(.*?)\]\]\s*$", texte, re.M | re.S)
    if not m:
        return []
    lignes = (m.group(1) + "]]").splitlines()
    lues = [ENTREE.match(l) for l in lignes]
    if not all(lues):
        return []
    return [(x[1], x[2], x[3], int(x[4]), None if x[5] == "nil" else int(x[5])) for x in lues]


def fautes_champs(entrees, boutons):
    fautes = []
    ids = [i for e in entrees for i in (e[3], e[4]) if i is not None]
    if len(entrees) < 30:
        fautes.append(f"{len(entrees)} entrees lues")
    if len(ids) != len(set(ids)):
        fautes.append("id en double")
    if any(not 1 <= i <= 199 for i in ids):
        fautes.append("id hors de 1..199")
    if set(ids) & set(boutons):
        fautes.append("id d'un champ = id d'un bouton")
    if len({e[0] for e in entrees}) != len(entrees):
        fautes.append("cle en double")
    return fautes


def controle_champs():
    texte = MODULE.read_text(encoding="utf-8")
    boutons = [int(x) for x in re.findall(r"^ecranSysteme\.BOUTON_\w+ = (\d+)$", texte, re.M)]
    entrees = champs(texte)
    fautes = fautes_champs(entrees, boutons)
    print(f"--- CHAMPS relue par expression reguliere : {len(entrees)} entrees, boutons {boutons}, fautes : {fautes or 'aucune'}")
    ok = not fautes and len(boutons) == 2
    for nom, t in [("entree sur deux lignes", texte.replace('    ["ramMin", "RAM libre minimale", "Ko", 2, nil],',
                                                               '    ["ramMin", "RAM libre minimale",\n     "Ko", 2, nil],')),
                   ("id en double", texte.replace('"Ko", 2, nil]', '"Ko", 1, nil]')),
                   ("id d'un bouton", texte.replace('"Ko", 2, nil]', '"Ko", 120, nil]')),
                   ("id de la barre de navigation", texte.replace('"Ko", 2, nil]', '"Ko", 201, nil]'))]:
        rouge = bool(fautes_champs(champs(t), boutons))
        print(f"  {'OK   ' if rouge else 'ECHEC'} CHAMPS : {nom}")
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
        (d / "banc").mkdir()
        rouge = VERT not in lance(d / "banc", copie)
        print(f"  {'OK   ' if rouge else 'ECHEC'} {genre} : {nom}")
        ok = ok and rouge
    return ok


def main():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        (tmp / "banc").mkdir()
        sortie = lance_berry(tmp / "banc")
        print("\n".join(l for l in sortie.splitlines() if not l.startswith("  OK")))
        print(f"  ({sum(l.startswith('  OK') for l in sortie.splitlines())} verifications OK)")
        ok = VERT in sortie
        ok = controle_champs() and ok
        print("--- Temoins (chaque mutant doit etre rouge)")
        ok = temoins(tmp, MODULE, MUTANTS, "module", lambda d, c: lance_berry(d, c)) and ok
        ok = temoins(tmp, DRIVER, MUTANTS_DRIVER, "driver", lambda d, c: lance_berry(d, "-", c)) and ok
        ok = temoins(tmp, LOGS, MUTANTS_LOGS, "logs", lambda d, c: lance_berry(d, "-", "-", c)) and ok
    print("BANC_ECRAN_SYSTEME (enveloppe):", "VERT" if ok else "ROUGE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
