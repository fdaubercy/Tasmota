r"""Banc du visuel d'accueil (data/fs/visuelFonctions.be + controleVisuel.be) : partie Berry (banc_visuel.be) et mutants.

UTILISATION
    python outils_docs/scripts_python/berry/banc_visuel.py [--sans-mutants]
Depuis n'importe quel dossier. Code de sortie 0 = vert : le vrai module passe banc_visuel.be ET chaque mutant (copie du
module avec une protection retiree) le fait echouer (temoins negatifs). Ni le serveur web de Tasmota (Referer), ni la RAM,
ni la solidification ne sont testes : un banc vert ne remplace pas l'essai sur une carte.
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from banc_coprocesseur import trouve_berry, trouve_racine  # noqa: E402  (meme dossier : module voisin)

# (nom, fichier, texte a muter, remplacement)
MUTANTS = [
    ("driver pose sans description", "controleVisuel.be", "if (visuelFonctions.charge() != nil)", "if (true)"),
    ("JSON injecte sans echappement", "visuelFonctions.be", 'return string.replace(json.dump(d), "<",', 'return string.replace(json.dump(d), "Z",'),
    ("version non controlee", "visuelFonctions.be", 'if (d.find("version") != 1)', "if (false)"),
    ("chemin de mesure non controle", "visuelFonctions.be", 'if (!ok)    err.push(p + " : source.chemin vide ou invalide")', "if (false)    err.push(p)"),
    ("coordonnee hors du fond acceptee", "visuelFonctions.be", "elif (maxi > 0 && (v < 0 || v > maxi))", "elif (false)"),
    ("etat : tous les blocs toujours construits", "visuelFonctions.be", 'if (types.contains("wifi"))', "if (true)"),
    ("etat : SENSOR entier", "visuelFonctions.be", "dst[ch[i]] = src[ch[i]]", "dst = src"),
    ("reseau sans cache", "visuelFonctions.be", "t - m[\"reseau\"][0] < visuelFonctions.CACHE_RESEAU", "false"),
    ("route sans controle d'acces", "visuelFonctions.be", "if (!webserver.check_privileged_access())    return nil    end", ""),
    ("fond absent sans erreur", "visuelFonctions.be", 'visuelFonctions.log("VISUEL_ERREUR: Fond absent (visuel.svg|webp|jpg) !", LOG_LEVEL_ERREUR)', "visuelFonctions.log('x', LOG_LEVEL_DEBUG)"),
    ("fond sans Cache-Control", "visuelFonctions.be", 'webserver.header("Cache-Control", "max-age=86400")', ""),
    ("fond tronque au premier morceau", "visuelFonctions.be", "webserver.content_send(morceau)\n            tasmota.yield()",
     "webserver.content_send(morceau)\n            break"),
    ("etat journalise en info", "visuelFonctions.be", 'visuelFonctions.log("VISUEL: etat envoye !", LOG_LEVEL_DEBUG_PLUS)', 'visuelFonctions.log("VISUEL: etat envoye !", LOG_LEVEL_INFO)'),
    ("module ModBus absent : exception", "visuelFonctions.be", "    except ..\n        r = {}\n    end", "    except .. as erreur\n        raise erreur\n    end"),
]


def lance(berry, racine, sources):
    r = subprocess.run([str(berry), str(Path(__file__).with_suffix(".be")), str(Path(tempfile.mkdtemp(prefix="banc_visuel_"))), str(sources)],
                       cwd=str(racine), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


def main():
    ap = argparse.ArgumentParser(description="Banc du visuel d'accueil")
    ap.add_argument("--sans-mutants", action="store_true")
    args = ap.parse_args()
    racine = trouve_racine()
    berry = trouve_berry(racine)
    sortie = lance(berry, racine, "data")
    print(sortie, end="" if sortie.endswith("\n") else "\n")
    vert = sortie.strip().splitlines()[-1:] == ["BANC_VISUEL: OK"]
    if not args.sans_mutants:
        for nom, fichier, avant, apres in MUTANTS:
            source = (racine / "data" / "fs" / fichier).read_text(encoding="utf-8").replace("\r\n", "\n")
            if source.count(avant) != 1:
                print(f"KO   mutant '{nom}' : texte a muter introuvable ou repete ({source.count(avant)} fois)")
                vert = False
                continue
            with tempfile.TemporaryDirectory() as tmp:
                fs = Path(tmp) / "fs"
                fs.mkdir()
                for f in (racine / "data" / "fs").glob("*.be"):
                    if f.name in ("visuelFonctions.be", "controleVisuel.be"):
                        (fs / f.name).write_text((racine / "data" / "fs" / f.name).read_text(encoding="utf-8"), encoding="utf-8")
                (fs / fichier).write_text(source.replace(avant, apres), encoding="utf-8")
                (Path(tmp) / "sd").mkdir()
                sortie_m = lance(berry, racine, Path(tmp).as_posix())
            rouge = "BANC_VISUEL: OK" not in sortie_m
            premier = next((l for l in sortie_m.splitlines() if "ECHEC" in l), sortie_m.strip()[-70:])
            print(("OK   " if rouge else "KO   ") + f"mutant '{nom}' : banc rouge ({premier.strip()[:70]})")
            vert = vert and rouge
    print("\n" + ("VERT" if vert else "ROUGE"))
    return 0 if vert else 1


if __name__ == "__main__":
    sys.exit(main())
