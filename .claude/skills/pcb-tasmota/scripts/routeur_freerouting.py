"""Routage par Freerouting, en option de routeur_grille (meme API).

Usage normal : Routeur(..., moteur="freerouting") ou variable PCB_ROUTEUR=freerouting ;
`route_tout` passe alors ici, le reste (route_net GND, coutures) est inchange.

Chaine (verifiee hors IHM, KiCad 10.0.3, 2026-10-12) :
  pcbnew.ExportSpecctraDSN(board, dsn)  -> reecriture du DSN (largeur par net, via,
  isolement, lisere de bord) -> java -jar freerouting (sans IHM) -> pcbnew.ImportSpecctraSES.
Les nets absents de la liste (la masse) sont RETIRES du DSN par defaut (`autres=None`) :
leurs pastilles restent des obstacles, et la masse suit le flux habituel (route_net
"GND" a la grille, plans, coutures). `autres=0.5` les fait router par Freerouting.
Un net que Freerouting laisse incomplet est arrache et repris par la grille.
Le DRC de kicad-cli reste juge. Mesure sur la carte cuve (2026-10-12) : 33/33 et DRC 0,
mais 1 a 2,5 min (JVM + routage + optimisation), donc PAS plus rapide que la grille
sur une porteuse : a reserver aux cartes que la grille ne finit pas.

Outils HORS depot, dans %LOCALAPPDATA%\\pcb-tasmota\\outils\\ (ou $PCB_OUTILS) :
  jdk-25.0.4.1+1-jre\\bin\\java.exe       Temurin JRE 25 (le jar 2.5.0 exige Java 25)
  freerouting-2.5.0\\freerouting-2.5.0.jar
  python routeur_freerouting.py --verifier   etat des outils
  python routeur_freerouting.py --installer  telecharge et verifie (SHA-256) ; jamais implicite
PIEGES : le binaire natif freerouting-cli-2.5.0-windows-x64 (sans Java) plante (GraalVM,
UnsupportedFeatureError) puis reste bloque sans rendre la main : ne pas l'utiliser.
Le jar 2.5.0 refuse Java 21 (UnsupportedClassVersionError, class file 69 = Java 25).
`-da` coupe l'envoi de statistiques d'usage (actif par defaut chez Freerouting).
"""
import hashlib
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

OUTILS = Path(os.environ.get("PCB_OUTILS") or Path(os.environ.get("LOCALAPPDATA", Path.home())) / "pcb-tasmota" / "outils")
JRE = "jdk-25.0.4.1+1-jre"
JAR = Path("freerouting-2.5.0") / "freerouting-2.5.0.jar"
PAQUETS = [  # (url, sha256 publie, destination relative, archive zip ?)
    ("https://github.com/adoptium/temurin25-binaries/releases/download/jdk-25.0.4.1%2B1/"
     "OpenJDK25U-jre_x64_windows_hotspot_25.0.4.1_1.zip",
     "4c95451cea98556def2c54f7782933f52a26d4a36bd85e1d59f0364464828b07", Path(JRE), True),
    ("https://github.com/freerouting/freerouting/releases/download/v2.5.0/freerouting-2.5.0.jar",
     "f6f51bb02245e8e717f9359bd260cc9c5c0b1bc0acc8b7cb2cd5b8ffeb5de3c7", JAR, False),
]
AIDE = (f"Freerouting absent. Installer (110 Mo environ, hors depot, dans {OUTILS}) :\n"
        f'  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" {Path(__file__).name} --installer\n'
        "ou rester sur le routeur a grille (moteur par defaut).")


# ------------------------------------------------------------------ outils
def outils():
    """(java, jar) ; FileNotFoundError avec la marche a suivre s'ils manquent."""
    java, jar = OUTILS / JRE / "bin" / "java.exe", OUTILS / JAR
    if not (java.is_file() and jar.is_file()):
        raise FileNotFoundError(AIDE)
    return java, jar


def _sha256(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def installe(journal=print):
    """Telecharge le JRE et le jar, verifie les SHA-256 publies, extrait. Idempotent."""
    depot = OUTILS / "telechargements"
    depot.mkdir(parents=True, exist_ok=True)
    for url, sha, dest, archive in PAQUETS:
        if (OUTILS / dest).exists():
            journal(f"deja la : {OUTILS / dest}")
            continue
        fichier = depot / url.rsplit("/", 1)[1]
        if not fichier.is_file() or _sha256(fichier) != sha:
            journal(f"telechargement : {url}")
            urllib.request.urlretrieve(url, fichier)
        if _sha256(fichier) != sha:
            fichier.unlink()
            raise RuntimeError(f"SHA-256 faux pour {fichier.name} : fichier supprime, rien installe")
        if archive:
            with zipfile.ZipFile(fichier) as z:
                for nom in z.namelist():                      # pas de chemin hors du dossier
                    if nom.startswith(("/", "\\")) or ".." in Path(nom).parts:
                        raise RuntimeError(f"archive suspecte : {nom}")
                z.extractall(OUTILS)
        else:
            (OUTILS / dest).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fichier, OUTILS / dest)
        journal(f"installe : {OUTILS / dest} (SHA-256 verifie)")


# ------------------------------------------------------------------ DSN
def _fin(texte, i):
    """Indice juste apres la parenthese fermant celle ouverte en i (guillemets respectes)."""
    prof, guil = 0, False
    for j in range(i, len(texte)):
        ch = texte[j]
        if ch == '"':
            guil = not guil
        elif not guil and ch == "(":
            prof += 1
        elif not guil and ch == ")":
            prof -= 1
            if prof == 0:
                return j + 1
    raise ValueError("DSN mal forme : parenthese non fermee")


def _bloc(texte, motif, depuis=0):
    """(debut, fin) du premier bloc `(motif ...` a partir de `depuis`."""
    m = re.compile(r"\(" + motif + r"[\s)]").search(texte, depuis)
    if not m:
        raise ValueError(f"DSN : bloc ({motif} introuvable")
    return m.start(), _fin(texte, m.start())


def _lisere(chemin_bord, b, couches):
    """Bandes interdites de largeur b (um) le long du contour, cote interieur."""
    pts = list(zip(chemin_bord[0::2], chemin_bord[1::2]))
    aire = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))
    sens = 1 if aire > 0 else -1                       # normale interieure = sens * (-dy, dx)
    polys = []
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        L = math.hypot(x2 - x1, y2 - y1)
        if L < 1e-6:
            continue
        nx, ny = -sens * (y2 - y1) / L * b, sens * (x2 - x1) / L * b
        polys.append([(x1, y1), (x2, y2), (x2 + nx, y2 + ny), (x1 + nx, y1 + ny)])
    for x, y in pts:                                   # carres aux sommets : pas de trou
        polys.append([(x - b, y - b), (x + b, y - b), (x + b, y + b), (x - b, y + b)])
    return "".join(f'    (keepout "" (polygon {c} 0 ' + " ".join(f"{u:.1f} {v:.1f}" for u, v in p + p[:1])
                   + "))\n" for p in polys for c in couches)


def prepare_dsn(texte, largeurs, iso=0.25, via=(0.8, 0.4), bord=0.6, ignores=()):
    """Reecrit le DSN exporte par KiCad. largeurs : {nom de net DSN : largeur mm}."""
    if "(unit um)" not in texte:
        raise ValueError("DSN : unite attendue um (format KiCad 10)")
    um = lambda mm: f"{mm * 1000:.0f}"                                   # noqa: E731
    nom_via = f"Via[0-1]_{um(via[0])}:{um(via[1])}_um"
    d, f = _bloc(texte, "structure")
    struct = texte[d:f]
    couches = re.findall(r"\(layer (\S+)\s*\(type signal\)", struct)
    bord_pts = [float(v) for v in re.search(r"\(boundary\s*\(path pcb [\d.]+\s+([-\d.\s]+)\)", struct)
                .group(1).split()]
    a, b = _bloc(struct, "via")
    struct = struct[:a] + f'(via "{nom_via}")' + struct[b:]
    a, b = _bloc(struct, "rule")
    struct = (struct[:a] + f"(rule (width {um(min(largeurs.values()))}) (clearance {um(iso)}))"
              + struct[b:])
    struct = struct[:-1] + _lisere(bord_pts, bord * 1000, couches) + "  )"
    texte = texte[:d] + struct + texte[f:]
    d, f = _bloc(texte, "library")
    pile = (f'    (padstack "{nom_via}"\n' + "".join(f"      (shape (circle {c} {um(via[0])}))\n" for c in couches)
            + "      (attach off)\n    )\n  )")
    texte = texte[:d] + texte[d:f][:-1] + pile + texte[f:]
    d, f = _bloc(texte, "network")
    reseau = texte[d:f]
    while "(class " in reseau:                          # classes KiCad remplacees par les notres
        a, b = _bloc(reseau, "class")
        reseau = reseau[:a] + reseau[b:]
    classes = {}
    for n, w in largeurs.items():
        classes.setdefault(w, []).append(n)
    q = lambda n: '"' + n.replace('"', "") + '"'       # noqa: E731
    ajout = "".join(f'    (class "fr_{um(w)}" {" ".join(q(n) for n in nets)}\n'
                    f'      (circuit (use_via "{nom_via}"))\n'
                    f"      (rule (width {um(w)}) (clearance {um(iso)})))\n"
                    for w, nets in sorted(classes.items()))
    for n in ignores:                                   # net retire : ses pastilles restent
        m = re.search(r"\(net (" + re.escape(n) + "|" + re.escape(q(n)) + r")[\s)]", reseau)
        if m:                                           # des obstacles, sans net
            reseau = reseau[:m.start()] + reseau[_fin(reseau, m.start()):]
    reseau =reseau.rstrip()[:-1].rstrip() + "\n" + ajout + "  )"
    return texte[:d] + reseau + texte[f:]


# ------------------------------------------------------------------ routage
def route_freerouting(routeur, nets, autres=None, iso=None, passes=50, delai_s=600, optimise=True,
                      dossier=None, journal=print):
    """Route `nets` [(nom, largeur_mm)] par Freerouting ; rend la liste des echecs."""
    import pcbnew
    java, jar = outils()
    board = routeur.board
    routeur._arrache()                       # ImportSpecctraSES remplace toutes les pistes
    dossier = Path(dossier or tempfile.mkdtemp(prefix="freerouting_"))
    dossier.mkdir(parents=True, exist_ok=True)
    dsn, ses, log = dossier / "carte.dsn", dossier / "carte.ses", dossier / "freerouting.log"
    ses.unlink(missing_ok=True)
    if not pcbnew.ExportSpecctraDSN(board, str(dsn)):
        raise RuntimeError("ExportSpecctraDSN a echoue")
    voulu = dict(nets)
    larg, ignores, a_router = {}, [], []
    for nom, ni in routeur.c.nets.items():
        code = ni.GetNetCode()
        if sum(1 for o in routeur.obst_pads if o[2] == code) < 2:
            continue
        w = voulu.get(nom, autres)
        if w is None:
            ignores.append(ni.GetNetname())
        else:
            larg[ni.GetNetname()] = w
            a_router.append((nom, w))
    dsn.write_text(prepare_dsn(dsn.read_text(encoding="utf-8"), larg, iso or routeur.iso,
                               (routeur.via_d, routeur.via_p), routeur.bord, ignores), encoding="utf-8")
    cmd = [str(java), "-Djava.awt.headless=true", "-jar", str(jar), "-de", str(dsn), "-do", str(ses),
           "-da", "--gui.enabled=false", f"--router.autorouter.max_passes={passes}",
           "--router.automatic_neckdown=false", f"--router.optimizer.enabled={str(optimise).lower()}",
           f"--router.job_timeout={delai_s // 3600:02d}:{delai_s // 60 % 60:02d}:{delai_s % 60:02d}"]
    t0 = time.perf_counter()
    with open(log, "w", encoding="utf-8", errors="replace") as sortie:
        try:
            rc = subprocess.run(cmd, stdout=sortie, stderr=subprocess.STDOUT, cwd=dossier,
                                timeout=delai_s + 120).returncode
        except subprocess.TimeoutExpired:
            rc = "delai depasse"
    if rc != 0 or not ses.is_file():
        raise RuntimeError(f"Freerouting : code {rc}, pas de .ses ; journal : {log}")
    if not pcbnew.ImportSpecctraSES(board, str(ses)):
        raise RuntimeError(f"ImportSpecctraSES a echoue sur {ses}")
    journal(f"Freerouting : {time.perf_counter() - t0:.0f} s, {len(a_router)} nets ; fichiers : {dossier}")
    routeur.adopte_pistes(list(board.GetTracks()))
    board.BuildConnectivity()
    conn = board.GetConnectivity()
    for nom, w in a_router:
        routeur.deja[nom] = _complet(routeur, conn, nom)
    for nom, w in a_router:                  # filet : la grille reprend un net incomplet
        if not routeur.deja[nom]:
            del routeur.deja[nom]
            routeur.retire_net(nom)            # pas de demi-arbre Freerouting en double
            routeur.deja[nom] =routeur.route_net(nom, w)
            journal(f"{nom} : incomplet apres Freerouting, grille -> {'ok' if routeur.deja[nom] else 'echec'}")
    echecs = [n for n, _ in nets if not routeur.deja.get(n, True)]
    journal(f"Freerouting : {len(nets) - len(echecs)}/{len(nets)} nets routes"
            + (f", echecs : {', '.join(echecs)}" if echecs else ""))
    return echecs


def _complet(routeur, conn, nom):
    code = routeur.c.nets[nom].GetNetCode()
    pads = [o[3] for o in routeur.obst_pads if o[2] == code]
    # GetConnectedItems = tout l'ilot, pastille comprise ; GetConnectedPads = voisins directs seuls
    lies = {i.m_Uuid.AsString() for i in conn.GetConnectedItems(pads[0]) if i.GetClass() == "PAD"}
    return all(p.m_Uuid.AsString() in lies for p in pads)


if __name__ == "__main__":
    if "--installer" in sys.argv:
        installe()
    try:
        j, r = outils()
        print(f"java : {j}\njar  : {r}")
        print(subprocess.run([str(j), "-version"], capture_output=True, text=True).stderr.splitlines()[0])
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)
