"""Banc de gen_tapp.py : refus, format du firmware, octets reproductibles, atomicite, temoins.

Lancer : PYTHONIOENCODING=utf-8 ~/.platformio/penv/Scripts/python.exe test_gen_tapp.py
Code de sortie 0 = vert. Dossiers temporaires uniquement ; aucun .tapp amont n'est modifie.
"""
import contextlib
import io
import os
import runpy
import shutil
import struct
import sys
import tempfile
import zipfile
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[2]
AMONT = RACINE / "tasmota" / "berry" / "extensions"
MODULE = ICI / "gen_tapp.py"
MANIFEST = '{"name": "Essai", "version": "0x190A0100", "min_tasmota": "0x0F010001"}'
AUTOEXEC = "import tasmota\nprint('essai')\n"


class Resultats:
    def __init__(self, bavard):
        self.ko, self.echecs, self.bavard = 0, [], bavard

    def verifie(self, obtenu, attendu, libelle):
        ok = obtenu == attendu
        if not ok:
            self.ko += 1
            self.echecs.append(libelle)
        if self.bavard:
            print(f"{'OK  ' if ok else 'KO  '} {libelle}" + ("" if ok else f" (obtenu {obtenu!r}, attendu {attendu!r})"))


def charge(chemin):
    sys.path[:0] = [str(ICI)]
    try:
        return runpy.run_path(str(chemin))
    finally:
        del sys.path[0]


def source(tmp, manifest=MANIFEST, autoexec=AUTOEXEC, extra=None):
    d = Path(tmp) / "essai"
    d.mkdir()
    if manifest is not None:
        (d / "manifest.json").write_bytes(manifest.encode("utf-8"))
    if autoexec is not None:
        (d / "autoexec.be").write_bytes(autoexec.encode("utf-8"))
    for nom, txt in (extra or {}).items():
        (d / nom).write_bytes(txt.encode("utf-8"))
    return d


def tente(mod, *args, **kw):
    try:
        return mod["construit"](*args, **kw), None
    except (ValueError, OSError) as e:
        return None, f"{type(e).__name__} {e}"


def entetes(chemin):
    """Relit les en-tetes locaux octet par octet, comme ZipArchive::parse du firmware."""
    b = Path(chemin).read_bytes()
    off, res = 0, []
    while b[off:off + 4] == b"PK\x03\x04":
        _, flags, comp, _, _, _, cs, us, nl, el = struct.unpack("<HHHHHIIIHH", b[off + 4:off + 30])
        nom = b[off + 30:off + 30 + nl].decode("ascii")
        res.append(dict(nom=nom, flags=flags, comp=comp, cs=cs, us=us, nl=nl, el=el))
        off += 30 + nl + el + us
    return res


def ecrit(d, nom, texte):
    (d / nom).write_bytes(texte.encode("utf-8"))


def t_refus(mod, r):
    cas = [
        ("sous-dossier", lambda d: (d / "sous").mkdir(), "sous-dossier interdit"),
        ("autoexec absent", lambda d: (d / "autoexec.be").unlink(), "autoexec.be"),
        ("manifest absent", lambda d: (d / "manifest.json").unlink(), "manifest.json"),
        ("manifest invalide", lambda d: ecrit(d, "manifest.json", "{pas du json"), "manifest.json invalide"),
        ("manifest sans name", lambda d: ecrit(d, "manifest.json", '{"version": 1}'), "'name'"),
        ("name vide", lambda d: ecrit(d, "manifest.json", '{"name": " "}'), "'name'"),
        ("manifest pas un objet", lambda d: ecrit(d, "manifest.json", "[1]"), "objet"),
        ("version illisible", lambda d: ecrit(d, "manifest.json", '{"name": "a", "version": "1.0.2"}'), "'version'"),
        ("min_tasmota booleen", lambda d: ecrit(d, "manifest.json", '{"name": "a", "min_tasmota": true}'), "'min_tasmota'"),
        ("nom trop long", lambda d: ecrit(d, "a" * 62 + ".be", "var a = 1\n"), "65 octets"),
        ("nom non ASCII", lambda d: ecrit(d, "café.be", "var a = 1\n"), "non ASCII"),
        ("Berry ne compile pas", lambda d: ecrit(d, "autoexec.be", "def f(\nprint(1)\n"), "autoexec.be"),
        ("nom du framework nu", lambda d: ecrit(d, "autoexec.be", "def f() return LOG_LEVEL_INFO end\n"), "avant /autoexec.be"),
    ]
    for lib, abime, motif in cas:
        with tempfile.TemporaryDirectory() as tmp:
            d = source(tmp)
            abime(d)
            ancien = Path(tmp) / "essai.tapp"
            ancien.write_bytes(b"ANCIEN")
            chemin, msg = tente(mod, d)
            r.verifie(chemin is None and motif in (msg or ""), True, f"refus : {lib} (motif {msg!r})")
            r.verifie(sorted(os.listdir(tmp)), ["essai", "essai.tapp"], f"refus : {lib} : rien d'ecrit")
            r.verifie(ancien.read_bytes(), b"ANCIEN", f"refus : {lib} : ancien .tapp intact")
    with tempfile.TemporaryDirectory() as tmp:
        d = source(tmp)
        for lib, sortie, motif in (("sortie sans .tapp", Path(tmp) / "x.zip", ".tapp"),
                                   ("sortie dans le dossier", d / "x.tapp", "dans le dossier")):
            chemin, msg = tente(mod, d, sortie)
            r.verifie(chemin is None and motif in (msg or ""), True, f"refus : {lib} (motif {msg!r})")
    chemin, msg = tente(mod, Path(tempfile.gettempdir()) / "gen_tapp_absent_xyz")
    r.verifie("introuvable" in (msg or ""), True, "refus : dossier introuvable")


def t_format(mod, r):
    with tempfile.TemporaryDirectory() as tmp:
        d = source(tmp, extra={"zeta.be": "var z = 1\n", ".cache": "x"})
        chemin, msg = tente(mod, d)
        r.verifie(chemin, Path(tmp).resolve() / "essai.tapp", "format : sortie par defaut a cote du dossier")
        with zipfile.ZipFile(chemin) as z:
            noms, types, auto = z.namelist(), [i.compress_type for i in z.infolist()], z.read("autoexec.be").decode()
        r.verifie(types, [zipfile.ZIP_STORED] * 4, "format : ZIP_STORED partout (zipfile)")
        r.verifie(noms, sorted(noms), "format : noms tries")
        r.verifie(sorted(noms), [".cache", "autoexec.be", "manifest.json", "zeta.be"], "format : tous les fichiers, sans filtre, a plat")
        r.verifie(auto, AUTOEXEC, "format : contenu intact")
        e = entetes(chemin)
        r.verifie(len(e), 4, "firmware : 4 entrees lues en-tete par en-tete")
        r.verifie(all(x["flags"] == 0 for x in e), True, "firmware : drapeaux a 0 (ZipReadFS::parse)")
        r.verifie(all(x["comp"] == 0 for x in e), True, "firmware : compression 0")
        r.verifie(all(x["cs"] == x["us"] for x in e), True, "firmware : taille compressee = taille d'origine")
        r.verifie(all(x["nl"] <= 64 and "/" not in x["nom"] and "#" not in x["nom"] for x in e), True, "firmware : nom <= 64, sans / ni #")
        amont = AMONT / "Wifi_Heap_Sticker.tapp"
        ea = entetes(amont)
        r.verifie(amont.exists() and {x["comp"] for x in ea} == {x["comp"] for x in e}, True, "forme : meme methode que Wifi_Heap_Sticker.tapp (stored)")
        r.verifie({"manifest.json", "autoexec.be"} <= {x["nom"] for x in ea} and all("/" not in x["nom"] for x in ea),
                  True, "forme : l'amont est a plat avec manifest.json et autoexec.be")
        premiers = chemin.read_bytes()
        os.utime(d / "autoexec.be", (1_000_000_000, 1_000_000_000))
        chemin.unlink()
        mod["construit"](d)
        r.verifie(chemin.read_bytes() == premiers, True, "octets : deux constructions donnent les memes octets")
        out = Path(tmp) / "autre.tapp"
        out.write_bytes(b"ANCIEN")
        r.verifie(mod["construit"](d, out).read_bytes() == premiers, True, "sortie explicite : ancien remplace")
        r.verifie(sorted(os.listdir(tmp)), ["autre.tapp", "essai", "essai.tapp"], "sortie : aucun temporaire laisse")
    for lib, man in (("version numerique", '{"name": "a", "version": 7, "min_tasmota": 0}'), ("sans version", '{"name": "a"}')):
        with tempfile.TemporaryDirectory() as tmp:
            r.verifie(tente(mod, source(tmp, manifest=man))[1], None, f"manifest accepte : {lib}")


def t_vrai_cas(mod, r):
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "Wifi_Heap_Sticker"
        shutil.copytree(AMONT / "Wifi_Heap_Sticker", src)
        chemin, msg = tente(mod, src)
        r.verifie(msg, None, "vrai cas : Wifi_Heap_Sticker compile et se construit")
        if chemin:
            with zipfile.ZipFile(chemin) as z, zipfile.ZipFile(AMONT / "Wifi_Heap_Sticker.tapp") as ref:
                lf = lambda b: b.replace(b"\r\n", b"\n")  # le checkout du depot peut etre en CRLF
                r.verifie(sorted(z.namelist()) == sorted(ref.namelist()) and all(z.read(n) == (src / n).read_bytes() for n in ref.namelist()),
                          True, "vrai cas : memes fichiers que l'archive amont, contenus ecrits tels quels")
                r.verifie(all(lf(z.read(n)) == lf(ref.read(n)) for n in ref.namelist()), True,
                          "vrai cas : contenus egaux a l'archive amont (fins de ligne mises a part)")


def t_atomique(mod, r):
    with tempfile.TemporaryDirectory() as tmp:
        d = source(tmp, extra={"b.be": "var b = 1\n"})
        ancien = Path(tmp) / "essai.tapp"
        ancien.write_bytes(b"ANCIEN")
        reel, appels = zipfile.ZipFile.writestr, []

        def casse(self, *a, **k):
            appels.append(1)
            if len(appels) == 2:
                raise OSError("disque plein simule")
            return reel(self, *a, **k)

        zipfile.ZipFile.writestr = casse
        try:
            try:
                mod["construit"](d)
                leve = False
            except OSError:
                leve = True
        finally:
            zipfile.ZipFile.writestr = reel
        r.verifie(leve, True, "atomique : l'erreur d'ecriture remonte")
        r.verifie(ancien.read_bytes() if ancien.exists() else None, b"ANCIEN", "atomique : ancien .tapp intact apres echec en cours d'ecriture")
        r.verifie(sorted(os.listdir(tmp)), ["essai", "essai.tapp"], "atomique : aucun temporaire apres echec")


def t_silence_et_cli(mod, r):
    with tempfile.TemporaryDirectory() as tmp:
        d = source(tmp)
        cwd, sortie = os.getcwd(), io.StringIO()
        with contextlib.redirect_stdout(sortie):
            mod["construit"](d)
        r.verifie((sortie.getvalue(), os.getcwd()), ("", cwd), "construit : rien d'imprime, dossier courant inchange")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = mod["main"]([str(d), "--sortie", str(Path(tmp) / "cli.tapp")])
        r.verifie((rc, "cli.tapp : 2 fichier(s)" in out.getvalue(), err.getvalue()), (0, True, ""), "CLI : succes, une ligne, code 0")
        out, err = io.StringIO(), io.StringIO()
        (d / "autoexec.be").unlink()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = mod["main"]([str(d)])
        r.verifie((rc, "autoexec.be" in err.getvalue(), out.getvalue()), (1, True, ""), "CLI : refus, motif sur stderr, code 1")


TESTS = {"refus": t_refus, "format": t_format, "vrai": t_vrai_cas, "atomique": t_atomique, "cli": t_silence_et_cli}

# (nom, transformation du source, groupes a lancer, prefixe du libelle qui doit passer KO)
MUTANTS = [
    ("ZIP_DEFLATED", lambda s: s.replace("zipfile.ZIP_STORED", "zipfile.ZIP_DEFLATED"), ["format"], "firmware : compression 0"),
    ("verification Berry retiree", lambda s: s.replace("AVERTISSEMENTS[:] = _controle_berry(", "AVERTISSEMENTS[:] = [] and _controle_berry("),
     ["refus"], "refus : Berry ne compile pas"),
    ("noms du framework declares", lambda s: s.replace("sans=GLOBALES_DU_FRAMEWORK", "sans=()"), ["refus"], "refus : nom du framework nu"),
    ("controle du sous-dossier retire", lambda s: s.replace("if (dossier / nom).is_dir():", "if False:"), ["refus"], "refus : sous-dossier"),
    ("ecriture non atomique",
     lambda s: s.replace('fd, tmp = tempfile.mkstemp(suffix=".tmp", prefix=sortie.name, dir=sortie.parent)',
                         "fd = os.open(sortie, os.O_WRONLY | os.O_CREAT | os.O_TRUNC); tmp = str(sortie)"),
     ["atomique"], "atomique : ancien .tapp intact"),
]


def main():
    r = Resultats(True)
    mod = charge(MODULE)
    for f in TESTS.values():
        f(mod, r)
    src = MODULE.read_text(encoding="utf-8")
    for nom, change, groupes, cible in MUTANTS:
        with tempfile.TemporaryDirectory() as tmp:
            texte = change(src)
            applique = texte != src
            (Path(tmp) / "gen_tapp.py").write_text(texte, encoding="utf-8")
            m = Resultats(False)
            if applique:
                mm = charge(Path(tmp) / "gen_tapp.py")
                for g in groupes:
                    TESTS[g](mm, m)
            tue = applique and any(e.startswith(cible) for e in m.echecs)
            r.verifie(tue, True, f"temoin rouge : {nom} tue par '{cible}' ({len(m.echecs)} KO au total)")
    print("VERT" if r.ko == 0 else f"ROUGE : {r.ko} echec(s)")
    return 1 if r.ko else 0


if __name__ == "__main__":
    sys.exit(main())
