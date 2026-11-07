"""Banc de l'exemple d'extension data/extensions/fsMqtt/ (gabarit A de outils_docs/EXTENSIONS_TAPP.md).

UTILISATION
    python outils_docs/scripts_python/berry/banc_tapp_fsmqtt.py [--sans-mutants]
Depuis n'importe quel dossier. Code de sortie 0 = vert : le vrai autoexec.be passe banc_tapp_fsmqtt.be, chaque mutant le
fait echouer, l'archive de gen_tapp.py a la forme attendue, et aucun env n'embarque data/extensions. Ne remplace pas
l'essai sur carte (A10 du plan autoexec-mqtt-tapp) : lecture de l'archive par le firmware, /ext, ordre reel au demarrage.
"""
import argparse
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from banc_coprocesseur import trouve_berry, trouve_racine  # noqa: E402  (meme dossier : module voisin)
import gen_tapp  # noqa: E402  (meme dossier : module voisin)

# (nom, [(texte de l'autoexec.be, remplacement), ...])
MUTANTS = [
    ("chargement sans minuterie", [("tasmota.set_timer(1000, def ()", "(def ()"), ("  end)\nend", "  end)()\nend")]),
    ("niveau lu sans global.", [('!", global.LOG_LEVEL_INFO)', '!", LOG_LEVEL_INFO)')]),
    ("globale creee", [("\ndo\n", "\nvar ext_fsmqtt = 1\ndo\n")]),
    ("minuterie trop courte", [("set_timer(1000", "set_timer(10")]),
    ("echec non rattrape", [("except .. as e, m\n", "except .. as e, m\n      raise e, m\n")]),
    ("module non charge", [("import fsMqtt", "import fsMqttAbsent")]),
]


def lance(berry, racine, extension):
    r = subprocess.run([str(berry), "-g", "-s", str(Path(__file__).with_suffix(".be")), str(extension)], cwd=str(racine),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


def verifie(ok, libelle):
    print(("OK   " if ok else "KO   ") + libelle)
    return ok


def archive_conforme(dossier):
    """Refabrique dans un dossier temporaire : l'archive du depot, ignoree par git, n'existe pas forcement."""
    with tempfile.TemporaryDirectory() as tmp:
        a, b = Path(tmp) / "a.tapp", Path(tmp) / "b.tapp"
        gen_tapp.construit(dossier, sortie=a)
        gen_tapp.construit(dossier, sortie=b)
        with zipfile.ZipFile(a) as z:
            infos = z.infolist()
        noms = sorted(i.filename for i in infos)
        vert = verifie(noms == ["autoexec.be", "manifest.json"], f"archive : a plat, {noms}")
        vert = verifie(all(i.compress_type == zipfile.ZIP_STORED for i in infos), "archive : sans compression") and vert
        return verifie(a.read_bytes() == b.read_bytes(), "archive : deux fabrications identiques octet pour octet") and vert


def main():
    ap = argparse.ArgumentParser(description="Banc de l'exemple d'extension fsMqtt")
    ap.add_argument("--sans-mutants", action="store_true")
    args = ap.parse_args()
    racine = trouve_racine()
    berry = trouve_berry(racine)
    dossier = racine / "data" / "extensions" / "fsMqtt"

    sortie = lance(berry, racine, "data/extensions/fsMqtt")
    print(sortie, end="" if sortie.endswith("\n") else "\n")
    vert = "BANC_TAPP_FSMQTT: OK" in sortie
    vert = archive_conforme(dossier) and vert
    # Une image ne prend que data/fs et le dossier de la carte : une liste du cenv qui citerait l'exemple l'embarquerait
    vert = verifie("data/extensions" not in (racine / "platformio_tasmota_cenv.ini").read_text(encoding="utf-8"),
                   "aucun env du cenv ne cite data/extensions") and vert

    if not args.sans_mutants:
        source = (dossier / "autoexec.be").read_text(encoding="utf-8").replace("\r\n", "\n")
        for nom, remplacements in MUTANTS:
            if any(source.count(avant) != 1 for avant, _ in remplacements):
                vert = verifie(False, f"mutant '{nom}' : texte a muter introuvable (exemple modifie ?)") and vert
                continue
            mute = source
            for avant, apres in remplacements:
                mute = mute.replace(avant, apres)
            with tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "autoexec.be").write_text(mute, encoding="utf-8")
                sortie_m = lance(berry, racine, Path(tmp).as_posix())
            rouge = "BANC_TAPP_FSMQTT: OK" not in sortie_m
            premier = next((l for l in sortie_m.splitlines() if l.startswith("KO")), sortie_m.strip()[-70:])
            vert = verifie(rouge, f"mutant '{nom}' : banc rouge ({premier[:70]})") and vert

    print("\n" + ("VERT" if vert else "ROUGE"))
    return 0 if vert else 1


if __name__ == "__main__":
    sys.exit(main())
