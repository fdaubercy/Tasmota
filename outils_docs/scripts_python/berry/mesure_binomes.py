r"""Taille d'un binome Berry (driver + module) en .be, en .bec et solidifie, ecrite en commentaire GENERE.

UTILISATION
-----------
  python mesure_binomes.py --ecrire   data/fs/controleXxx.be data/fs/xxxFonctions.be [autres modules...]
  python mesure_binomes.py --verifier data/fs/controleXxx.be data/fs/xxxFonctions.be [autres modules...]

  1er fichier = le DRIVER : il recoit le bloc « TAILLE DU BINOME » en tete. Les suivants = ses modules : ils recoivent
  une ligne qui renvoie au driver. Un fichier seul (driver sans module, module sans driver) porte son propre bloc.
  Un fichier sans directive '#@ solidify:' est marque « non solid. ». --verifier ne modifie rien : code 1 si un bloc ou une ligne manque ou est perime.
  A lancer avant un commit qui touche un de ces fichiers (plan tasks/plans/binomes-berry.md, A2).

CE QUI EST MESURE (sur le texte SANS le bloc et la ligne generes)
------------------------------------------------------------------
  .be       : taille du source, ce qu'occupe le fichier sur le LittleFS s'il n'est pas solidifie ;
  .bec      : bytecode compile par lib/libesp32/berry/berry.exe (PC, 64 bits) : le .bec de la carte a 0,4 % pres
              (cuveFonctions 20 793 o sur PC, 20 716 sur la carte ; controleCuve 8 124 / 8 108 ; 2026-11-24)
              et de la RAM qu'occupe le code charge ; les globales du framework inconnues du compilateur PC sont
              declarees dans une copie (quelques octets de plus) ;
  solidifie : objet xtensa -Os du .h solidifie (memes etapes que solidifie_et_compile_berry.py), ce qu'occupe le module
              dans la partition app, sans RAM pour le code. Les chaines vont dans la table globale du firmware, en partie
              partagees : seul leur nombre est donne.

Jamais pendant un build : comme solidifie_et_compile_berry.py, ce script vide lib/libesp32/berry_custom/src/embedded
et regenere lib/libesp32/berry/generate (dossiers gitignores, refaits par chaque build).
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

DEBUT = "#- TAILLE DU BINOME"
FIN = "FIN TAILLE DU BINOME -#"
RENVOI = "# TAILLE DU BINOME :"
INTERDITS = ("-#", "#@", 'module("')         # hors marqueur de fin : fermeture du commentaire, directive, regex du solidifieur


# ---------------------------------------------------------------- texte (fonctions pures, banc test_mesure_binomes.py)
def retire_generes(texte: str) -> str:
    """Le texte sans le bloc de taille ni la ligne de renvoi (ce qui est mesure)."""
    lignes, sortie, dans_bloc = texte.splitlines(keepends=True), [], False
    for ligne in lignes:
        if not dans_bloc and ligne.startswith(DEBUT):
            dans_bloc = True
        if dans_bloc:
            if ligne.rstrip().endswith(FIN):
                dans_bloc = False
            continue
        if ligne.startswith(RENVOI):
            continue
        sortie.append(ligne)
    return "".join(sortie)


def avec_entete(texte: str, entete: str) -> str:
    """Pose l'en-tete genere en tete du fichier, a la place de l'ancien ; fin de ligne du fichier conservee."""
    nl = "\r\n" if "\r\n" in texte else "\n"
    return entete.replace("\n", nl) + nl + retire_generes(texte)


def ko(octets: int) -> str:
    return f"{octets / 1024:.1f} Ko".replace(".", ",")


def bloc_driver(mesures: list) -> str:
    """mesures : [(nom, be, bec, solidifie, chaines)], le driver en premier."""
    lignes = [f"{DEBUT} (genere par outils_docs/scripts_python/berry/mesure_binomes.py --ecrire, ne pas editer)",
              f"   {'fichier':32s} {'.be':>9s} {'.bec':>9s} {'solidifie':>10s}"]
    for nom, be, bec, sol, _ in mesures:
        lignes.append(f"   {nom:32s} {ko(be):>9s} {ko(bec):>9s} {ko(sol) if sol is not None else 'non solid.':>10s}")
    tot = [sum(m[i] or 0 for m in mesures) for i in (1, 2, 3, 4)]
    lignes.append(f"   {'total':32s} {ko(tot[0]):>9s} {ko(tot[1]):>9s} {ko(tot[2]):>10s}  + {tot[3]} chaines")
    lignes += ["   .be : LittleFS si non solidifie (hors ce bloc). .bec : LittleFS, et ordre de grandeur de la RAM du code charge",
               "   (berry.exe du PC). solidifie : partition app (objet xtensa -Os), pas de RAM pour le code ; chaines dans la",
               "   table globale du firmware, en partie partagees. RAM reelle : tasmota.gc() sur une carte.",
               FIN]
    return "\n".join(lignes)


def ligne_renvoi(driver: str) -> str:
    return f"{RENVOI} voir le bloc en tete de {driver} (genere par mesure_binomes.py, ne pas editer)"


def controle_interdits(entete: str) -> None:
    corps = entete.replace(FIN, "")
    for s in INTERDITS:
        if s in corps:
            raise ValueError(f"sequence interdite {s!r} dans l'en-tete genere")


LIGNE_MESURE = re.compile(r"^\s+(\S+)\s+([\d,]+) Ko\s+([\d,]+) Ko\s+(non solid\.|[\d,]+ Ko)(?:\s+\+ (\d+) chaines)?\s*$")
LIEN_RENVOI = re.compile(r"voir le bloc en tete de (\S+\.be)")


def lit_taille(chemin_be, _suivi=()):
    """Taille du binome lue dans le bloc genere, SANS rien mesurer : {"fichiers": [{"nom", "be", "bec", "solidifie"}],
    "total": {"be", "bec", "solidifie"}, "chaines": N}, en Ko (les valeurs ecrites dans le bloc, une decimale ;
    "solidifie" vaut None pour « non solid. »). Un module qui porte la ligne de renvoi suit le driver nomme (meme
    dossier). None si le fichier n'a ni bloc ni renvoi, est illisible, ou si le renvoi boucle ou vise un fichier sans bloc."""
    chemin = Path(chemin_be)
    try:
        texte = chemin.read_text(encoding="utf-8")
    except (OSError, ValueError):      # ValueError : UnicodeDecodeError
        return None
    lignes = texte.splitlines()
    renvoi = next((LIEN_RENVOI.search(l) for l in lignes if l.startswith(RENVOI)), None)
    if renvoi:
        cible = chemin.with_name(renvoi.group(1))
        return None if cible in _suivi or cible == chemin else lit_taille(cible, _suivi + (chemin,))
    debut = next((i for i, l in enumerate(lignes) if l.startswith(DEBUT)), None)
    if debut is None:
        return None
    lus, chaines = [], 0
    for ligne in lignes[debut + 1:]:
        if ligne.rstrip().endswith(FIN):
            break
        m = LIGNE_MESURE.match(ligne)
        if m and all(v.count(",") <= 1 for v in m.groups()[1:4]):   # « 1,2,3 » : ligne abimee, ignoree
            nom, be, bec, sol, ch = m.groups()
            lus.append({"nom": nom, "be": float(be.replace(",", ".")), "bec": float(bec.replace(",", ".")),
                        "solidifie": None if sol.startswith("non") else float(sol[:-3].replace(",", "."))})
            chaines = int(ch) if ch else chaines
    total = next((x for x in lus if x["nom"] == "total"), None)
    if total is None:
        return None
    return {"fichiers": [x for x in lus if x["nom"] != "total"],
            "total": {k: total[k] for k in ("be", "bec", "solidifie")}, "chaines": chaines}


def cout_bloc(racine, fichiers):
    """Cout d'un bloc du manifeste (champ `fichiers` de modele_persist.json) : {"be", "bec", "solidifie", "fichiers"}
    en Ko, somme des lignes des blocs TAILLE DU BINOME lus pour ses .be, chaque fichier compte une fois ;
    "solidifie" ne somme que les fichiers solidifiables. None si aucun .be du bloc n'a de bloc de taille."""
    vus = {}
    for f in fichiers:
        if f.endswith(".be"):
            for x in (lit_taille(Path(racine) / f) or {}).get("fichiers", []):
                vus.setdefault(x["nom"], x)
    if not vus:
        return None
    somme = lambda k: round(sum(x[k] or 0 for x in vus.values()), 1)
    return {"be": somme("be"), "bec": somme("bec"), "solidifie": somme("solidifie"), "fichiers": sorted(vus)}


# ---------------------------------------------------------------- mesures (outils du PC)
RACINE = Path(__file__).resolve().parents[3]
BERRY = RACINE / "lib" / "libesp32" / "berry"
CUSTOM = RACINE / "lib" / "libesp32" / "berry_custom"
EMB, SOL = CUSTOM / "src" / "embedded", CUSTOM / "src" / "solidify"


def outils():
    pio = Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".platformio"
    gcc = next((g for motif in ("xtensa-esp-elf-gcc.exe", "xtensa-esp-elf-gcc")
                for g in pio.glob(f"packages/toolchain-xtensa-esp-elf/bin/{motif}")), None)
    py = next((p for p in (pio / "penv" / "Scripts" / "python.exe", pio / "penv" / "bin" / "python") if p.exists()), None)
    bexe = next((p for p in (BERRY / "berry.exe", BERRY / "berry") if p.exists()), None)
    if not (gcc and py and bexe):
        sys.exit("ERREUR : toolchain xtensa, Python de PlatformIO ou berry.exe introuvable (un build doit etre passe une fois).")
    return gcc, gcc.with_name(gcc.name.replace("gcc", "size")), py, bexe


def taille_bec(bexe: Path, nom: str, source: bytes, tmp: Path) -> int:
    copie, sortie, noms = tmp / nom, tmp / (Path(nom).stem + ".bec"), []
    for _ in range(80):
        copie.write_bytes((f"var {', '.join(noms)}\n".encode() if noms else b"") + source)
        r = subprocess.run([str(bexe), "-c", str(copie), "-o", str(sortie)], capture_output=True, text=True)
        if r.returncode == 0 and sortie.exists():
            return sortie.stat().st_size
        m = re.search(r"'(\w+)' undeclared", r.stdout + r.stderr)
        if not m:
            sys.exit(f"ERREUR : {nom} ne compile pas en .bec : {(r.stdout + r.stderr).strip()[-300:]}")
        noms.append(m.group(1))
    sys.exit(f"ERREUR : {nom} : trop de globales inconnues pour le compilateur PC")


def coc(py: Path, env: dict) -> None:
    j = os.path.join   # copie conforme de solidifie_et_compile_berry.py, etape 2
    cmd = [str(py), j("tools", "coc", "coc"), "-o", "generate", "src", "default",
           j("..", "berry_tasmota", "src"), j("..", "berry_matter", "src", "solidify"), j("..", "berry_matter", "src"),
           j("..", "berry_custom", "src", "solidify"), j("..", "berry_custom", "src"),
           j("..", "berry_animation", "src", "solidify"), j("..", "berry_animation", "src"),
           j("..", "berry_tasmota", "src", "solidify"), j("..", "berry_mapping", "src"), j("..", "berry_int64", "src"),
           j("..", "..", "libesp32_lvgl", "lv_binding_berry", "src"),
           j("..", "..", "libesp32_lvgl", "lv_binding_berry", "src", "solidify"),
           j("..", "..", "libesp32_lvgl", "lv_binding_berry", "generate"),
           j("..", "..", "libesp32_lvgl", "lv_haspmota", "src", "solidify"),
           "-c", j("default", "berry_conf.h"), j("..", "..", "..", "tasmota", "tasmota_defines_for_berry.h")]
    r = subprocess.run(cmd, cwd=BERRY, capture_output=True, text=True, env=env)
    if r.returncode:
        raise RuntimeError("coc : " + (r.stdout + r.stderr)[-300:])


def taille_solidifiee(outs, nom: str, source: bytes, tmp: Path):
    gcc, size, py, _ = outs
    env = {**os.environ, "PYTHONPATH": str(BERRY), "PYTHONUTF8": "1"}
    for f in EMB.glob("*.be"):
        f.unlink()
    for h in SOL.glob("solidified_*.h"):
        h.unlink()
    (EMB / nom).write_bytes(source)
    c = CUSTOM / "src" / "_mesure_binome.c"
    try:
        r = subprocess.run([str(py), "-m", "berry_port", "-s", "-g", "solidify_all_python.be"],
                           cwd=CUSTOM, capture_output=True, text=True, env=env)
        h = SOL / f"solidified_{Path(nom).stem}.h"
        if r.returncode or not h.exists():
            raise RuntimeError(f"{nom} ne se solidifie pas : {(r.stdout + r.stderr).strip()[-300:]}")
        chaines = len(set(re.findall(r"be_(?:nested_)?(?:kv_)?str(?:_weak|_long)?\((\w+)\)",
                                     h.read_text(encoding="utf-8", errors="replace"))))
        coc(py, env)
        o = tmp / "_mesure_binome.o"
        c.write_text(f'#include "solidify/{h.name}"\n', encoding="utf-8")
        p = subprocess.run([str(gcc), "-c", "-Os", f"-I{CUSTOM / 'src'}", f"-I{BERRY / 'src'}", f"-I{BERRY / 'default'}",
                            f"-I{BERRY / 'generate'}", f"-I{RACINE / 'tasmota'}", str(c), "-o", str(o)],
                           capture_output=True, text=True, cwd=CUSTOM / "src")
        if p.returncode:
            raise RuntimeError(f"{nom} : le .h solidifie ne compile pas : {p.stderr.strip()[-300:]}")
        s = subprocess.run([str(size), "-A", str(o)], capture_output=True, text=True).stdout
        octets = sum(int(l.split()[1]) for l in s.splitlines() if l.startswith((".rodata", ".data", ".text", ".literal")))
        return octets, chaines
    finally:
        for f in EMB.glob("*.be"):
            f.unlink()
        for hh in SOL.glob("solidified_*.h"):
            try:
                hh.unlink()
            except OSError:
                pass       # cpptools tient parfois le .h fraichement ecrit
        if c.exists():
            c.unlink()


def refuse_si_build() -> None:
    sys.path.insert(0, str(RACINE / ".claude" / "hooks"))
    try:
        import garde_build
        builds = garde_build.builds_en_cours()
    except Exception:                                    # noqa: BLE001 - hook absent ou PowerShell en echec
        builds = None
    if builds:
        sys.exit(f"REFUS : un build PlatformIO est en cours ({', '.join(builds)}) : ce script vide "
                 f"lib/libesp32/berry_custom/src/embedded, dont le build a besoin.")
    if builds is None:
        sys.exit("REFUS : detection des builds impossible ; relancer quand la detection fonctionne.")


def main(argv) -> int:
    if len(argv) < 2 or argv[0] not in ("--ecrire", "--verifier"):
        print(__doc__)
        return 2
    mode, chemins = argv[0], [Path(a) if Path(a).is_absolute() else RACINE / a for a in argv[1:]]
    for p in chemins:
        if not p.is_file() or p.suffix != ".be":
            sys.exit(f"ERREUR : {p} n'est pas un fichier .be")
    refuse_si_build()
    outs = outils()
    textes = {p: p.read_bytes().decode("utf-8") for p in chemins}
    mesures = []
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        for p in chemins:
            source = retire_generes(textes[p]).encode("utf-8")
            # sans directive '#@ solidify:', le module ne peut pas etre solidifie : colonne « non solid. »
            sol, chaines = taille_solidifiee(outs, p.name, source, tmp) if b"#@ solidify:" in source else (None, 0)
            mesures.append((p.name, len(source), taille_bec(outs[3], p.name, source, tmp), sol, chaines))
    driver = chemins[0].name
    attendus = {chemins[0]: bloc_driver(mesures)}
    attendus.update({p: ligne_renvoi(driver) for p in chemins[1:]})
    perimes = []
    for p, entete in attendus.items():
        controle_interdits(entete)
        neuf = avec_entete(textes[p], entete)
        if neuf != textes[p]:
            perimes.append(p)
            if mode == "--ecrire":
                p.write_bytes(neuf.encode("utf-8"))
    print(bloc_driver(mesures))
    for p in perimes:
        print(("ECRIT : " if mode == "--ecrire" else "PERIME : ") + str(p.relative_to(RACINE)))
    if not perimes:
        print("A JOUR : rien a ecrire")
    return 1 if (mode == "--verifier" and perimes) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
