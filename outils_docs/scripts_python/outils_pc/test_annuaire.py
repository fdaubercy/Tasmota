"""Banc de l'annuaire des outils PC (registre, presence, serveur).

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
    ids = ["pont_serie", "sniffeur_modbus", "testeur_udp", "sniffeur_mqtt", "syslog", "synchro_fork", "build",
           "fichiers_berry", "assistant_persist"]
    verifie([o.id for o in reg.OUTILS], ids, "sept_outils : ids et ordre")
    verifie(all(o.groupe in reg.GROUPES for o in reg.OUTILS), True, "sept_outils : groupes connus")
    verifie([o.id for o in reg.OUTILS if not os.path.isfile(os.path.join(RACINE, o.script))], [],
            "sept_outils : scripts existants")
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

    ps = reg.par_id("pont_serie")
    verifie(reg.valide(ps, {}, [], []), ["--port", "auto", "--vitesse", "115200", "--tcp", "7000"],
            "drapeau relance_log off par defaut : option absente")
    verifie(reg.valide(ps, {"relance_log": "on"}, [], [])[-1], "--relance-log", "drapeau on : option seule, sans valeur")
    verifie(reg.valide(ps, {"relance_log": True}, [], [])[-1], "--relance-log", "drapeau : booleen JSON true accepte")
    verifie("--relance-log" in reg.valide(ps, {"relance_log": "off"}, [], []), False, "drapeau off : option absente")
    for v in ("oui --x", "1", "", "--relance-log"):
        verifie(refuse(ps, {"relance_log": v}), True, f"drapeau : valeur piegee refusee {v!r}")

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

    section_texte_arret()

    j = reg.en_json()
    verifie(sorted(j), ["debits", "groupes", "outils"], "en_json : cles")
    verifie("script" in j["outils"][0], False, "en_json : sans script")
    verifie((j["outils"][2]["a_port_com"], j["outils"][2]["port_defaut"]), (True, 7400), "en_json : derives")
    verifie(isinstance(j["outils"][0]["parametres"][0], dict), True, "en_json : parametres en dicts")


def textes_arret(ids):
    """{id: texte} de la fonction texteArret de la page, executee par node sur les fiches de en_json().

    None si node est absent (le banc le dit et retombe sur un controle statique)."""
    import annuaire_page
    import shutil
    if not shutil.which("node"):
        return None
    m = re.search(r"function texteArret\(o\) \{.*?\n\}\n", annuaire_page.PAGE, re.S)
    if not m:
        return {}
    fiches = [o for o in reg.en_json()["outils"] if o["id"] in ids]
    script = m.group(0) + "\nconst f = " + json.dumps(fiches) + ";\n" \
        "process.stdout.write(JSON.stringify(Object.fromEntries(f.map(o => [o.id, texteArret(o)]))));\n"
    r = subprocess.run(["node", "-e", script], capture_output=True, timeout=30)
    return json.loads(r.stdout.decode("utf-8")) if r.returncode == 0 else {"erreur": r.stderr.decode("utf-8", "replace")}


def section_texte_arret():
    """Texte « Arrêter » de l'aide : celui de l'outil build parle d'un lancement de build, pas d'un depot."""
    textes = textes_arret(["build", "synchro_fork", "pont_serie"])
    if textes is None:
        print("NOTE node absent : texteArret non execute, controle statique du registre seulement")
        textes = {o["id"]: o.get("arret_refuse", "") for o in reg.en_json()["outils"]}
    build, synchro, pont = textes.get("build", ""), textes.get("synchro_fork", ""), textes.get("pont_serie", "")
    verifie(("un lancement de build est en cours" in build, "jusqu'à sa fin" in build, "moitié modifié" in build),
            (True, True, False), f"texte_arret : build -> lancement de build en cours, arret refuse jusqu'a sa fin ({build[-160:]})")
    verifie("dépôt à moitié modifié" in synchro, True, "texte_arret : temoin, la synchro garde « depot a moitie modifie »")
    verifie(("refusé" in pont, bool(pont)), (False, True), "texte_arret : temoin, outil sans route_occupe -> pas de refus")


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


def maintenant():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def ecrit_fiche(dossier, nom, port, pid, lance_par="annuaire", jeton="jt", local=False, debut=None):
    """debut par defaut = maintenant : le processus (le banc) existe deja, la fiche est donc vivante."""
    with open(os.path.join(dossier, f"{port}.json"), "w", encoding="utf-8") as f:
        json.dump({"nom": nom, "port": port, "pid": pid, "debut": debut or maintenant(), "jeton": jeton,
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
    verifie(e["debut"][:10], maintenant()[:10], "fiche_vivante : debut")
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

    # PID reutilise : fiche ecrite il y a 1 h, alors que ce processus a ete cree apres -> pas la meme vie.
    ecrit_fiche(dossier, "Pont serie", mort, os.getpid(), debut="2020-01-01T00:00:00")
    verifie(etat("pont_serie")["etat"], "arrete", "fiche PID reutilise (processus plus recent) : pas marche")
    verifie(os.path.exists(os.path.join(dossier, f"{mort}.json")), True, "fiche PID reutilise : conservee")
    # Temoin : meme PID, debut = maintenant, AUCUN serveur sur le port -> marche (pas de sondage du port).
    ecrit_fiche(dossier, "Pont serie", mort, os.getpid())
    verifie(etat("pont_serie")["etat"], "marche", "TEMOIN meme fiche, debut = maintenant, port ferme : marche")
    # Pas de connexion au port d'un outil dont la fiche est vivante (le pont afficherait client connecte).
    ecoute, p_pont = serveur_libre()
    ecoute.settimeout(0.5)
    ecrit_fiche(dossier, "Pont serie", p_pont, os.getpid())
    os.remove(os.path.join(dossier, f"{mort}.json"))
    verifie(etat("pont_serie")["etat"], "marche", "fiche vivante : marche")
    try:
        ecoute.accept()
        connexions = 1
    except socket.timeout:
        connexions = 0
    verifie(connexions, 0, "fiche vivante : aucune connexion au port de l'outil")
    ecoute.close()
    os.remove(os.path.join(dossier, f"{p_pont}.json"))
    # Duree d'un etat avec tous les ports fermes (sondes en parallele).
    import time
    t0 = time.monotonic()
    pre.etat_outils({}, {o.id: {o.cle_port_page: libres[o.id]} for o in reg.OUTILS}, None)
    duree = time.monotonic() - t0
    verifie(duree < 1.0, True, f"etat_outils, ports fermes : {duree:.2f} s < 1.0 s")
    lances = {"pont_serie": {"pid": os.getpid(), "valeurs": {"port": "COM3"}}}
    e = etat("sniffeur_modbus", lances=lances, derniers={"sniffeur_modbus": {"port": "COM3"}})
    verifie((e["etat"], "COM3" in e["raison"], "Pont série" in e["raison"]), ("bloque", True, True), "com_tenu")
    e = etat("sniffeur_modbus", lances=lances, derniers={"sniffeur_modbus": {"port": "COM4"}})
    verifie(e["etat"], "arrete", "TEMOIN com_tenu : autre port libre")
    lances = {"pont_serie": {"pid": pid_mort(), "valeurs": {"port": "COM3"}}}
    e = etat("sniffeur_modbus", lances=lances, derniers={"sniffeur_modbus": {"port": "COM3"}})
    verifie(e["etat"], "arrete", "TEMOIN com_tenu : lance mort ne bloque pas")


def appel(port, methode, chemin, corps=None, entetes=None, hote="127.0.0.1"):
    """(statut, json ou None) d'une requete HTTP sur hote:port."""
    import http.client
    c = http.client.HTTPConnection(hote, port, timeout=10)
    donnees = None if corps is None else json.dumps(corps).encode("utf-8")
    c.request(methode, chemin, body=donnees, headers=dict(entetes or {}))
    r = c.getresponse()
    brut = r.read()
    c.close()
    try:
        return r.status, json.loads(brut.decode("utf-8"))
    except ValueError:
        return r.status, None


def tue_arbre(pr):
    """Tue le processus lance par CE test et ses enfants (par PID)."""
    subprocess.run(["taskkill", "/T", "/F", "/PID", str(pr.pid)], capture_output=True)
    try:
        pr.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def section_serveur():
    print("== serveur ==")
    import threading
    import time
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import acces_web
    import annuaire_outils as ann
    import annuaire_presence as pre
    from annuaire_lanceur import Lanceur

    racine = tempfile.mkdtemp()
    os.environ["OUTILS_TASMOTA_DOSSIER"] = racine
    dossier = str(acces_web.dossier_presence())
    libres = {o.id: port_libre() for o in reg.OUTILS}
    with open(os.path.join(racine, "derniers.json"), "w", encoding="utf-8") as f:
        json.dump({o.id: {o.cle_port_page: libres[o.id]} for o in reg.OUTILS}, f)

    lanceur = Lanceur(RACINE)
    lances, arrets = [], []
    reponse_arret = [True]

    def faux_lance(outil, args, valeurs=None):
        lances.append((outil.id, args, valeurs))
        return 4242
    lanceur.lance = faux_lance

    def faux_arrete(outil, pid):
        arrets.append((outil.id, pid))
        return reponse_arret[0]
    lanceur.arrete = faux_arrete

    acces = acces_web.Acces(0, False, "Annuaire des outils")
    srv = ann.Serveur(("0.0.0.0", 0), ann.fabrique_gestionnaire(lanceur, acces))
    port = srv.server_address[1]
    acces.port, acces.cookie = port, f"jeton_{port}"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    ent = {"X-Annuaire": "1"}

    def post(chemin, corps, entetes=ent, hote="127.0.0.1"):
        return appel(port, "POST", chemin, corps, entetes, hote)

    try:
        s, j = appel(port, "GET", "/registre")
        verifie((s, len(j["outils"])), (200, 9), "routes_get : /registre a 9 outils")
        s, j = appel(port, "GET", "/etat")
        verifie((s, len(j["outils"]), isinstance(j["liens_reseau"], list)), (200, 9, True),
                "routes_get : /etat a 9 entrees")
        verifie(isinstance(j.get("derniers"), dict), True, "routes_get : /etat porte derniers (dict)")
        verifie(appel(port, "GET", "/console?id=inconnu")[0], 404, "routes_get : console inconnue -> 404")
        verifie(appel(port, "GET", "/console?id=syslog")[1], {"lignes": []}, "routes_get : console vide")
        s, j = appel(port, "GET", "/ports")
        verifie((s, isinstance(j, list)), (200, True), "routes_get : /ports liste")
        verifie(appel(port, "GET", "/")[0], 200, "routes_get : page")
        verifie(appel(port, "GET", "/nimporte")[0], 404, "TEMOIN routes_get : route inconnue -> 404")

        verifie(post("/lance", {"id": "syslog", "valeurs": {}}), (200, {"pid": 4242}), "lance_ok : reponse")
        verifie(lances, [("syslog", ["--http", "7200", "--journal"], {})], "lance_ok : enregistreur")

        del lances[:]
        verifie(post("/lance", {"id": "sniffeur_modbus", "valeurs": {"port": "COM3 --x"}})[0], 400,
                "lance_refuse : valeur piegee -> 400")
        s, j = post("/lance", {"id": "sniffeur_modbus", "valeurs": {"debit": "12"}})
        verifie((s, "erreur" in j), (400, True), "lance_refuse : message d'erreur")
        verifie(post("/lance", {"id": "syslog", "valeurs": {}}, entetes={})[0], 403,
                "lance_refuse : sans X-Annuaire -> 403")
        verifie(post("/lance", {"id": "syslog", "valeurs": {}}, entetes=dict(ent, Origin="http://evil"))[0], 403,
                "lance_refuse : Origin etrangere -> 403")
        verifie(post("/lance", {"id": "zzz"})[0], 404, "lance : id inconnu -> 404")
        verifie(post("/arrete", {"id": "zzz"})[0], 404, "arrete : id inconnu -> 404")
        verifie(lances, [], "lance_refuse : enregistreur vide")
        verifie(post("/lance", {"id": "syslog", "valeurs": {}},
                     entetes=dict(ent, Origin=f"http://127.0.0.1:{port}"))[0], 200,
                "TEMOIN lance_refuse : meme origine -> 200")
        del lances[:]

        # outil deja en marche (fiche + port ouvert) -> 409 ; lance par l'annuaire -> peut etre arrete
        srv_outil, p_outil = serveur_libre()
        ecrit_fiche(dossier, "Serveur syslog", p_outil, os.getpid())
        s, j = post("/lance", {"id": "syslog", "valeurs": {}})
        verifie((s, lances), (409, []), "lance : outil en marche -> 409")
        verifie(post("/arrete", {"id": "syslog"}), (200, {"ok": True}), "arrete_ok : 200")
        verifie(arrets, [("syslog", os.getpid())], "arrete_ok : pid de la fiche")
        reponse_arret[0] = False
        verifie(post("/arrete", {"id": "syslog"}),
                (500, {"erreur": "Arret non confirme : le processus vit encore"}),
                "arrete : mort non confirmee -> 500")
        reponse_arret[0] = True
        lanceur.lances["syslog"] = {"pid": 4343, "valeurs": {}}
        del arrets[:]
        post("/arrete", {"id": "syslog"})
        verifie(arrets, [("syslog", 4343)], "arrete : pid de lanceur.lances prioritaire")
        del lanceur.lances["syslog"]
        ecrit_fiche(dossier, "Serveur syslog", p_outil, os.getpid(), lance_par="")
        verifie(post("/arrete", {"id": "syslog"})[0], 409, "arrete : outil lance ailleurs -> 409")
        verifie(post("/arrete", {"id": "syslog"}, entetes={})[0], 403, "arrete : sans X-Annuaire -> 403")
        srv_outil.close()
        os.remove(os.path.join(dossier, f"{p_outil}.json"))
        # fenetre de demarrage : lance connu, PID vivant, pas encore de fiche -> 409
        lanceur.lances["syslog"] = {"pid": os.getpid(), "valeurs": {}}
        verifie(post("/lance", {"id": "syslog", "valeurs": {}})[0], 409,
                "lance : demarrage en cours (pid vivant) -> 409")
        lanceur.lances["syslog"] = {"pid": pid_mort(), "valeurs": {}}
        verifie(post("/lance", {"id": "syslog", "valeurs": {}})[0], 200, "TEMOIN lance : ancien pid mort -> 200")
        del lanceur.lances["syslog"]

        # lancements concurrents du meme outil : un seul doit partir
        def lance_lent(outil, args, valeurs=None):
            lances.append((outil.id, args, valeurs))
            time.sleep(0.4)
            lanceur.lances[outil.id] = {"pid": os.getpid(), "valeurs": dict(valeurs or {})}
            return 4242
        del lances[:]
        lanceur.lance = lance_lent
        reponses = []
        fils = [threading.Thread(target=lambda: reponses.append(post("/lance", {"id": "syslog", "valeurs": {}})[0]))
                for _ in range(2)]
        for t in fils:
            t.start()
        for t in fils:
            t.join()
        verifie((sorted(reponses), len(lances)), ([200, 409], 1), "lance_concurrent : un 200, un 409, un seul lancement")
        del lanceur.lances["syslog"]
        del lances[:]
        lanceur.lance = faux_lance

        # synchro : faux serveur /execution sur un port libre, fiche factice pointant dessus
        etat_synchro = {"en_cours": True}

        class Faux(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                corps = json.dumps(etat_synchro).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Length", str(len(corps)))
                self.end_headers()
                self.wfile.write(corps)
        faux = HTTPServer(("127.0.0.1", 0), Faux)
        threading.Thread(target=faux.serve_forever, daemon=True).start()
        p_sync = faux.server_address[1]
        ecrit_fiche(dossier, "Synchro du fork", p_sync, os.getpid())
        del arrets[:]
        verifie(post("/arrete", {"id": "synchro_fork"}),
                (409, {"erreur": "Une operation de synchro est en cours : arret refuse"}),
                "arret_synchro_refuse : en_cours true -> 409")
        verifie(arrets, [], "arret_synchro_refuse : rien arrete")
        etat_synchro["en_cours"] = False
        verifie(post("/arrete", {"id": "synchro_fork"})[0], 200, "TEMOIN arret_synchro : en_cours false -> 200")
        verifie(arrets, [("synchro_fork", os.getpid())], "arret_synchro : arret demande")
        faux.shutdown()
        faux.server_close()
        os.remove(os.path.join(dossier, f"{p_sync}.json"))

        # acces distant
        ips = acces_web.ips_reseau()
        if not ips:
            print("SAUTE  acces_distant : aucune adresse reseau sur ce PC")
        else:
            import test_acces_web
            ip = ips[0]
            verifie(test_acces_web.cas_refus(acces, ip, port), 4, f"acces_distant : 4 refus sans jeton ({ip})")
            verifie(appel(port, "GET", "/etat", hote=ip)[0], 403, "acces_distant : /etat sans jeton -> 403")
            cookie = {"Cookie": f"{acces.cookie}={acces.jeton}"}
            s, j = appel(port, "GET", "/etat", entetes=cookie, hote=ip)
            verifie((s, j["liens_reseau"]), (200, []), "acces_distant : avec jeton -> 200, pas de liens reseau")
            verifie(post("/lance", {"id": "syslog", "valeurs": {}}, hote=ip)[0], 403,
                    "acces_distant : POST sans jeton -> 403")
            s, _ = post("/lance", {"id": "sniffeur_modbus", "valeurs": {"debit": "12"}},
                        entetes=dict(ent, **cookie, Origin=f"http://{ip}:{port}"), hote=ip)
            verifie(s, 400, "acces_distant : POST avec jeton atteint la validation")
    finally:
        srv.shutdown()
        srv.server_close()

    # double demarrage : vrais sous-processus, dans le dossier de donnees de test
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "annuaire_outils.py")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    flags = 0x08000000 if os.name == "nt" else 0

    def lance_annuaire(p):
        return subprocess.Popen([sys.executable, script, "--http", str(p), "--sans-navigateur"], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                creationflags=flags, text=True)
    p1 = p2 = p3 = None
    sock = None
    try:
        pa = port_libre()
        p1 = lance_annuaire(pa)
        fin = time.monotonic() + 20
        while time.monotonic() < fin and not (pre.port_repond(pa)
                                              and os.path.exists(os.path.join(dossier, f"{pa}.json"))):
            time.sleep(0.2)
        verifie(pre.port_repond(pa), True, "double_demarrage : le premier ecoute")
        p2 = lance_annuaire(pa)
        sortie, _ = p2.communicate(timeout=30)
        verifie((p2.returncode, sortie), (0, ""), "double_demarrage : le second sort en 0 sans rien afficher")
        verifie(p1.poll(), None, "double_demarrage : le premier tourne toujours")
        sock, q = serveur_libre()
        p3 = lance_annuaire(q)
        sortie, _ = p3.communicate(timeout=30)
        verifie((p3.returncode, f"Port {q} deja utilise par un autre programme" in sortie), (1, True),
                "double_demarrage : port pris par un autre programme -> 1 et message")
    finally:
        for pr in (p1, p2, p3):
            if pr is not None and pr.poll() is None:
                tue_arbre(pr)
        if sock:
            sock.close()
        os.environ.pop("OUTILS_TASMOTA_DOSSIER", None)


def principal():
    section_registre()
    print()
    section_presence()
    print()
    section_serveur()
    print()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    return 0 if not ECHECS else 1


if __name__ == "__main__":
    sys.exit(principal())
