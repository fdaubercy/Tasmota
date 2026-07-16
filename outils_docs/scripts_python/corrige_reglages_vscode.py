r"""
=============================================================================
  corrige_reglages_vscode.py  -  Corrige le PermissionError sur tasmota.ino.cpp
=============================================================================

UTILISATION
-----------
  python corrige_reglages_vscode.py             Applique les reglages.
  python corrige_reglages_vscode.py --verifier  Applique PUIS prouve que ca marche.
  python corrige_reglages_vscode.py --etat      Diagnostic seul, ne modifie rien.

A LANCER UNE FOIS PAR POSTE, apres un clone du depot.

LE SYMPTOME
-----------
Build PlatformIO qui echoue par intermittence sur :

    PermissionError: [Errno 13] Permission denied: '...\tasmota\tasmota.ino.cpp'

LA CAUSE (mesuree le 2026-07-15, pas supposee)
----------------------------------------------
Ni Windows Defender, ni un build concurrent : c'est `cpptools-srv2.exe -i TagParser`,
l'indexeur de l'extension C/C++ de VS Code. PlatformIO ecrit tasmota.ino.cpp (7,6 Mo),
le relit, puis le ROUVRE en ecriture quelques millisecondes plus tard
(pioino.py:104-110) ; l'indexeur s'en saisit entre-temps.

Nomme par le Restart Manager de Windows sur 23 echecs sur 23. Reproduit a 92 % dans
le depot, 0 % hors depot.

LE CORRECTIF
------------
Deux reglages, dans le profil VS Code ACTIF :

    "C_Cpp.files.exclude": { "**/.vscode": true, "**/.vs": true, "**/*.ino.cpp": true },
    "C_Cpp.exclusionPolicy": "checkFilesAndFolders",

LES DEUX sont indispensables. Seul, C_Cpp.files.exclude n'a AUCUN effet : par defaut
(checkFolders) l'extension n'evalue ses exclusions qu'au niveau des dossiers et
"individual files are not checked". Mesure : 8 ouvertures sur 8 malgre l'exclusion,
puis 0 sur 10 une fois exclusionPolicy pose.

POURQUOI PAS .vscode/settings.json DU DEPOT
-------------------------------------------
Il est suivi par git ET existe en amont : toute modification entrerait en conflit a
chaque synchronisation du fork. D'ou le profil, qui ne laisse aucune trace dans git.

CE QUE CE SCRIPT NE FAIT PAS
----------------------------
Il ne parse pas le settings.json : c'est du JSONC (commentaires autorises), qu'aucun
parseur JSON standard n'avale. Il travaille en insertion textuelle et preserve le
fichier au caractere pres. Une sauvegarde horodatee est ecrite avant toute
modification.
=============================================================================
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace", line_buffering=True)

VERT, JAUNE, ROUGE, GRIS, GRAS, RAZ = "", "", "", "", "", ""
if os.name == "nt":
    try:
        k = ctypes.windll.kernel32
        k.SetConsoleMode(k.GetStdHandle(-11), 7)
        VERT, JAUNE, ROUGE = "\033[32m", "\033[33m", "\033[31m"
        GRIS, GRAS, RAZ = "\033[90m", "\033[1m", "\033[0m"
    except Exception:
        pass

MOTIF = "**/*.ino.cpp"
POLICY = "checkFilesAndFolders"

BLOC = '''
// ─── Ajoute par outils_docs/scripts_python/corrige_reglages_vscode.py ───
// Corrige le PermissionError intermittent sur tasmota/tasmota.ino.cpp.
// Cause mesuree : cpptools-srv2.exe -i TagParser (l'indexeur C/C++) ouvre le .cpp
// genere pendant que PlatformIO le reecrit (pioino.py:104-110). Ce n'est ni Defender
// ni un build concurrent : nomme par le Restart Manager sur 23 echecs sur 23.
//
// Les deux premiers motifs sont les valeurs PAR DEFAUT de C_Cpp.files.exclude :
// definir ce reglage les remplace, il faut donc les reconduire.
"C_Cpp.files.exclude": {
    "**/.vscode": true,
    "**/.vs": true,
    "**/*.ino.cpp": true
},
// INDISPENSABLE : sans lui, le motif de FICHIER ci-dessus est purement ignore.
// Par defaut (checkFolders) l'extension n'evalue ses exclusions qu'une fois par
// dossier, "individual files are not checked". Mesure : 8 ouvertures sur 8 malgre
// l'exclusion, puis 0 sur 10 une fois ce reglage pose.
"C_Cpp.exclusionPolicy": "checkFilesAndFolders"
'''.strip("\n")


# ── Localisation du profil VS Code actif ─────────────────────────────────────

def dossier_code() -> Path:
    """Le dossier de configuration de VS Code, selon l'OS."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", "")) / "Code"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "Code"
    else:
        base = Path.home() / ".config" / "Code"
    if not base.is_dir():
        sys.exit(f"{ROUGE}ERREUR : dossier de configuration VS Code introuvable "
                 f"({base}). VS Code est-il installe ?{RAZ}")
    return base


def profil_actif(code: Path) -> tuple[Path, str]:
    """Retourne (settings.json a modifier, nom du profil).

    Piege : avec un profil actif, User/settings.json n'est PLUS le fichier applique.
    L'ecrire n'aurait aucun effet — erreur commise le 2026-07-15.
    """
    defaut = code / "User" / "settings.json"
    storage = code / "User" / "globalStorage" / "storage.json"
    if not storage.is_file():
        return defaut, "Default"

    try:
        profils = json.loads(storage.read_text(encoding="utf-8")).get("userDataProfiles", [])
    except (json.JSONDecodeError, OSError):
        return defaut, "Default"

    # Profils reels : on ecarte les profils integres (builtin/...).
    reels = [p for p in profils
             if p.get("location") and not str(p["location"]).startswith("builtin")]
    if not reels:
        return defaut, "Default"

    # Le profil que VS Code ouvre par defaut, s'il est nomme.
    voulu = None
    if defaut.is_file():
        m = re.search(r'"window\.newWindowProfile"\s*:\s*"([^"]+)"',
                      defaut.read_text(encoding="utf-8", errors="replace"))
        if m:
            voulu = m.group(1)

    choisi = next((p for p in reels if p.get("name") == voulu), None) if voulu else None
    if choisi is None:
        if len(reels) == 1:
            choisi = reels[0]
        else:
            print(f"{JAUNE}[!] Plusieurs profils VS Code et aucun designe par "
                  f"window.newWindowProfile :{RAZ}")
            for p in reels:
                print(f"      - {p.get('name')}  ({p.get('location')})")
            sys.exit(f"{ROUGE}Ambigu : appliquer le correctif a la main, ou definir "
                     f"window.newWindowProfile.{RAZ}")

    return (code / "User" / "profiles" / str(choisi["location"]) / "settings.json",
            str(choisi.get("name", "?")))


# ── Etat des reglages ────────────────────────────────────────────────────────

def etat(texte: str) -> tuple[bool, bool, bool]:
    """(exclude_present, motif_present, policy_ok) — par lecture textuelle.

    On NE parse pas : le fichier est du JSONC, qu'aucun parseur JSON standard
    n'avale. L'insertion textuelle preserve les reglages existants au caractere pres.
    """
    sans_com = re.sub(r"^\s*//.*$", "", texte, flags=re.M)
    return (
        '"C_Cpp.files.exclude"' in sans_com,
        MOTIF in sans_com,
        bool(re.search(r'"C_Cpp\.exclusionPolicy"\s*:\s*"' + POLICY + '"', sans_com)),
    )


def applique(fichier: Path) -> bool:
    """Insere le bloc avant l'accolade finale. True si le fichier a ete modifie."""
    texte = fichier.read_text(encoding="utf-8")
    a_exclude, a_motif, a_policy = etat(texte)

    if a_motif and a_policy:
        print(f"  {VERT}deja en place — rien a faire{RAZ}")
        return False

    if a_exclude and not a_motif:
        print(f"  {ROUGE}C_Cpp.files.exclude existe deja mais SANS {MOTIF}.{RAZ}")
        print("  Je ne fusionne pas a l'aveugle dans un reglage existant.")
        print(f"  A ajouter a la main dans {fichier} :")
        print(f'      "{MOTIF}": true')
        print(f'  et  "C_Cpp.exclusionPolicy": "{POLICY}"')
        return False

    fin = texte.rstrip()
    if not fin.endswith("}"):
        sys.exit(f"{ROUGE}ERREUR : {fichier} ne se termine pas par '}}'. "
                 f"Fichier inattendu, je n'y touche pas.{RAZ}")

    sauv = fichier.with_name(
        fichier.name + ".avant-correctif-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(fichier, sauv)
    print(f"  sauvegarde : {GRIS}{sauv.name}{RAZ}")

    corps = fin[:fin.rfind("}")].rstrip()
    # Virgule de separation, sauf si l'objet est vide.
    if corps.rstrip().endswith(("{", ",")):
        separateur = "\n"
    else:
        separateur = ",\n"
    indente = "\n".join("    " + l if l.strip() else l for l in BLOC.splitlines())
    fichier.write_text(corps + separateur + indente + "\n}\n", encoding="utf-8")

    a_exclude, a_motif, a_policy = etat(fichier.read_text(encoding="utf-8"))
    if not (a_motif and a_policy):
        shutil.copy2(sauv, fichier)
        sys.exit(f"{ROUGE}ERREUR : relecture negative apres ecriture. "
                 f"Fichier restaure depuis la sauvegarde.{RAZ}")
    print(f"  {VERT}applique et relu{RAZ}")
    return True


# ── Sonde : prouver que le reglage AGIT ──────────────────────────────────────

CCH_KEY, CCH_APP, CCH_SVC = 64, 255, 63


class _FT(ctypes.Structure):
    _fields_ = [("l", wt.DWORD), ("h", wt.DWORD)]


class _UP(ctypes.Structure):
    _fields_ = [("pid", wt.DWORD), ("t", _FT)]


class _PI(ctypes.Structure):
    _fields_ = [("Process", _UP), ("app", wt.WCHAR * (CCH_APP + 1)),
                ("svc", wt.WCHAR * (CCH_SVC + 1)), ("type", ctypes.c_uint),
                ("status", wt.ULONG), ("sess", wt.DWORD), ("restart", wt.BOOL)]


def qui_tient(chemin: str) -> list:
    """Processus detenant un handle sur `chemin`, via le Restart Manager."""
    rm = ctypes.WinDLL("RstrtMgr.dll")
    s = wt.DWORD(0)
    cle = (wt.WCHAR * (CCH_KEY + 1))()
    if rm.RmStartSession(ctypes.byref(s), 0, cle) != 0:
        return []
    try:
        f = (wt.LPCWSTR * 1)(chemin)
        if rm.RmRegisterResources(s, 1, f, 0, None, 0, None) != 0:
            return []
        besoin, obtenu, raisons = wt.UINT(0), wt.UINT(0), wt.DWORD(0)
        rm.RmGetList(s, ctypes.byref(besoin), ctypes.byref(obtenu), None,
                     ctypes.byref(raisons))
        if besoin.value == 0:
            return []
        infos = (_PI * besoin.value)()
        obtenu = wt.UINT(besoin.value)
        if rm.RmGetList(s, ctypes.byref(besoin), ctypes.byref(obtenu), infos,
                        ctypes.byref(raisons)) != 0:
            return []
        return [(infos[i].Process.pid, infos[i].app) for i in range(obtenu.value)]
    finally:
        rm.RmEndSession(s)


def verifie(racine: Path, tours: int = 6) -> int:
    """Compare un TEMOIN (.cpp, non exclu) et la CIBLE (.ino.cpp, exclue).

    Les deux sont ecrits dans la MEME boucle : ils subissent donc le meme etat
    d'indexeur. C'est ce qui rend la comparaison valide — mesurer la cible seule
    ne prouve rien, l'activite de l'indexeur variant de 0 a 100 % selon le moment.
    """
    dossier = racine / "tasmota"
    if not dossier.is_dir():
        print(f"{JAUNE}[!] {dossier} introuvable : verification impossible.{RAZ}")
        return 2

    # Nettoyage des residus d'un run precedent. Il faut le faire ICI, au demarrage :
    # a la fin d'un run, l'indexeur TIENT encore le temoin (c'est le phenomene meme
    # qu'on mesure) et la suppression echoue. Le temps qu'on revienne, il a lache.
    # Ces noms sont gitignores (`tasmota/zzz_verif_*`) : un residu ne salit rien.
    for vieux in dossier.glob("zzz_verif_*"):
        try:
            vieux.unlink()
        except OSError:
            pass

    temoin = dossier / "zzz_verif_temoin.cpp"
    cible = dossier / "zzz_verif_cible.ino.cpp"
    charge = ('# 1 "x.ino"\nstatic void Foo(void) { int x = 42; }\n' * 200) * 900

    def essai(p: Path):
        try:
            p.unlink()
        except OSError:
            pass
        time.sleep(0.2)
        subprocess.run([sys.executable, "-c",
                        "import io,sys;io.open(sys.argv[1],'w',encoding='utf-8')"
                        ".write(open(sys.argv[2],encoding='utf-8').read())",
                        str(p), str(tmp)], capture_output=True)
        for _ in range(20):
            d = qui_tient(str(p))
            if d:
                return d
            time.sleep(0.1)
        return None

    tmp = dossier / "zzz_verif_charge.txt"
    tmp.write_text(charge, encoding="utf-8")
    vu_temoin = vu_cible = 0
    try:
        print(f"  {GRIS}temoin = .cpp ordinaire (doit etre indexe){RAZ}")
        print(f"  {GRIS}cible  = .ino.cpp (ne doit PAS l'etre){RAZ}\n")
        for t in range(1, tours + 1):
            dt, dc = essai(temoin), essai(cible)
            vu_temoin += bool(dt)
            vu_cible += bool(dc)
            print(f"    tour {t} | temoin: {'OUVERT' if dt else '-':<7}"
                  f" | cible: {'OUVERT' if dc else '-'}")
    finally:
        # On tente, sans s'acharner : l'indexeur tient encore le temoin, c'est
        # justement ce qu'on vient de mesurer. Le residu est gitignore, et le
        # prochain run le balaiera au demarrage.
        for p in (temoin, cible, tmp):
            for _ in range(6):
                if not p.exists():
                    break
                try:
                    p.unlink()
                    break
                except OSError:
                    time.sleep(0.5)

    print(f"\n  temoin ouvert : {vu_temoin}/{tours}   cible ouverte : {vu_cible}/{tours}")
    if vu_temoin == 0:
        print(f"  {JAUNE}NON CONCLUANT : l'indexeur dort — meme le temoin n'est pas "
              f"ouvert. Relancer plus tard, ou ouvrir le depot dans VS Code.{RAZ}")
        return 2
    if vu_cible == 0:
        print(f"  {VERT}{GRAS}CONCLUANT : l'indexeur travaille (temoin ouvert) et "
              f"ignore les .ino.cpp. Le correctif agit.{RAZ}")
        return 0
    print(f"  {ROUGE}{GRAS}LE CORRECTIF N'AGIT PAS : la cible est encore ouverte.{RAZ}")
    return 1


# ── Programme principal ──────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--verifier", action="store_true")
    p.add_argument("--etat", action="store_true")
    p.add_argument("-h", "--help", action="store_true")
    a = p.parse_args()
    if a.help:
        print(__doc__)
        return 0

    if os.name != "nt":
        print(f"{JAUNE}[!] Ce correctif vise Windows. Sur un autre OS, le "
              f"PermissionError n'existe pas.{RAZ}")

    racine = Path(__file__).resolve().parent
    while racine != racine.parent and not (racine / ".git").exists():
        racine = racine.parent

    code = dossier_code()
    fichier, nom = profil_actif(code)
    print(f"\n{GRAS}Profil VS Code actif : {nom}{RAZ}")
    print(f"{GRIS}  {fichier}{RAZ}\n")

    if not fichier.is_file():
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_text("{\n}\n", encoding="utf-8")
        print(f"  {GRIS}(settings.json cree, il n'existait pas){RAZ}")

    e, m, pol = etat(fichier.read_text(encoding="utf-8"))
    print(f"  C_Cpp.files.exclude       : {'present' if e else 'absent'}")
    print(f"  motif {MOTIF:<18}: {VERT + 'present' + RAZ if m else JAUNE + 'ABSENT' + RAZ}")
    print(f"  exclusionPolicy = {POLICY} : "
          f"{VERT + 'oui' + RAZ if pol else JAUNE + 'NON — le motif serait ignore' + RAZ}")

    if a.etat:
        print(f"\n{GRIS}--etat : rien n'a ete modifie.{RAZ}")
        return 0 if (m and pol) else 1

    print()
    applique(fichier)

    if a.verifier:
        print(f"\n{GRAS}Verification (l'indexeur ouvre-t-il encore les .ino.cpp ?){RAZ}\n")
        return verifie(racine)

    print(f"\n{GRIS}Prise en compte a chaud, sans redemarrer VS Code.{RAZ}")
    print(f"{GRIS}Pour prouver que ca agit : relancer avec --verifier{RAZ}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
