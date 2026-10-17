"""Banc de l'annuaire des outils PC (annuaire_registre.py ; presence et serveur ajoutes ensuite).

Code de sortie 0 = vert. Une section par fonction, appelee par principal().
"""

import json
import os
import re
import socket
import subprocess
import sys
import tempfile

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


def serveur_libre():
    """Socket en ecoute sur un port libre : (socket, port)."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen(128)
    return s, s.getsockname()[1]


def port_libre():
    s, p = serveur_libre()
    s.close()
    return p


def pid_mort():
    """PID d'un processus que ce test vient de lancer et de laisser se terminer."""
    pr = subprocess.Popen([sys.executable, "-c", "pass"])
    pr.wait()
    return pr.pid


def ecrit_fiche(dossier, nom, port, pid, lance_par="annuaire", jeton="jt", local=False):
    with open(os.path.join(dossier, f"{port}.json"), "w", encoding="utf-8") as f:
        json.dump({"nom": nom, "port": port, "pid": pid, "debut": "2026-10-17T10:00:00", "jeton": jeton,
                   "local": local, "lance_par": lance_par}, f)


def section_presence():
    print("== presence ==")
    racine = tempfile.mkdtemp()
    os.environ["OUTILS_TASMOTA_DOSSIER"] = racine
    import acces_web
    import annuaire_presence as pre
    dossier = str(acces_web.dossier_presence())
    libres = {o.id: port_libre() for o in reg.OUTILS}
    for f in os.listdir(dossier):
        os.remove(os.path.join(dossier, f))

    def etat(id, **kw):
        # Ports de page libres par defaut : le banc ne depend pas des outils reels qui tournent.
        derniers = {o.id: {o.cle_port_page: libres[o.id]} for o in reg.OUTILS}
        for k, v in kw.get("derniers", {}).items():
            derniers[k] = {**derniers.get(k, {}), **v}
        l = pre.etat_outils(kw.get("lances", {}), derniers, kw.get("hote"))
        return next(e for e in l if e["id"] == id)

    verifie(pre.pid_vivant(os.getpid()), True, "pid_vivant : ce processus")
    verifie(pre.pid_vivant(pid_mort()), False, "TEMOIN pid_vivant : processus termine")

    srv, port = serveur_libre()
    verifie(pre.port_repond(port), True, "port_repond : serveur ouvert")
    verifie(pre.port_repond(port_libre()), False, "TEMOIN port_repond : port ferme")

    ecrit_fiche(dossier, "Serveur syslog", port, os.getpid())
    e = etat("syslog")
    verifie((e["etat"], e["port"], e["lien"]), ("marche", port, f"http://127.0.0.1:{port}/"), "fiche_vivante")
    verifie(e["debut"], "2026-10-17T10:00:00", "fiche_vivante : debut")
    verifie(etat("syslog", hote="192.168.0.3")["lien"], f"http://192.168.0.3:{port}/?jeton=jt", "fiche_vivante : lien distant")
    verifie((e["peut_arreter"], e["lance_ailleurs"], e["console"]), (True, False, False), "peut_arreter annuaire")
    verifie(etat("syslog", lances={"syslog": {"pid": os.getpid(), "valeurs": {}}})["console"], True, "console capturee")
    ecrit_fiche(dossier, "Serveur syslog", port, os.getpid(), lance_par="")
    e = etat("syslog")
    verifie((e["peut_arreter"], e["lance_ailleurs"]), (False, True), "peut_arreter : lance ailleurs")
    ecrit_fiche(dossier, "Serveur syslog", port, os.getpid(), jeton=None, local=True)
    verifie(etat("syslog", hote="192.168.0.3")["lien"], None, "fiche sans jeton : lien distant None")
    verifie(etat("pont_serie")["etat"], "arrete", "TEMOIN autre outil : arrete")
    ecrit_fiche(dossier, "Terminal supplementaire", port_libre(), os.getpid())
    verifie(len(pre.etat_outils({}, {}, None)), len(reg.OUTILS), "fiche hors registre ignoree")

    for f in os.listdir(dossier):
        os.remove(os.path.join(dossier, f))
    mort = port_libre()
    ecrit_fiche(dossier, "Pont serie", mort, pid_mort())
    verifie(etat("pont_serie")["etat"], "arrete", "fiche_perimee : arrete")
    verifie(os.listdir(dossier), [], "fiche_perimee : fichier supprime")
    with open(os.path.join(dossier, "1.json"), "w") as f:
        f.write("{pas du json")
    verifie(pre.lit_fiches(), {}, "fichier illisible ignore")
    os.remove(os.path.join(dossier, "1.json"))

    verifie(etat("syslog", derniers={"syslog": {"http": port}})["port"], port, "arrete : port attendu depuis derniers")
    e = etat("syslog", derniers={"syslog": {"http": port}})
    verifie((e["etat"], e["raison"], e["lien"]), ("marche", "en marche (sans fiche)", f"http://127.0.0.1:{port}/"),
            "port_sans_fiche")
    verifie(etat("syslog", derniers={"syslog": {"http": port}}, hote="192.168.0.3")["lien"], None,
            "port_sans_fiche : lien distant None")
    e = pre.etat_outils({}, {"syslog": {"http": "abc"}}, None)[4]
    verifie((e["id"], e["port"]), ("syslog", reg.par_id("syslog").port_page({})), "valeur invalide : defaut")
    srv.close()
    verifie(etat("syslog", derniers={"syslog": {"http": port}})["etat"], "arrete", "TEMOIN port ferme : arrete")

    ecrit_fiche(dossier, "Pont serie", mort, os.getpid())
    verifie(etat("pont_serie")["etat"], "arrete", "fiche PID vivant port ferme : pas marche")
    verifie(os.path.exists(os.path.join(dossier, f"{mort}.json")), True, "fiche PID vivant port ferme : conservee")
    srv2 = socket.socket()
    srv2.bind(("127.0.0.1", mort))
    srv2.listen(5)
    verifie(etat("pont_serie")["etat"], "marche", "TEMOIN meme fiche, port ouvert : marche")
    srv2.close()
    lances = {"pont_serie": {"pid": os.getpid(), "valeurs": {"port": "COM3"}}}
    e = etat("sniffeur_modbus", lances=lances, derniers={"sniffeur_modbus": {"port": "COM3"}})
    verifie((e["etat"], "COM3" in e["raison"], "Pont série" in e["raison"]), ("bloque", True, True), "com_tenu")
    e = etat("sniffeur_modbus", lances=lances, derniers={"sniffeur_modbus": {"port": "COM4"}})
    verifie(e["etat"], "arrete", "TEMOIN com_tenu : autre port libre")
    lances = {"pont_serie": {"pid": pid_mort(), "valeurs": {"port": "COM3"}}}
    e = etat("sniffeur_modbus", lances=lances, derniers={"sniffeur_modbus": {"port": "COM3"}})
    verifie(e["etat"], "arrete", "TEMOIN com_tenu : lance mort ne bloque pas")


def principal():
    section_registre()
    print()
    section_presence()
    print()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(principal())
