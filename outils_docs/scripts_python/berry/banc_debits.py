r"""Banc du module debits (carte Serveur Debits de PAC) : banc_debits.be, puis temoins sur des copies du module.

    python outils_docs/scripts_python/berry/banc_debits.py

Code de sortie 0 si tout est vert. Ne teste pas la vraie carte : ni les interruptions des compteurs, ni le pilote
FlowRateMeter, ni la RAM, ni le rendu de la page (essai de charge A6 du plan debitmetres-chauffage).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
BERRY = RACINE / "lib/libesp32/berry/berry.exe"
BANC = "outils_docs/scripts_python/berry/banc_debits.be"
MODULE = RACINE / "data/bureau/tasmota32s3-serveur-debits-pac/debitsFonctions.be"
PAGE = RACINE / "data/bureau/tasmota32s3-serveur-debits-pac/equilibragePage.be"

# Chaque mutant doit rendre le banc rouge : (nom, texte du module, remplacement)
MUTANTS = [
    ("facteur du FlowRateMeter faux", "debitsFonctions.HZ_PAR_RATE = 0.12", "debitsFonctions.HZ_PAR_RATE = 0.1"),
    ("compteur remis a zero compte", " || b < a)", ")"),
    ("duree prise en ms", "* 1000 / ms /", "/ ms /"),
    ("cle francaise oubliee", '["Débit", "Flowrate"]', '["Flowrate"]'),
    ("Rate seul ignore", "rates = [rates]", "rates = nil"),
    ("K de la voie ignore", "/ ks[i + 2]", "/ ks[0]"),
    # (pas de temoin « voie 7 acceptee » : la voie 7 n'a pas d'entree au persist, regleVoie la refuse aussi)
    ("K nul accepte", "if (k == nil || k < 0.1 || k > 1000)", "if (k == nil || k > 1000)"),
    ("persist non sauve", "    persist.save(true)   # true : modif imbriquee", "    # true : modif imbriquee"),
    ("voie sans mesure a 0", 'd[i] == nil ? "null"', 'd[i] == nil ? "0"'),
    ("virgule francaise ignoree", 's = string.replace(str(s), ",", ".")', 's = str(s)'),
    ("texte non numerique accepte", 'if (s[i] < "0" || s[i] > "9")    return nil    end', ''),
    ("nom non echappe", '"<", "&lt;"', '"<", "<"'),
    ("espaces doubles gardes", 'while string.find(texte, "  ") >= 0', 'while false'),
    ("imprecis non signale", "if debitsFonctions.imprecis(d[i])    imprecis.push(i + 1)    end", ""),
    ("ecran non ecrit apres la mesure", "    var e = tasmota.millis()\n    debitsFonctions.ecran()\n", "    var e = tasmota.millis()\n"),
    ("barre en valeur absolue", "int(q * 100 / max + 0.5)", "int(q * 100 / 5 + 0.5)"),
    ("imprecis non colore", 'debitsFonctions.imprecis(q) ? "imprecis" : "normal"', '"normal"'),
    ("voie a l'arret affichee normale", 'if (q <= 0)    return ["0.00 L/min", "arrêt", 0, "arret"]    end', ''),
    ("ecran sans test d'affichage", 'if (!display.started())', 'if (false)'),
    ("seuil muet en 1/10 de min", "* 60000\n", "* 6000\n"),
    ("serie a 0 jamais remise a zero", "            debitsFonctions.zero[i] = nil\n", ""),
    ("erreur muet a chaque mesure", "if (muet && !debitsFonctions.muets[i])", "if (muet)"),
    ("Muets absent du JSON", "if debitsFonctions.muets[i]    muets.push(i + 1)    end", ""),
    ("muet du persist non valide", '|| m < 1)    m = debitsFonctions.MUET_DEFAUT', '|| false)    m = debitsFonctions.MUET_DEFAUT'),
    ("veille sans borne haute", "if (v < 0 || v > 120)", "if (v < 0)"),
    ("veille non appliquee apres reglage", "            persist.save(true)\n            debitsFonctions.appliqueVeille()\n", "            persist.save(true)\n"),
    ("veille 0 laisse l'ecran assombri", "if (v == 0 && haspmota.dimming_state < 100)", "if (false)"),
    ("sortie de veille non publiee", "        tasmota.defer(def () tasmota.publish_rule(", "        tasmota.defer(def () print("),
    # ModBus (A3 du plan debits-deux-cartes)
    ("bit 12 du mot d'etats oublie", "var etats = debitsFonctions.BIT_GROUPE", "var etats = 0"),
    ("debit tronque au lieu d'arrondi", "int(d[i] * 100 + 0.5)", "int(d[i] * 100)"),
    ("voie sans mesure servie a 0", "d[i] == nil ? modbusFonctions.SENTINELLE_UINT32", "d[i] == nil ? 0"),
    ("muet absent du mot d'etats", "if debitsFonctions.muets[i]    etats |= 1 << i    end", ""),
    ("imprecis absent du mot d'etats", "etats |= 1 << (6 + i)", "etats |= 0"),
    ("cle modbus ignoree", 'if (modules["debits"].find("modbus", "OFF") == "ON")    debitsFonctions.publieModbus', "if (true)    debitsFonctions.publieModbus"),
    ("fenetre changee non redeclaree", "if (f != debitsFonctions.fenetreModbus)", "if (debitsFonctions.fenetreModbus == nil)"),
    ("fraicheur d'une seule fenetre", "2 * f * 1000", "f * 1000"),
    ("fraicheur non notee", "        modbusFonctions.noteMesure(int(e[\"type\"]) + int(e[\"id\"]) - 1)\n", ""),
    ("push absent", "    modbusFonctions.pousseEtat(debitsFonctions.REGISTRE_MODBUS, \"uint32\", valeurs)\n", ""),
    ("valeur ecrite dans la mauvaise entree", "e[\"value\"] = valeurs[i]", "e[\"value\"] = valeurs[6 - i]"),
    ("veille non appliquee au demarrage","        debitsFonctions.ecran()\n        debitsFonctions.appliqueVeille()\n", "        debitsFonctions.ecran()\n"),
]

# Temoins de la page /equilibrage (equilibragePage.be), meme regle
MUTANTS_PAGE = [
    ("acces privilegie ignore", "if (!webserver.check_privileged_access())    return nil    end\n    var f =", "var f ="),
    ("POST sans acces privilegie", "if (!webserver.check_privileged_access())    return nil    end\n    var verdict", "var verdict"),
    ("favori sans relais", 'if (webserver.header("Referer") == nil)    return equilibragePage.envoieRelais()    end', ""),
    ("relais en boucle sans Referer", '(webserver.has_arg("r") ? "" : ', '(false ? "" : '),
    ("champ inconnu accepte", 'if (champs.find(cle) == nil)    return [nil, "champ inconnu : " + str(cle)]    end', ""),
    ("caractere refuse accepte", 'return [nil, "caractere refuse pour " + cle]', "continue"),
    ("code du mode carte oublie", "            gestionFileFolder.readFileByLineAndContentSend(equilibragePage.CODE)\n", ""),
    ("</ non echappe dans window.CARTE", 'string.replace(json.dump(carte), "</", "<\\\\/")', "json.dump(carte)"),
    ("page absente non signalee", "if (!path.exists(equilibragePage.PAGE))", "if (false)"),
    ("reponse laissee ouverte apres une exception", "if (ouverte)    webserver.content_close()    end", ""),
    ("age de la mesure en ms", "(tasmota.millis() - r[\"t\"]) / 1000", "(tasmota.millis() - r[\"t\"])"),
    ("mesures illisibles : reponse jamais envoyee", "        texte = json.dump(calcul())", "        texte = nil"),
    ("debit imprecis non signale", "for q: d    imprecis.push(debitsFonctions.imprecis(q))    end", ""),
]


def lance_berry(dossier, module=None, page=None):
    args = [str(BERRY), BANC, str(dossier)] + ([str(module or MODULE), str(page)] if page else [str(module)] if module else [])
    r = subprocess.run(args, cwd=RACINE, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    return r.stdout + r.stderr


def main():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        (tmp / "banc").mkdir()
        sortie = lance_berry(tmp / "banc")
        print("\n".join(l for l in sortie.splitlines() if not l.startswith("  OK")))
        print(f"  ({sum(l.startswith('  OK') for l in sortie.splitlines())} verifications OK)")
        ok = "BANC_DEBITS: OK" in sortie
        texte = MODULE.read_text(encoding="utf-8")
        print("--- Temoins (chaque mutant doit etre rouge)")
        for i, (nom, avant, apres) in enumerate(MUTANTS):
            if texte.count(avant) != 1:
                print(f"  ECHEC temoin « {nom} » : texte absent ou ambigu dans le module")
                ok = False
                continue
            d = tmp / f"mutant{i}"
            d.mkdir()
            copie = d / "mutant.be"
            copie.write_text(texte.replace(avant, apres), encoding="utf-8")
            rouge = "BANC_DEBITS: OK" not in lance_berry(d, copie)
            print(f"  {'OK   ' if rouge else 'ECHEC'} {nom}")
            ok = ok and rouge
        page = PAGE.read_text(encoding="utf-8")
        for i, (nom, avant, apres) in enumerate(MUTANTS_PAGE):
            if page.count(avant) != 1:
                print(f"  ECHEC temoin « {nom} » : texte absent ou ambigu dans la page")
                ok = False
                continue
            d = tmp / f"page{i}"
            d.mkdir()
            copie = d / "mutant.be"
            copie.write_text(page.replace(avant, apres), encoding="utf-8")
            rouge = "BANC_DEBITS: OK" not in lance_berry(d, page=copie)
            print(f"  {'OK   ' if rouge else 'ECHEC'} page : {nom}")
            ok = ok and rouge
    print("BANC_DEBITS (enveloppe):", "VERT" if ok else "ROUGE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
