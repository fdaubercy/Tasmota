"""Banc de build_reparations (plan build-reparations A1) : catalogue, correspondance sur la fin du journal, filtre des secrets.

UTILISATION (Python de PlatformIO, depuis la racine du depot)
    python outils_docs/scripts_python/outils_pc/test_build_reparations.py
Code de sortie 0 = vert. Mutants : le module est recharge avec une garde retiree ; le banc doit alors passer au rouge.
"""

import importlib
import json
import sys
import tempfile
import time
from pathlib import Path

import build_reparations as br

ECHECS = []
SILENCE = []


def verifie(nom, condition):
    if not condition:
        ECHECS.append(nom)
        if not SILENCE:
            print("ECHEC :", nom)


def leve(f, *a):
    try:
        f(*a)
    except ValueError:
        return True
    return False


def ecrit(dossier, nom, contenu):
    p = Path(dossier) / nom
    p.write_text(json.dumps(contenu), encoding="utf-8")
    return p


def regle(**kw):
    r = {"id": "r1", "titre": "T", "motif": "boom", "etapes": ["compilation"],
         "actions": [{"action": "attendre", "parametres": {"secondes": 1}}], "origine": "base", "ajoutee_le": "2026-11-14"}
    r.update(kw)
    return r


def passe_catalogue(d):
    # fusion, local gagne sur l'id, suppressions locales
    base = ecrit(d, "base.json", {"regles": [regle(id="a"), regle(id="b", motif="zut")]})
    loc = ecrit(d, "loc.json", {"regles": [regle(id="b", motif="autre", origine="ia"), regle(id="c")], "supprimees": ["a"]})
    rs = br.charge_catalogue(base, loc)
    verifie("fusion + suppression", sorted(r.id for r in rs) == ["b", "c"])
    verifie("local remplace la base", [r for r in rs if r.id == "b"][0].motif == "autre")
    verifie("local absent = base seule", len(br.charge_catalogue(base, Path(d) / "nexiste.pas")) == 2)
    # refus
    for nom, mauvais in [("action hors liste", regle(actions=[{"action": "rm", "parametres": {}}])),
                         ("motif invalide", regle(motif="(")),
                         ("attendre sans secondes", regle(actions=[{"action": "attendre", "parametres": {}}])),
                         ("secondes negatives", regle(actions=[{"action": "attendre", "parametres": {"secondes": -1}}])),
                         ("sans actions", regle(actions=[])),
                         ("secondes trop grandes", regle(actions=[{"action": "attendre", "parametres": {"secondes": 3601}}])),
                         ("etape upload", regle(etapes=["upload"])),
                         ("etape erase_upload", regle(etapes=["compilation", "erase_upload"])),
                         ("etapes vide", regle(etapes=[]))]:
        p = ecrit(d, "mauvais.json", {"regles": [mauvais]})
        verifie("refus : " + nom, leve(br.charge_catalogue, p, Path(d) / "nexiste.pas"))
    casse = Path(d) / "casse.json"
    casse.write_text("{", encoding="utf-8")
    verifie("refus : json de base casse", leve(br.charge_catalogue, casse, Path(d) / "x"))
    # local fautif : ignore et signale, la base reste
    loc = ecrit(d, "loc2.json", {"regles": [regle(id="mauvaise", motif="("), regle(id="bonne")], "supprimees": "a"})
    rs, av = br.charge_catalogue_avec_avertissements(base, loc)
    verifie("local : regle fautive ignoree", sorted(r.id for r in rs) == ["a", "b", "bonne"] and len(av) == 2)
    rs, av = br.charge_catalogue_avec_avertissements(base, casse)
    verifie("local casse : base seule + avertissement", sorted(r.id for r in rs) == ["a", "b"] and len(av) == 1)
    verifie("charge_catalogue rend la liste seule", isinstance(br.charge_catalogue(base, casse), list))


def passe_catalogue_depot():
    # la regle de base livree se charge et reconnait le cas d'origine, pas un port COM
    racine = Path(__file__).resolve().parents[3]
    rs = br.charge_catalogue(racine / "outils_docs" / "schemas" / "reparations_build.json", Path("absent.json"))
    verifie("regle de base verrou_fichier", [r.id for r in rs] == ["verrou_fichier"])
    j = ("[1/3] ...\nPermissionError: [Errno 13] Permission denied: "
         "'C:\\\\Users\\\\x\\\\Documents\\\\Github\\\\Tasmota\\\\lib\\\\libesp32\\\\berry_custom\\\\src\\\\modules.h'\n*** error")
    verifie("verrou du depot reconnu", br.cherche(rs, j, "compilation", "e") is not None)
    verifie("port COM ignore", br.cherche(rs, "PermissionError: [Errno 13] Permission denied: 'COM7'", "compilation", "e") is None)
    verifie("actions de base", [a["action"] for a in rs[0].actions] == ["libere_verrou", "attendre"])


def passe_cherche(d):
    rs = br.charge_catalogue(ecrit(d, "b.json", {"regles": [
        regle(id="x", motif="boom", etapes=["compilation"]),
        regle(id="y", motif="zut", etapes=["toutes"])]}), Path(d) / "n")
    verifie("trouve", br.cherche(rs, "a\nboom\n", "compilation", "e").id == "x")
    verifie("mauvaise etape", br.cherche(rs, "boom", "liens", "e") is None)
    verifie("toutes les etapes", br.cherche(rs, "zut", "liens", "e").id == "y")
    verifie("journal vide", br.cherche(rs, "", "compilation", "e") is None)
    verifie("sans correspondance", br.cherche(rs, "rien", "compilation", "e") is None)
    # fin du journal seulement : une ligne a 51 lignes de la fin ne compte pas
    vieux = "boom\n" + "ok\n" * br.LIGNES_FIN
    verifie("hors des 50 dernieres lignes", br.cherche(rs, vieux, "compilation", "e") is None)
    verifie("dans les 50 dernieres lignes", br.cherche(rs, "boom\n" + "ok\n" * (br.LIGNES_FIN - 1), "compilation", "e") is not None)
    # journal de 100 000 lignes : rapide
    gros = "ligne de journal assez longue pour peser\n" * 100000 + "boom\n"
    t = time.time()
    r = br.cherche(rs, gros, "compilation", "e")
    verifie("100 000 lignes rapide", r is not None and time.time() - t < 2)


def passe_secrets():
    cas = [('#define STA_PASS1 "motdepasse1"', "motdepasse1"), ("-DSTA_PASS=abc123def", "abc123def"),
           ('#define MQTT_PASS "m-q-t-t"', "m-q-t-t"), ('OTA_PASS = "ota secret"', "ota secret"),
           ('"password": "pw-json"', "pw-json"), ("PASSWORD=azerty", "azerty"), ("token: ghp_abcdef123456", "ghp_abcdef123456"),
           ("Token=XyZ", "XyZ"),
           ('-DSTA_PASS=\\"abc def\\"', "abc def"), ("Authorization: Bearer eyJabc.def", "eyJabc.def"),
           ("-DWIFI_PW=zz99", "zz99"), ("PW=qq88", "qq88"), ("_PW: ww77", "ww77")]
    for texte, valeur in cas:
        sortie = br.filtre_secrets("avant\n" + texte + "\napres")
        verifie("masque : " + texte, valeur not in sortie and "avant" in sortie and "apres" in sortie)
    t = time.time()
    br.filtre_secrets("PASS" * 50000 + " " + "a" * 100000)
    verifie("filtre non quadratique", time.time() - t < 2)
    verifie("nom de la cle gardee", "STA_PASS1" in br.filtre_secrets('#define STA_PASS1 "x1y2"'))
    neutre = "pass through now\ntoken bucket full\nPermission denied: 'C:\\x\\modules.h'\nbypassed passed\nSTA_SSID \"maison\""
    verifie("texte sans secret intact", br.filtre_secrets(neutre) == neutre)


VERROU = "PermissionError: [Errno 13] Permission denied: 'C:\\\\Users\\\\x\\\\Documents\\\\Github\\\\Tasmota\\\\lib\\\\{f}'"


def passe_reparateur(d):
    """A3 : Reparateur.traite / repond_choix sur une vraie Serie jamais lancee (aucun pio)."""
    import threading
    import build_serie as bs
    racine = Path(d) / "depot"
    racine.mkdir(exist_ok=True)
    regles = br.charge_catalogue(ecrit(d, "rep.json", {"regles": [regle(
        id="v", motif=r"PermissionError: \[Errno 13\] Permission denied: '[^']*Tasmota", etapes=["compilation", "prebuild"],
        actions=[{"action": "libere_verrou", "parametres": {}}, {"action": "attendre", "parametres": {"secondes": 0}}])]}),
        Path(d) / "n")
    libres = []

    def faux_libere(chemin, liste, pid, demande):
        libres.append(chemin)
        return {"libre": True, "ferme": [], "attend": [], "demande": [], "refuse": []}

    def rep(**kw):
        s = bs.Serie(racine, Path(d) / "donnees", builds_en_cours=lambda: [], sondage=0.05)
        kw.setdefault("libere", faux_libere)
        return s, br.Reparateur(s, regles, chemin_local=Path(d) / "local.json", **kw)

    L = bs.Ligne("e1", "com", "COM5", "")
    s, r = rep()
    j1 = "Compiling a.o\n" + VERROU.format(f="modules.h") + "\n[FAILED] Took 1 s"
    verifie("traite : verrou reconnu -> relance", r.traite(L, "compiler", "", "Compilation", j1, []) is True)
    verifie("traite : chemin extrait, backslashes simples",
            libres[-1:] == ["C:\\Users\\x\\Documents\\Github\\Tasmota\\lib\\modules.h"])
    verifie("traite : meme panne identique -> pas deux fois", r.traite(L, "compiler", "", "Compilation", j1, []) is False)
    etats = [e["etat"] for e in s.evenements if e["type"] == "reparation"]
    verifie("traite : en_cours puis echouee", etats == ["en_cours", "echouee"])
    s, r = rep()
    vus = [r.traite(L, "compiler", "", "Compilation", VERROU.format(f=f"f{i}.h"), []) for i in range(4)]
    verifie("traite : 2 relances au plus par etape", vus == [True, True, False, False])
    verifie("traite : autre etape, compteur a part", r.traite(L, "buildfs", "buildfs", "Pré-build", j1, []) is True)
    s, r = rep()
    for cible in ("upload", "erase_upload", "nobuild upload", "uploadfs"):
        verifie("traite : jamais un envoi (" + cible + ")", r.traite(L, "upload", cible, "Compilation", j1, []) is False)
    verifie("traite : etape d'envoi refusee", r.traite(L, "compiler", "", "Téléversement", j1, []) is False)
    verifie("traite : sans regle", r.traite(L, "compiler", "", "Compilation", "error: x\n[FAILED]", []) is False)
    verifie("traite : journal vide", r.traite(L, "compiler", "", "Compilation", "", []) is False)
    verifie("traite : chemin absent du journal", br.Reparateur(s, br.charge_catalogue(ecrit(d, "r2.json", {"regles": [regle(
        id="w", motif="boom", actions=[{"action": "libere_verrou", "parametres": {}}])]}), Path(d) / "n"),
        libere=faux_libere).traite(L, "compiler", "", "Compilation", "boom", []) is False)
    s, r = rep()
    s._arret = True
    verifie("traite : arret demande -> rien", r.traite(L, "compiler", "", "Compilation", j1, []) is False)
    # choix : demande ouverte, reponse, refus d'une 2e reponse ; choix inconnu
    for choix, attendu in (("fermer", True), ("annuler", False)):
        def libere_demande(chemin, liste, pid, demande):
            ok = demande({"pid": 77, "nom": "outil.exe", "ligne": "outil.exe --password=secret123"})
            return {"libre": True, "ferme": [], "attend": [], "demande": [], "refuse": [], "ok": ok}
        s, r = rep(libere=libere_demande)
        rendu = []
        t = threading.Thread(target=lambda: rendu.append(r.traite(L, "compiler", "", "Compilation", j1, [])))
        t.start()
        for _ in range(100):
            if any(e["type"] == "choix_reparation" for e in s.evenements):
                break
            time.sleep(0.02)
        ch = [e for e in s.evenements if e["type"] == "choix_reparation"]
        verifie("choix : emis, sans secret", len(ch) == 1 and "secret123" not in ch[0]["texte"] and "outil.exe" in ch[0]["texte"])
        verifie("choix : inconnu -> ValueError", leve(r.repond_choix, "e1", "zz"))
        r.repond_choix("e1", choix)
        t.join(5)
        verifie("choix : " + choix, rendu == [attendu])
        try:
            r.repond_choix("e1", choix)
            verifie("choix : 2e reponse refusee", False)
        except RuntimeError:
            pass
    # expiration a 10 min (horloge injectee)
    horloge = [0.0]
    s, r = rep(libere=libere_demande, horloge=lambda: horloge[0])
    rendu = []
    t = threading.Thread(target=lambda: rendu.append(r.traite(L, "compiler", "", "Compilation", j1, [])))
    t.start()
    time.sleep(0.2)
    horloge[0] = 599
    time.sleep(0.2)
    verifie("choix : toujours ouvert avant 10 min", t.is_alive())
    horloge[0] = 601
    t.join(5)
    verifie("choix : expire -> pas de reparation", rendu == [False])
    try:
        r.repond_choix("e1", "fermer")
        verifie("choix : reponse apres expiration refusee", False)
    except RuntimeError:
        pass
    # vide_build : le dossier de l'env rate seulement
    for env in ("e1", "e2"):
        (racine / ".pio" / "build" / env).mkdir(parents=True, exist_ok=True)
    s, r = rep()
    r.regles = br.charge_catalogue(ecrit(d, "r3.json", {"regles": [regle(
        id="vb", motif="boom", actions=[{"action": "vide_build", "parametres": {}}])]}), Path(d) / "n")
    verifie("vide_build : relance", r.traite(L, "compiler", "", "Compilation", "boom", []) is True)
    verifie("vide_build : seul l'env rate", (not (racine / ".pio/build/e1").exists(), (racine / ".pio/build/e2").exists())
            == (True, True))
    # regle locale
    n = r.ajoute_regle_locale(regle(id="ia1", origine="ia"))
    lu = json.loads((Path(d) / "local.json").read_text(encoding="utf-8"))
    verifie("ajoute_regle_locale : ecrite et en memoire", [x["id"] for x in lu["regles"]] == ["ia1"] and n in r.regles)
    verifie("ajoute_regle_locale : regle invalide refusee", leve(r.ajoute_regle_locale, regle(motif="(")))


def mutant(nom, remplace_ancien, remplace_nouveau):
    """Recharge le module avec une garde retiree et rejoue le banc : il doit echouer."""
    source = Path(br.__file__).read_text(encoding="utf-8")
    verifie("mutant applicable : " + nom, remplace_ancien in source)
    avant = len(ECHECS)
    SILENCE.append(1)
    try:
        ns = {"__name__": "build_reparations_mutant", "__file__": br.__file__}
        exec(compile(source.replace(remplace_ancien, remplace_nouveau, 1), br.__file__, "exec"), ns)
        sys.modules["build_reparations"] = type(sys)("m")
        sys.modules["build_reparations"].__dict__.update(ns)
        globals()["br"] = sys.modules["build_reparations"]
        with tempfile.TemporaryDirectory() as d:
            for f in (lambda: passe_catalogue(d), passe_catalogue_depot, lambda: passe_cherche(d), passe_secrets,
                      lambda: passe_reparateur(d)):
                try:
                    f()
                except Exception:
                    ECHECS.append("exception")
    finally:
        rouge = len(ECHECS) > avant
        SILENCE.clear()
        del ECHECS[avant:]
        sys.modules["build_reparations"] = importlib.import_module("build_reparations")
        globals()["br"] = sys.modules["build_reparations"]
    verifie("mutant tue : " + nom, rouge)


def main():
    with tempfile.TemporaryDirectory() as d:
        passe_catalogue(d)
        passe_catalogue_depot()
        passe_cherche(d)
        passe_reparateur(d)
    passe_secrets()
    if ECHECS:
        print(len(ECHECS), "echec(s)")
        return 1
    mutant("action hors liste acceptee", "if nom not in ACTIONS", "if False")
    mutant("motif non borne a la fin du journal", "\"\\n\".join(lignes[-LIGNES_FIN:])", "journal")
    mutant("secrets non filtres", "return _SECRET.sub(", "return texte; _SECRET.sub(")
    mutant("limite de relances retiree", "self._relances.get(cle, 0) >= RELANCES_MAX", "False")
    mutant("boucle sans signature", "signature in vus", "False")
    mutant("relance d'un envoi", "cible.split()[-1:] not in ([], [\"buildfs\"])", "False")
    if ECHECS:
        print(len(ECHECS), "echec(s)")
        return 1
    print("test_build_reparations : tout est vert")
    return 0


if __name__ == "__main__":
    sys.exit(main())
