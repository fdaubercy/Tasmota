r"""Banc de la carte d'AFFICHAGE des debits (carte tasmota32s3-bureau-ecran-debits-pac) : banc_ecran_debits.be, puis temoins
sur des copies du module et du driver.

    python outils_docs/scripts_python/berry/banc_ecran_debits.py

Code de sortie 0 si tout est vert. Ne teste pas la vraie carte : ni le releve ModBus, ni le push, ni HASPmota/LVGL reels,
ni le rendu sur l'ecran (essais sur cartes du plan debits-deux-cartes, A6). Les entrees analogiques sont posees a la main
comme les range modBus_TasmotaSlaveModBus (banc_test_modbus.py couvre le releve groupe et la repartition du push).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
BERRY = RACINE / "lib/libesp32/berry/berry.exe"
BANC = "outils_docs/scripts_python/berry/banc_ecran_debits.be"
MODULE = RACINE / "data/bureau/tasmota32s3-ecran-debits-pac/ecranDebitsFonctions.be"
DRIVER = RACINE / "data/bureau/tasmota32s3-ecran-debits-pac/controleEcranDebits.be"
VERT = "BANC_ECRAN_DEBITS: OK"

# Chaque mutant doit rendre le banc rouge : (nom, texte du module, remplacement)
MUTANTS = [
    ("centiemes pris pour des L/min", "v == nil ? nil : v / 100.0", "v == nil ? nil : v / 1.0"),
    ("etatConstate ignore", 'e.find("etatConstate") != "valide"', "false"),
    ("fraicheur d'une seule fenetre", "now - t > 2 * ecranDebitsFonctions.fenetre()", "now - t > ecranDebitsFonctions.fenetre()"),
    ("fraicheur jamais controlee", "now - t > 2 * ecranDebitsFonctions.fenetre()", "false"),
    ("fraicheur trop lache (3 fenetres)", "now - t > 2 * ecranDebitsFonctions.fenetre()", "now - t > 3 * ecranDebitsFonctions.fenetre()"),
    ("sentinelle affichee comme un debit", "v != modbusFonctions.SENTINELLE_UINT32", "true"),
    ("fenetre illisible acceptee", '(type(v) == "int" && v >= 2 && v <= 60) ? v : ecranDebitsFonctions.FENETRE_DEFAUT', "v"),
    ("bit muet decale", "muets.push(w != nil && (w & (1 << i)) != 0)", "muets.push(w != nil && (w & (1 << (i + 1))) != 0)"),
    ("bit imprecis decale", "imprecis.push(w != nil && (w & (1 << (6 + i))) != 0)", "imprecis.push(w != nil && (w & (1 << (7 + i))) != 0)"),
    ("mot d'etats perime cru", 'return {"frais": w != nil,', 'return {"frais": true,'),
    ("voie muette non signalee", 'if (muet)    return ["0.00 L/min", "muet", 0, "muet"]    end', ""),
    ("voie inconnue affichee 0", 'if (q == nil)    return ["inconnu", "", 0, "inconnu"]    end', "if (q == nil)    q = 0.0    end"),
    ("voie a l'arret affichee normale", 'if (q <= 0)    return ["0.00 L/min", "arrêt", 0, "arret"]    end', ""),
    ("imprecis non colore", 'imprecis ? "imprecis" : "normal"', '"normal"'),
    ("total partiel non marque", '(tt[1] < ecranDebitsFonctions.NB_VOIES ? " (partiel)" : "")', '""'),
    ("total sans voie connue", 'var total = "Total inconnu"', 'var total = "Total 0.00 L/min"'),
    ("barre en valeur absolue", "int(q * 100 / max + 0.5)", "int(q * 100 / 5 + 0.5)"),
    ("ecran reecrit sans test de changement", "if (cle == ecranDebitsFonctions.dernier)    return    end", ""),
    ("objets neufs non reecrits", "        ecranDebitsFonctions.dernier = nil    # objets neufs : tout reecrire\n", ""),
    ("nom du persist ignore", 'str(ent.find("nom", "Départ " + str(i + 1)))', '"Départ " + str(i + 1)'),
    ("message fenetre a chaque seconde", "if (toutes && !ecranDebitsFonctions.toutesInconnues)", "if (toutes)"),
    ("message fenetre des le demarrage", "ecranDebitsFonctions.toutesInconnues = true   #", "ecranDebitsFonctions.toutesInconnues = false   #"),
    ("message fenetre en erreur", '(ReglageEcranDebits fenetre) ?", LOG_LEVEL_DEBUG)', '(ReglageEcranDebits fenetre) ?", LOG_LEVEL_ERREUR)'),
    ("message fenetre jamais re-arme", "    ecranDebitsFonctions.toutesInconnues = toutes\n",
     "    ecranDebitsFonctions.toutesInconnues = ecranDebitsFonctions.toutesInconnues || toutes\n"),
    ("message fenetre seulement avec un ecran", "    ecranDebitsFonctions.suitFenetre(d)\n    if (global.p1b13 == nil)    return    end\n",
     "    if (global.p1b13 == nil)    return    end\n    ecranDebitsFonctions.suitFenetre(d)\n"),
    ("fenetre 1 acceptee", "if (n == nil || n < 2 || n > 60)", "if (n == nil || n > 60)"),
    ("fenetre non sauvee", '            modules["ecranDebits"]["fenetre"] = n\n            persist.save(true)', '            modules["ecranDebits"]["fenetre"] = n'),
    ("veille sans borne haute", "if (n == nil || n > 120)", "if (n == nil)"),
    ("veille non appliquee apres reglage", "            persist.save(true)\n            ecranDebitsFonctions.appliqueVeille()\n", "            persist.save(true)\n"),
    ("veille 0 laisse l'ecran assombri", "if (v == 0 && haspmota.dimming_state < 100)", "if (false)"),
    ("sortie de veille non publiee", "        tasmota.defer(def () tasmota.publish_rule(", "        tasmota.defer(def () print("),
    ("veille non appliquee au demarrage", "        ecranDebitsFonctions.ecran()\n        ecranDebitsFonctions.appliqueVeille()\n", "        ecranDebitsFonctions.ecran()\n"),
    ("ecran absent : pas de test d'affichage", "if (!display.started())", "if (false)"),
]
# Temoins du driver controleEcranDebits.be
MUTANTS_DRIVER = [
    ("commande non declaree", 'tasmota.add_cmd("ReglageEcranDebits", ecranDebitsFonctions.reglageEcranDebits)', ""),
    ("ecran non demarre", "        ecranDebitsFonctions.demarreEcran()\n", ""),
    ("ecran non rafraichi chaque seconde", "            ecranDebitsFonctions.ecran()\n        except", "            0\n        except"),
    ("log info dans every_second", "            ecranDebitsFonctions.ecran()\n        except",
     "            ecranDebitsFonctions.ecran()\n            ecranDebitsFonctions.log('ECRAN_DEBITS: tic !', LOG_LEVEL_INFO)\n        except"),
]


def lance_berry(dossier, module="-", driver=None):
    args = [str(BERRY), BANC, str(dossier), str(module)] + ([str(driver)] if driver else [])
    r = subprocess.run(args, cwd=RACINE, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    return r.stdout + r.stderr


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
        print("\n".join(l for l in sortie.splitlines() if not l.startswith("  OK")))
        print(f"  ({sum(l.startswith('  OK') for l in sortie.splitlines())} verifications OK)")
        ok = VERT in sortie
        print("--- Temoins (chaque mutant doit etre rouge)")
        ok = temoins(tmp, MODULE, MUTANTS, "module", lambda d, c: lance_berry(d, c)) and ok
        ok = temoins(tmp, DRIVER, MUTANTS_DRIVER, "driver", lambda d, c: lance_berry(d, "-", c)) and ok
    print("BANC_ECRAN_DEBITS (enveloppe):", "VERT" if ok else "ROUGE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
