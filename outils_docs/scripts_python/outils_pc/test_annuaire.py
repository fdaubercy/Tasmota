"""Banc de l'annuaire des outils PC (annuaire_registre.py ; presence et serveur ajoutes ensuite).

Code de sortie 0 = vert. Une section par fonction, appelee par principal().
"""

import os
import re
import sys

import annuaire_registre as reg

ECHECS = []
RACINE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def refuse(outil, valeurs, ports=(), ponts=()):
    try:
        reg.valide(outil, valeurs, list(ports), list(ponts))
    except ValueError:
        return True
    return False


def lit(outil):
    with open(os.path.join(RACINE, outil.script), encoding="utf-8") as f:
        return f.read()


def section_registre():
    print("== registre ==")
    ids = ["pont_serie", "sniffeur_modbus", "testeur_udp", "sniffeur_mqtt", "syslog", "synchro_fork"]
    verifie([o.id for o in reg.OUTILS], ids, "six_outils : ids et ordre")
    verifie(all(o.groupe in reg.GROUPES for o in reg.OUTILS), True, "six_outils : groupes connus")
    verifie([o.id for o in reg.OUTILS if not os.path.isfile(os.path.join(RACINE, o.script))], [],
            "six_outils : scripts existants")
    verifie(all(o.interet and o.aide and o.journaux and o.nom for o in reg.OUTILS), True, "textes renseignes")

    for o in reg.OUTILS:
        src = lit(o)
        lignes = [l for l in src.splitlines() if "acces_web.Acces(" in l and f'"{o.nom_acces}"' in l]
        verifie(bool(lignes), True, f"nom_acces_reel : {o.id}")
        manquantes = [p.option for p in o.parametres
                      if not re.search(r'add_argument\(\s*"' + re.escape(p.option) + r'"', src)]
        verifie(manquantes, [], f"options_reelles : {o.id}")
        verifie(o.port_page({}) in range(1024, 65536), True, f"port de page par defaut : {o.id}")

    mb = reg.par_id("sniffeur_modbus")
    verifie(reg.valide(mb, {}, [], []), ["--port", "auto", "--debit", "19200", "--http", "7300"], "valide_defauts")
    verifie(reg.valide(mb, {"debit": 9600, "http": "7301"}, [], []),
            ["--port", "auto", "--debit", "9600", "--http", "7301"], "valeurs int et str acceptees")
    verifie(reg.valide(mb, {"port": "COM3"}, ["COM3"], [])[:2], ["--port", "COM3"], "port detecte accepte")

    tu = reg.par_id("testeur_udp")
    args = reg.valide(tu, {"port_maitre": "pont:7000"}, [], [7000])
    verifie(("--port-maitre" in args and args[args.index("--port-maitre") + 1] == "pont:7000"), True, "valide_pont")
    verifie("--port-esclave" in args, False, "port_esclave vide : option absente")
    verifie(refuse(tu, {"port_maitre": "pont:7000"}, ponts=[]), True, "pont inconnu refuse")
    verifie(reg.valide(tu, {"port_esclave": "COM4"}, ["COM4"], [])[:2], ["--port-esclave", "COM4"], "com_ou_pont : port detecte")
    verifie(tu.a_port_com, True, "testeur a_port_com")
    verifie(reg.par_id("syslog").a_port_com, False, "syslog sans port com")
    verifie(reg.par_id("syslog").port_page({"http": 7250}), 7250, "port_page depuis valeurs")

    for valeurs in ({"port": "COM3 --x"}, {"port": "../x"}, {"debit": "12"}, {"inconnue": "1"}, {"http": "80"},
                    {"debit": "abc"}, {"http": "70000"}):
        verifie(refuse(mb, valeurs, ports=["COM3"]), True, f"valeurs_piegees_refusees {valeurs}")
    # Temoin : une valeur saine, elle, ne leve rien.
    verifie(refuse(mb, {"port": "COM3", "debit": "19200", "http": "7300"}, ports=["COM3"]), False,
            "TEMOIN valeurs saines acceptees")

    sf = reg.par_id("synchro_fork")
    verifie((sf.dans_job, sf.route_occupe), (False, "/execution"), "synchro_hors_job")
    verifie(reg.par_id("pont_serie").dans_job, True, "pont dans_job")
    try:
        reg.par_id("zzz")
        trouve = True
    except KeyError:
        trouve = False
    verifie(trouve, False, "par_id inconnu -> KeyError")

    j = reg.en_json()
    verifie(sorted(j), ["debits", "groupes", "outils"], "en_json : cles")
    verifie("script" in j["outils"][0], False, "en_json : sans script")
    verifie((j["outils"][2]["a_port_com"], j["outils"][2]["port_defaut"]), (True, 7400), "en_json : derives")
    verifie(isinstance(j["outils"][0]["parametres"][0], dict), True, "en_json : parametres en dicts")


def principal():
    section_registre()
    print()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(principal())
