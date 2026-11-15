"""Banc REEL du jeton commun : de vrais processus. Code de sortie 0 = vert.

UTILISATION (a la main, ~40 s, hors de tout build : aucun pio, mais un vrai outil Build est lance puis arrete)
    python outils_docs/scripts_python/outils_pc/test_jeton_reel.py
Un annuaire ISOLE (port 17600, dossier de donnees temporaire OUTILS_TASMOTA_DOSSIER : l'annuaire reel et ses outils
vivants ne sont ni touches ni interroges) lance le vrai outil Build (port 17700, hors job). Les requetes partent de
l'adresse reseau de ce PC (= autre appareil : jeton exige). Verifie : jeton de l'outil = jeton de l'annuaire ; le cookie
de l'un ouvre l'autre (barre Annuaire) ; /_barre.json ; puis l'annuaire est tue et relance (nouveau jeton) : l'outil
survit, garde son ancien jeton, accepte le nouveau ; l'annuaire refuse l'ancien. Sans adresse reseau : arret sans rien lancer.
"""
import sys as _sys, pathlib as _pl  # suivi de l'avancement sur la page Sondes en cours
_sys.path.append(str(_pl.Path(__file__).resolve().parent.parent / "outils_pc"))
import suivi_sondes as _suivi; _suivi.suit_si_script_test()
import http.client, json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PC = Path(__file__).resolve().parent
sys.path.insert(0, str(PC))
import acces_web

PORT_A, PORT_B = 17600, 17700
tmp = Path(tempfile.mkdtemp(prefix="essai_jeton_"))
env = dict(os.environ, OUTILS_TASMOTA_DOSSIER=str(tmp), PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
env.pop(acces_web.VAR_JETON, None)
ips = acces_web.ips_reseau()
if not ips:
    sys.exit("aucune adresse reseau : essai impossible")
IP = ips[0]
RES = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    RES.append(ok)
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)


def requete(hote, port, chemin="/", cookie=None, methode="GET", corps=None, entetes=None):
    c = http.client.HTTPConnection(hote, port, timeout=10)
    h = dict(entetes or {})
    if cookie:
        h["Cookie"] = cookie
    c.request(methode, chemin, body=corps, headers=h)
    r = c.getresponse()
    d = r.read()
    c.close()
    return r.status, d


def attend(cond, delai=30):
    fin = time.monotonic() + delai
    while time.monotonic() < fin:
        try:
            v = cond()
            if v:
                return v
        except Exception:
            pass
        time.sleep(0.3)
    return None


def fiche(port):
    f = tmp / "presence" / f"{port}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else None


def lance_annuaire():
    p = subprocess.Popen([sys.executable, "-u", str(PC / "annuaire_outils.py"), "--http", str(PORT_A), "--sans-navigateur"],
                         cwd=str(REPO), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    verifie(bool(attend(lambda: fiche(PORT_A) and requete("127.0.0.1", PORT_A, "/registre")[0] == 200, 60)), True,
            "annuaire isole demarre")
    return p


def poste(chemin, donnees):
    return requete("127.0.0.1", PORT_A, chemin, methode="POST", corps=json.dumps(donnees),
                   entetes={"X-Annuaire": "1", "Content-Type": "application/json", "Origin": f"http://127.0.0.1:{PORT_A}"})


annuaire = outil_pid = None
try:
    annuaire = lance_annuaire()
    t1 = fiche(PORT_A)["jeton"]
    st, d = poste("/lance", {"id": "build", "valeurs": {"http": PORT_B}})
    verifie(st, 200, f"POST /lance build : {d[:80]!r}")
    verifie(bool(attend(lambda: fiche(PORT_B), 60)), True, "outil Build demarre, fiche de presence ecrite")
    fb = fiche(PORT_B) or {}
    outil_pid = fb.get("pid")
    verifie(fb.get("jeton") == t1, True, "REEL : l'outil lance a le meme jeton que l'annuaire")
    verifie(fb.get("lance_par"), "annuaire", "REEL : lance_par = annuaire")

    # « autre appareil » : adresse reseau de ce PC
    verifie(requete(IP, PORT_B)[0], 403, f"autre appareil ({IP}) : outil sans jeton refuse")
    verifie(requete(IP, PORT_A)[0], 403, "autre appareil : annuaire sans jeton refuse")
    st, _ = requete(IP, PORT_B, f"/?jeton={t1}")
    verifie(st, 303, "autre appareil : lien a jeton de l'outil -> 303 (cookie)")
    verifie(requete(IP, PORT_B, cookie=f"jeton_{PORT_B}={t1}")[0], 200, "autre appareil : outil avec son cookie")
    verifie(requete(IP, PORT_A, cookie=f"jeton_{PORT_B}={t1}")[0], 200,
            "REEL : le cookie de l'outil ouvre l'annuaire (barre « Annuaire » depuis un autre appareil)")
    verifie(requete(IP, PORT_B, cookie=f"jeton_{PORT_A}={t1}")[0], 200, "REEL : le cookie de l'annuaire ouvre l'outil")
    verifie(requete(IP, PORT_A, cookie=f"jeton_{PORT_B}=jeton-faux-1234567890")[0], 403, "mauvais jeton refuse")
    st, d = requete(IP, PORT_B, "/_barre.json", cookie=f"jeton_{PORT_B}={t1}")
    ids = [o["id"] for o in json.loads(d).get("outils", [])] if st == 200 else st
    verifie(ids, ["build"], "REEL : /_barre.json de l'outil liste l'outil vivant (hors annuaire)")
    st, d = requete("127.0.0.1", PORT_A, "/etat")
    etat = {o["id"]: o for o in json.loads(d)["outils"]} if st == 200 else {}
    verifie((etat.get("build", {}).get("etat"), etat.get("build", {}).get("lie")), ("marche", False),
            "annuaire : Build en marche, non lie (hors job)")

    # Redemarrage de l'annuaire : l'outil survit (hors job), garde son jeton, accepte le NOUVEAU jeton de l'annuaire
    annuaire.kill()
    annuaire.wait(10)
    time.sleep(2)
    vit = acces_web.pid_vivant(outil_pid)
    verifie(vit, True, "REEL : l'outil Build survit a l'arret de l'annuaire")
    if vit:
        (tmp / "presence" / f"{PORT_A}.json").unlink(missing_ok=True)
        annuaire = lance_annuaire()
        t2 = fiche(PORT_A)["jeton"]
        verifie(t2 != t1, True, "nouvel annuaire : nouveau jeton")
        verifie(requete(IP, PORT_B, cookie=f"jeton_{PORT_A}={t2}")[0], 200,
                "REEL : l'outil survivant accepte le NOUVEAU jeton de l'annuaire")
        verifie(requete(IP, PORT_B, cookie=f"jeton_{PORT_B}={t1}")[0], 200, "REEL : l'outil survivant garde son ancien jeton")
        verifie(requete(IP, PORT_A, cookie=f"jeton_{PORT_B}={t1}")[0], 403, "REEL : le nouvel annuaire refuse l'ancien jeton")
        verifie(requete(IP, PORT_B, cookie=f"jeton_{PORT_A}=jeton-faux-1234567890")[0], 403, "survivant : jeton quelconque refuse")
        st, _ = poste("/arrete", {"id": "build"})
        verifie(st, 200, "POST /arrete build")
        verifie(bool(attend(lambda: not acces_web.pid_vivant(outil_pid), 20)), True, "outil Build arrete")
finally:
    if annuaire and annuaire.poll() is None:
        annuaire.kill()
    if outil_pid and acces_web.pid_vivant(outil_pid):
        subprocess.run(["taskkill", "/F", "/PID", str(outil_pid)], capture_output=True)
    time.sleep(1)
    shutil.rmtree(tmp, ignore_errors=True)
print("\nVERT" if all(RES) else f"ROUGE : {RES.count(False)} echec(s)")
