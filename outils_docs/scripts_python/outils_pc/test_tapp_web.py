#!/usr/bin/env python3
"""Banc de la Fabrique d'extensions (tapp_web.py, tapp_sources.py) : routes, anti-CSRF, Host, jeton, noms hostiles, jamais
d'ecrasement, manifeste, controle, fabrication, gabarits egaux au document, secrets. L'envoi : test_tapp_envoi.py.

Depot temporaire (test_assistant_persist_autoexec.depot), serveur reel sur 127.0.0.1, port libre. Aucune carte, aucun pio.
Temoins : des mutants (copie du module modifiee en dossier temporaire, banc relance avec TAPP_MUTANT=<dossier>) doivent
passer KO sur LE test vise. Code 0 = vert.

Python de PlatformIO : <~/.platformio/penv/Scripts/python.exe> outils_docs/scripts_python/outils_pc/test_tapp_web.py
"""
import http.client
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path

if os.environ.get("TAPP_MUTANT"):
    sys.path.insert(0, os.environ["TAPP_MUTANT"])
    sys.path.append(str(Path(__file__).resolve().parents[1] / "berry"))     # gen_tapp : le mutant n'est plus a cote de berry/

import acces_web
import tapp_sources as ts                                # pose aussi berry/ dans sys.path
import gen_tapp
import tapp_web as tw
import test_assistant_persist_autoexec as taa
import test_assistant_persist_web as taw

ICI = Path(__file__).resolve().parent
DOC = ICI.parents[1] / "EXTENSIONS_TAPP.md"
ENTETES = {"X-Fabrique-Tapp": "1", "Content-Type": "application/json"}
ECHECS = []
REPONSES = []                    # texte de toutes les reponses, pour la recherche des secrets
HOSTILES = ["..", "../x", "..\\x", "a/b", "a\\b", "", ".", "C:\\x", "C:", "/abs", "\\\\srv\\x", "CON", "con", "NUL", "aux", "PRN", "com1",
            "COM9", "lpt1", "a b", "é", "a.b", "x.tapp", "x" * 32, "x" * 40, "x\n", "x\r\n", "%2e%2e", 5, None, ["x"], {"a": 1}, True]


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"))
    if not ok:
        ECHECS.append(libelle)
    return ok


def port_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Serveur:
    """Le vrai gestionnaire de tapp_web sur 127.0.0.1 ; `requete` garde chaque reponse pour la recherche des secrets."""

    def __init__(self, racine, builds=lambda: []):
        self.port = port_libre()
        self.acces = acces_web.Acces(self.port, True, "Fabrique d'extensions")
        self.serveur = ThreadingHTTPServer(("127.0.0.1", self.port), tw.fabrique_gestionnaire(self.acces, racine, builds))
        self.serveur.daemon_threads = True
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()

    def ferme(self):
        self.serveur.shutdown()
        self.serveur.server_close()

    def brut(self, methode, chemin, corps=None, entetes=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        donnees = None if corps is None else (corps if isinstance(corps, bytes) else json.dumps(corps).encode("utf-8"))
        c.request(methode, chemin, body=donnees, headers=dict(ENTETES if entetes is None else entetes))
        r = c.getresponse()
        texte = r.read().decode("utf-8", "replace")
        c.close()
        REPONSES.append(texte)
        return r.status, texte, r

    def requete(self, methode, chemin, corps=None, entetes=None):
        statut, texte, _ = self.brut(methode, chemin, corps, entetes)
        try:
            return statut, json.loads(texte)
        except ValueError:
            return statut, texte


def arbre(racine):
    """Empreinte du dossier data/ : (chemin relatif, taille, date) de tout ce qu'il contient."""
    return sorted((str(p.relative_to(racine)), p.stat().st_size, p.stat().st_mtime_ns) for p in (Path(racine) / "data").rglob("*") if p.is_file())


def blocs_du_document():
    """{(gabarit, fichier): texte} des blocs de code des § 5.2 et § 5.3 d'EXTENSIONS_TAPP.md, lu dans le vrai depot."""
    texte = DOC.read_text(encoding="utf-8")
    res = {}
    for gabarit, debut, fin in (("A", "### 5.2", "### 5.3"), ("B", "### 5.3", "### 5.4")):
        section = texte[texte.index(debut):texte.index(fin)]
        for m in re.finditer(r"^`([\w.]+)`\n```\w*\n(.*?)^```$", section, re.S | re.M):
            res[gabarit, m.group(1)] = m.group(2)
    return res


def gabarits(s, racine):
    blocs = blocs_du_document()
    verifie(sorted(blocs), [("A", "autoexec.be"), ("A", "manifest.json"), ("B", "autoexec.be"), ("B", "mon_ext.be")], "document : les 4 blocs des gabarits lus")
    for (g, f), texte in blocs.items():
        verifie(ts.GABARITS[g]["fichiers"].get(f) == texte, True, f"gabarit {g} : {f} identique au document")
    a, b = (json.loads(ts.GABARITS[g]["fichiers"]["manifest.json"]) for g in "AB")
    verifie((sorted(b), b["name"], "fsMqtt" in b["description"]), (sorted(a), "Mon extension", False), "gabarit B : manifeste de meme forme que A, nom du document, description neutre")
    verifie(sorted(ts.GABARITS["B"]["fichiers"]), ["autoexec.be", "manifest.json", "mon_ext.be"], "gabarit B : ses 3 fichiers")
    with tempfile.TemporaryDirectory() as t:
        for g in "AB":
            d = Path(t) / f"essai_{g}"
            d.mkdir()
            for f, texte in ts.GABARITS[g]["fichiers"].items():
                (d / f).write_text(texte, encoding="utf-8", newline="")
            verifie(gen_tapp.construit(d).is_file(), True, f"gabarit {g} : gen_tapp.construit accepte")
    st, g = s.requete("GET", "/extensions")
    verifie([x["id"] for x in g["gabarits"]], ["A", "B"], "GET /extensions : les deux gabarits proposes")
    verifie(all(x["libelle"] and x["explication"] for x in g["gabarits"]), True, "GET /extensions : chaque gabarit s'explique")


def etat_vide(s, racine):
    st, r = s.requete("GET", "/extensions")
    verifie((st, r["extensions"], r["ignores"]), (200, [], []), "premiere ouverture : liste vide, pas d'erreur")
    verifie((Path(racine) / "data" / "extensions").exists(), False, "premiere ouverture : un GET ne cree rien")
    st, page, rep = s.brut("GET", "/")
    verifie((st, "<title>Fabrique d'extensions</title>" in page, rep.getheader("Cache-Control")), (200, True, "no-store"), "GET / : la page")
    verifie("innerHTML" in page, False, "page : jamais d'innerHTML")
    verifie(("prefers-color-scheme" in page, 'data-theme="sombre"' in page, "max-width" in page), (True, True, True), "page : mode sombre et largeur de telephone")
    verifie("outils_docs/EXTENSIONS_TAPP.md" in page, True, "page : le document est nomme")
    st, r = s.requete("GET", "/inconnue")
    verifie(st, 404, "GET route inconnue -> 404")


def noms_hostiles(s, racine):
    avant = arbre(racine)
    for nom in HOSTILES:
        st, _ = s.requete("POST", "/creer", {"nom": nom, "gabarit": "A"})
        verifie(st, 400, f"creer, nom hostile {nom!r} -> 400")
        for route in ("/manifeste", "/verifie", "/fabrique", "/envoi/prepare", "/envoi"):
            st, _ = s.requete("POST", route, {"nom": nom, "name": "x", "env": "x", "jeton": "x"})
            verifie(st, 400, f"{route}, nom hostile {nom!r} -> 400")
    for brut in ("..", "..%2Fx", "a%5Cb", "CON", "x%0A", "", "x" * 32):
        verifie(s.requete("GET", "/extension?nom=" + brut)[0], 400, f"GET /extension nom hostile {brut!r} -> 400")
    verifie(s.requete("GET", "/extension")[0], 400, "GET /extension sans nom -> 400")
    verifie(s.requete("GET", "/extension?nom=absente")[0], 404, "GET /extension inconnue -> 404")
    for route in ("/manifeste", "/verifie", "/fabrique"):
        verifie(s.requete("POST", route, {"nom": "absente", "name": "x", "version": "1", "description": "", "min_tasmota": "1"})[0], 404, f"{route} extension inconnue -> 404")
    verifie(arbre(racine), avant, "noms hostiles : rien d'ecrit")
    verifie(any(Path(racine).parent.glob("x*")), False, "noms hostiles : rien a cote du depot")
    verifie(len("/.extensions/" + "x" * 31 + ".tapp"), 49, "nom de 31 caracteres : le chemin de la carte fait exactement 49 caracteres")
    verifie(s.requete("POST", "/creer", {"nom": "y" * 31, "gabarit": "A"})[0], 200, "nom de 31 caracteres accepte")
    shutil.rmtree(Path(racine) / "data" / "extensions")


def creation(s, racine):
    base = Path(racine) / "data" / "extensions"
    st, r = s.requete("POST", "/creer", {"nom": "ext_a", "gabarit": "A"})
    verifie(st, 200, "creer ext_a depuis le gabarit A")
    for f, texte in ts.GABARITS["A"]["fichiers"].items():
        verifie((base / "ext_a" / f).read_bytes(), texte.encode("utf-8"), f"creer : {f} copie tel quel, sans CRLF")
    verifie(s.requete("POST", "/creer", {"nom": "ext-b", "gabarit": "B"})[0], 200, "creer ext-b depuis le gabarit B")
    verifie(s.requete("POST", "/creer", {"nom": "x", "gabarit": "Z"})[0], 400, "creer : gabarit inconnu -> 400")
    verifie((base / "x").exists(), False, "creer : gabarit inconnu, pas de dossier")
    (base / "ext_a" / "autoexec.be").write_text("# mon travail\n", encoding="utf-8")
    st, msg = s.requete("POST", "/creer", {"nom": "ext_a", "gabarit": "B"})
    verifie((st, "existe" in str(msg)), (409, True), "creer sur un dossier existant : refus")
    verifie(((base / "ext_a" / "autoexec.be").read_text(encoding="utf-8"), (base / "ext_a" / "mon_ext.be").exists()), ("# mon travail\n", False), "creer sur un dossier existant : rien d'ecrase")
    verifie(s.requete("POST", "/creer", {"nom": "EXT_A", "gabarit": "A"})[0], 409, "creer : meme nom a la casse pres -> refus (Windows)")
    (base / "ext_a" / "autoexec.be").write_text(ts.GABARITS["A"]["fichiers"]["autoexec.be"], encoding="utf-8", newline="")
    (base / "orphelin.tapp").write_bytes(b"ancien")
    verifie((s.requete("POST", "/creer", {"nom": "orphelin", "gabarit": "A"})[0], (base / "orphelin").exists()), (409, False), "creer : un .tapp de meme nom existe -> refus, il serait ecrase a la fabrication")
    (base / "orphelin.tapp").unlink()
    (base / "mon dossier").mkdir()
    st, r = s.requete("GET", "/extensions")
    verifie(([x["nom"] for x in r["extensions"]], r["ignores"]), (["ext-b", "ext_a"], ["mon dossier"]), "liste : les extensions, et le dossier au nom refuse signale")
    (base / "mon dossier").rmdir()
    st, r = s.requete("GET", "/extension?nom=ext-b")
    verifie((st, r["chemin"], [f["nom"] for f in r["fichiers"]], r["manifeste"]["name"], r["tapp"]["existe"], r["destination"]),
            (200, "data/extensions/ext-b", ["autoexec.be", "manifest.json", "mon_ext.be"], "Mon extension", False, "/.extensions/ext-b.tapp"), "GET /extension : chemin, fichiers, manifeste, destination")
    for route, corps in (("/supprimer", {"nom": "ext_a"}), ("/efface", {"nom": "ext_a"})):
        verifie(s.requete("POST", route, corps)[0], 404, f"pas de route de suppression : {route}")
    verifie(s.requete("DELETE", "/extension?nom=ext_a")[0], 501, "pas de DELETE")
    verifie((base / "ext_a").is_dir(), True, "la source reste")


def jonction(s, racine):
    """Un dossier de data/extensions qui pointe ailleurs (jonction posee a la main) : refuse, rien de lu ni d'ecrit dehors."""
    base = Path(racine) / "data" / "extensions"
    with tempfile.TemporaryDirectory() as dehors:
        (Path(dehors) / "secret.be").write_text("x", encoding="utf-8")
        lien = base / "dehors"
        p = subprocess.run(["cmd", "/c", "mklink", "/J", str(lien), dehors], capture_output=True)
        if p.returncode:
            print("OK   jonction : impossible a creer ici, cas saute")
            return
        try:
            verifie(s.requete("GET", "/extension?nom=dehors")[0], 400, "jonction vers l'exterieur : lecture refusee")
            verifie(s.requete("POST", "/fabrique", {"nom": "dehors"})[0], 400, "jonction vers l'exterieur : fabrication refusee")
        finally:
            os.rmdir(lien)                                   # enleve le lien, jamais sa cible


def manifeste(s, racine):
    chemin = Path(racine) / "data" / "extensions" / "ext_a" / "manifest.json"
    d = json.loads(chemin.read_text(encoding="utf-8"))
    d["cle_a_moi"] = {"garde": [1, 2]}
    chemin.write_text(json.dumps(d), encoding="utf-8")
    bon = {"nom": "ext_a", "name": "Mon nom é", "version": "0x1B0B0701", "description": "Une description", "min_tasmota": "0x0F010001"}
    verifie(s.requete("POST", "/manifeste", bon)[0], 200, "manifeste : ecriture acceptee")
    m = json.loads(chemin.read_text(encoding="utf-8"))
    verifie((m["name"], m["version"], m["description"], m["min_tasmota"], m.get("cle_a_moi")),
            ("Mon nom é", "0x1B0B0701", "Une description", "0x0F010001", {"garde": [1, 2]}), "manifeste : 4 champs ecrits, cle inconnue conservee")
    verifie("nom" in m, False, "manifeste : le nom du dossier n'entre pas dans le fichier")
    verifie(sorted(p.name for p in chemin.parent.iterdir()), ["autoexec.be", "manifest.json"], "manifeste : aucun temporaire dans la source")
    verifie([p.name for p in chemin.parents[1].glob("*.tmp")], [], "manifeste : aucun temporaire a cote")
    avant = chemin.read_bytes()
    for cle, valeur in (("name", ""), ("name", "   "), ("name", None), ("name", 5), ("version", "abc"), ("version", ""), ("version", True), ("version", None),
                        ("min_tasmota", "0xZZ"), ("min_tasmota", ["1"]), ("description", 5), ("description", None)):
        st, msg = s.requete("POST", "/manifeste", dict(bon, **{cle: valeur}))
        verifie((st, chemin.read_bytes() == avant), (400, True), f"manifeste : {cle}={valeur!r} refuse, fichier intact")
    st, msg = s.requete("POST", "/manifeste", dict(bon, version="abc"))
    verifie("version" in str(msg), True, "manifeste : le refus nomme le champ (controle de gen_tapp)")
    chemin.write_text("{pas du json", encoding="utf-8")
    st, msg = s.requete("POST", "/manifeste", bon)
    verifie((st, chemin.read_text(encoding="utf-8"), "VS Code" in str(msg)), (400, "{pas du json", True), "manifeste illisible : refus, jamais ecrase, dit quoi faire")
    st, r = s.requete("GET", "/extension?nom=ext_a")
    verifie((st, bool(r["manifeste_erreur"])), (200, True), "manifeste illisible : la fiche le dit")
    chemin.unlink()
    verifie((s.requete("POST", "/manifeste", bon)[0], chemin.is_file()), (200, True), "manifeste absent : recree par le formulaire")
    chemin.write_bytes(avant)


def controle(s, racine):
    d = Path(racine) / "data" / "extensions" / "ext_a"
    tapp = d.parent / "ext_a.tapp"
    st, r = s.requete("POST", "/verifie", {"nom": "ext_a"})
    verifie((st, r["bon"], [p["motif"] for p in r["points"]], len(r["points"])), (200, True, [None] * 4, 4), "verifie : 4 points bons")
    verifie(tapp.exists(), False, "verifie : ne fabrique rien")
    be = d / "autoexec.be"
    source = be.read_bytes()
    be.write_text("def f(\n", encoding="utf-8")
    st, r = s.requete("POST", "/verifie", {"nom": "ext_a"})
    verifie((r["bon"], r["points"][3]["motif"] is not None, "compile" in r["points"][3]["motif"]), (False, True, True), "verifie : Berry qui ne compile pas, point Compilation")
    verifie((s.requete("POST", "/fabrique", {"nom": "ext_a"})[0], tapp.exists()), (400, False), "fabrique : Berry qui ne compile pas -> refus, rien d'ecrit")
    be.unlink()
    st, r = s.requete("POST", "/verifie", {"nom": "ext_a"})
    verifie((r["bon"], "autoexec.be" in r["points"][1]["motif"]), (False, True), "verifie : autoexec.be absent")
    be.write_bytes(source)
    (d / "sous").mkdir()
    st, r = s.requete("POST", "/verifie", {"nom": "ext_a"})
    verifie((r["bon"], "sous" in r["points"][0]["motif"]), (False, True), "verifie : sous-dossier, point Noms")
    st, r = s.requete("GET", "/extension?nom=ext_a")
    verifie(next(f["dossier"] for f in r["fichiers"] if f["nom"] == "sous"), True, "fichiers : le sous-dossier est signale")
    (d / "sous").rmdir()
    m = d / "manifest.json"
    bon = m.read_bytes()
    m.write_text('{"version": "1"}', encoding="utf-8")
    st, r = s.requete("POST", "/verifie", {"nom": "ext_a"})
    verifie((r["bon"], "name" in r["points"][2]["motif"]), (False, True), "verifie : manifeste sans name")
    m.write_bytes(bon)
    (d / "journal.be").write_text('log("sans prefixe")\n', encoding="utf-8")
    st, r = s.requete("POST", "/verifie", {"nom": "ext_a"})
    verifie((r["bon"], bool(r["avertissements"])), (True, True), "verifie : ecart de charte = avertissement rendu en valeur, pas un refus")
    (d / "journal.be").unlink()


def fabrication(s, racine):
    d = Path(racine) / "data" / "extensions" / "ext_a"
    tapp = d.parent / "ext_a.tapp"
    st, r = s.requete("POST", "/fabrique", {"nom": "ext_a"})
    verifie((st, r["tapp"]["existe"], r["tapp"]["a_jour"], r["tapp"]["chemin"]), (200, True, True, "data/extensions/ext_a.tapp"), "fabrique : .tapp a cote du dossier, a jour")
    with zipfile.ZipFile(tapp) as z:
        verifie((sorted(z.namelist()), {i.compress_type for i in z.infolist()}), (["autoexec.be", "manifest.json"], {zipfile.ZIP_STORED}), "fabrique : archive a plat, sans compression")
    ancien = tapp.read_bytes()
    (d / "autoexec.be").write_text("def f(\n", encoding="utf-8")
    verifie((s.requete("POST", "/fabrique", {"nom": "ext_a"})[0], tapp.read_bytes()), (400, ancien), "fabrique refusee : l'ancien .tapp reste")
    (d / "autoexec.be").write_text(ts.GABARITS["A"]["fichiers"]["autoexec.be"], encoding="utf-8", newline="")
    verifie(s.requete("POST", "/fabrique", {"nom": "ext_a"})[0], 200, "fabrique : de nouveau")

    def a_jour():
        return s.requete("GET", "/extension?nom=ext_a")[1]["tapp"]["a_jour"]
    verifie(a_jour(), True, "a jour apres fabrication")
    t = tapp.stat().st_mtime_ns
    os.utime(d / "autoexec.be", ns=(t + 2_000_000_000, t + 2_000_000_000))
    verifie(a_jour(), False, "source modifiee apres le .tapp : perime")
    os.utime(d / "autoexec.be", ns=(t - 2_000_000_000, t - 2_000_000_000))
    verifie(a_jour(), True, "source plus ancienne : a jour")
    os.utime(d, ns=(t + 2_000_000_000, t + 2_000_000_000))
    verifie(a_jour(), False, "dossier modifie apres le .tapp (fichier supprime) : perime")
    verifie(s.requete("POST", "/fabrique", {"nom": "ext_a"})[0], 200, "fabrique : de nouveau")
    os.utime(tapp, ns=(t + 4_000_000_000, t + 4_000_000_000))
    bon = {"nom": "ext_a", "name": "Autre", "version": "1", "description": "", "min_tasmota": "1"}
    s.requete("POST", "/manifeste", bon)
    os.utime(d / "manifest.json", ns=(t + 6_000_000_000, t + 6_000_000_000))
    verifie(a_jour(), False, "manifeste reecrit par la page : le .tapp est perime")
    verifie(s.requete("POST", "/fabrique", {"nom": "ext_a"})[0], 200, "fabrique : apres le manifeste")
    st, r = s.requete("GET", "/extensions")
    verifie(next(x["tapp"]["existe"] for x in r["extensions"] if x["nom"] == "ext_a"), True, "liste : l'etat du .tapp")


def un_seul_a_la_fois(racine):
    """gen_tapp n'est pas reentrant (redirect_stdout, AVERTISSEMENTS, preambule partage) : controle et construction un par un."""
    vraie_c, vraie_f = gen_tapp.controle, gen_tapp.construit
    actifs, maximum, garde = [0], [0], threading.Lock()

    def sonde(vraie):
        def f(*a, **k):
            with garde:
                actifs[0] += 1
                maximum[0] = max(maximum[0], actifs[0])
            time.sleep(0.05)
            try:
                return vraie(*a, **k)
            finally:
                with garde:
                    actifs[0] -= 1
        return f
    gen_tapp.controle, gen_tapp.construit = sonde(vraie_c), sonde(vraie_f)
    sortie = sys.stdout
    try:
        fils = [threading.Thread(target=f, args=(racine, "ext_a")) for f in (ts.verifie, ts.fabrique, ts.verifie, ts.fabrique)]
        for t in fils:
            t.start()
        for t in fils:
            t.join()
    finally:
        gen_tapp.controle, gen_tapp.construit = vraie_c, vraie_f
        sys.stdout = sortie         # sans verrou, deux redirect_stdout croises laissent sys.stdout sur un tampon : tout le banc se tairait
    verifie(maximum[0], 1, "verrou : controle et construction jamais en meme temps")


def surface(s):
    bon = {"nom": "ext_a"}
    verifie(s.requete("POST", "/verifie", bon, {"Content-Type": "application/json"})[0], 403, "POST sans X-Fabrique-Tapp -> 403")
    verifie(s.requete("POST", "/verifie", bon, dict(ENTETES, Origin="http://evil.example"))[0], 403, "POST d'une autre origine -> 403")
    verifie(s.requete("POST", "/verifie", bon, dict(ENTETES, Origin=f"http://127.0.0.1:{s.port}"))[0], 200, "POST meme origine -> 200")
    verifie(s.requete("GET", "/extensions", None, {"Host": "evil.example"})[0], 403, "GET, Host etranger (DNS rebinding) -> 403")
    verifie(s.requete("POST", "/verifie", bon, dict(ENTETES, Host="evil.example"))[0], 403, "POST, Host etranger -> 403")
    verifie(s.requete("GET", "/extensions", None, {"Host": f"localhost:{s.port}"})[0], 200, "GET, Host localhost -> 200")
    verifie(s.requete("POST", "/verifie", b"[1, 2]")[0], 400, "corps non objet -> 400")
    verifie(s.requete("POST", "/verifie", b"{pas du json")[0], 400, "JSON invalide -> 400")
    verifie(s.requete("POST", "/verifie", b"[" * 60000)[0], 400, "JSON trop imbrique -> 400")
    c = http.client.HTTPConnection("127.0.0.1", s.port, timeout=10)
    c.putrequest("POST", "/verifie")
    for cle, valeur in ENTETES.items():
        c.putheader(cle, valeur)
    c.putheader("Content-Length", str(tw.MAX_CORPS + 1))
    c.endheaders()
    verifie(c.getresponse().status, 400, "Content-Length trop grand -> 400")
    c.close()
    # autre appareil du reseau : jeton obligatoire (acces_web)
    vrai = acces_web.est_local
    acces_web.est_local = lambda _: False
    try:
        verifie(s.requete("GET", "/extensions", None, {})[0], 403, "autre appareil sans jeton -> 403")
        st, _, rep = s.brut("GET", f"/?jeton={s.acces.jeton}", None, {})
        verifie((st, f"jeton_{s.port}=" in (rep.getheader("Set-Cookie") or "")), (303, True), "autre appareil, jeton dans l'URL : cookie pose, redirection")
        verifie(s.requete("GET", "/extensions", None, {"Cookie": f"{s.acces.cookie}={s.acces.jeton}"})[0], 200, "autre appareil, cookie : accepte")
        verifie(s.requete("POST", "/verifie", bon, ENTETES)[0], 403, "autre appareil, POST sans jeton -> 403")
    finally:
        acces_web.est_local = vrai


def cartes(s):
    st, r = s.requete("GET", "/cartes")
    verifie((st, taa.ENV in [c["env"] for c in r["cartes"]]), (200, True), "GET /cartes : les cartes du parc")
    verifie(all(sorted(c) == ["env"] for c in r["cartes"]), True, "GET /cartes : le nom de l'env, rien d'autre")


def pas_une_carte(racine):
    """data/extensions/<nom>/ porte un autoexec.be sans etre une carte : essai reel, dossiers presents dans le depot temporaire."""
    import carte_modules_berry as cmb
    anomalies = [a for a in cmb.collecte(str(racine))[2] if "extensions" in a]
    verifie(anomalies, [], "carte_modules_berry : data/extensions n'est pas pris pour une carte")
    import assistant_persist_modele as apm
    verifie([str(x) for x in apm.persists_du_depot(racine) if "extensions" in str(x)], [], "assistant persist : aucune carte vue dans data/extensions")


def secrets_absents():
    secrets = taw.valeurs_reelles()
    verifie(len(secrets) >= 2, True, f"garde-fou : {len(secrets)} valeurs de mot de passe a chercher")
    fuites = sum(1 for v in secrets if any(v in texte for texte in REPONSES))
    verifie(fuites, 0, f"aucun mot de passe du depot dans les {len(REPONSES)} reponses")


def banc():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(tmp) / "donnees")
        racine = taa.depot(tmp)
        shutil.rmtree(racine / "data" / "extensions", ignore_errors=True)
        s = Serveur(racine)
        try:
            for etape in (etat_vide, gabarits, noms_hostiles, creation, jonction, manifeste, controle, fabrication):
                etape(s, racine)
            pas_une_carte(racine)
            un_seul_a_la_fois(racine)
            surface(s)
            cartes(s)
            secrets_absents()
        finally:
            s.ferme()


# (module, nom, ancien, nouveau, libelle du test qui doit passer KO)
MUTANTS = [
    ("tapp_sources.py", "liste blanche retiree", "if not isinstance(nom, str) or not RE_NOM.fullmatch(nom):", "if not isinstance(nom, str):", "creer, nom hostile 'a b' -> 400"),
    ("tapp_sources.py", "noms reserves retires", "if RESERVES.fullmatch(nom):", "if False:", "creer, nom hostile 'CON' -> 400"),
    ("tapp_sources.py", "dossier resolu non controle", "if cible.parent != base:", "if False:", "jonction vers l'exterieur : lecture refusee"),
    ("tapp_sources.py", "ecrasement a la creation", "os.mkdir(d)", "os.makedirs(d, exist_ok=True)", "creer sur un dossier existant : refus"),
    ("tapp_sources.py", "cles inconnues perdues", "nouveau = dict(existant_lu)", "nouveau = {}", "manifeste : 4 champs ecrits, cle inconnue conservee"),
    ("tapp_sources.py", "manifeste illisible ecrase", 'raise ValueError(f"{MANIFESTE} illisible (', 'existant_lu = {}\n                if False:\n                    raise ValueError(f"{MANIFESTE} illisible (', "manifeste illisible : refus, jamais ecrase, dit quoi faire"),
    ("tapp_sources.py", "controle du manifeste retire", "gen_tapp.controle_manifeste(nouveau)", "pass", "manifeste : version='abc' refuse, fichier intact"),
    ("tapp_sources.py", "a_jour sans le dossier", "dates = [d.stat().st_mtime_ns]", "dates = [0]", "dossier modifie apres le .tapp (fichier supprime) : perime"),
    ("tapp_sources.py", "verrou retire", "with VERROU:\n        points, avertissements = gen_tapp.controle", "if True:\n        points, avertissements = gen_tapp.controle", "verrou : controle et construction jamais en meme temps"),
    ("tapp_sources.py", "gabarit A modifie", "# Extension sans .be embarque", "# Extension modifiee", "gabarit A : autoexec.be identique au document"),
    ("tapp_web.py", "anti-CSRF retire", 'self.headers.get("X-Fabrique-Tapp") != "1" or ', "", "POST sans X-Fabrique-Tapp -> 403"),
    ("tapp_web.py", "origine non controlee", ' or not acces.origine_autorisee(self)', "", "POST d'une autre origine -> 403"),
    ("tapp_web.py", "Host non controle", "if not hote_autorise(self, acces.port):", "if False:", "GET, Host etranger (DNS rebinding) -> 403"),
    ("tapp_web.py", "jeton non controle", "if not acces.controle(self):", "if False:", "autre appareil sans jeton -> 403"),
]


def temoins():
    for module, nom, ancien, nouveau, libelle in MUTANTS:
        source = (ICI / module).read_text(encoding="utf-8")
        if not verifie(source.count(ancien), 1, f"mutant {nom} : motif present une fois"):
            continue
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / module).write_text(source.replace(ancien, nouveau), encoding="utf-8")
            p = subprocess.run([sys.executable, str(Path(__file__).resolve())], capture_output=True, text=True, encoding="utf-8",
                               env=dict(os.environ, TAPP_MUTANT=tmp, PYTHONIOENCODING="utf-8"))
        verifie(f"KO   {libelle}" in p.stdout, True, f"temoin rouge : {nom} tue par « {libelle} »")


if __name__ == "__main__":
    banc()
    if not os.environ.get("TAPP_MUTANT") and "--sans-temoin" not in sys.argv:
        temoins()
    print("VERT" if not ECHECS else f"ROUGE : {len(ECHECS)} echec(s)")
    sys.exit(1 if ECHECS else 0)
