r"""Banc de logFonctions.declare (plan tasks/plans/binomes-berry.md A4) : banc_log_declare.be sur data/fs/logFonctions.be, puis
temoins (copies modifiees de logFonctions.be, chacune doit etre rouge).

    python outils_docs/scripts_python/berry/banc_log_declare.py

Code de sortie 0 si tout est vert. Ne teste pas une vraie carte (tasmota et persist simules).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
BERRY = RACINE / "lib/libesp32/berry/berry.exe"
BANC = "outils_docs/scripts_python/berry/banc_log_declare.be"
LOGS = RACINE / "data/fs/logFonctions.be"
VERT = "BANC_LOG_DECLARE: OK"

MUTANTS = [
    ("declaree non rangee", '    d[string.tolower(str(cible))] = [str(cible), str(chemin), description]\n', ""),
    ("lieu sans repli declare", "    if (bloc == nil)    bloc = logFonctions.blocDeclare(c)    end", ""),
    ("cibles() sans les declarees", "        if (logFonctions.trouveCle(logFonctions.CIBLES, k) == nil)    l.push(d[k][0])    end\n", ""),
    ("tous sur CIBLES seulement", "        for c: logFonctions.cibles()\n", "        for c: logFonctions.CIBLES\n"),
    ("chemin non descendu", "        bloc = bloc.find(parties[i])\n", ""),
    ("description declaree ignoree", "    return (x != nil && x[2] != nil ? str(x[2]) : cible)", "    return cible"),
]


def lance(dossier: str) -> str:
    try:
        r = subprocess.run([str(BERRY), BANC, dossier], cwd=RACINE, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return "BLOQUE"
    return r.stdout + r.stderr


def main() -> int:
    sortie = lance("data/fs")
    print(sortie.strip())
    ok = VERT in sortie
    texte = LOGS.read_text(encoding="utf-8").replace("\r\n", "\n")
    print("--- Temoins (chaque mutant doit etre rouge)")
    with tempfile.TemporaryDirectory() as t:
        for i, (nom, avant, apres) in enumerate(MUTANTS):
            if texte.count(avant) != 1:
                print(f"  ECHEC temoin « {nom} » : texte absent ou ambigu")
                ok = False
                continue
            d = Path(t) / f"m{i}"
            d.mkdir()
            (d / "logFonctions.be").write_text(texte.replace(avant, apres), encoding="utf-8")
            rouge = VERT not in lance(str(d))
            print(f"  {'OK   ' if rouge else 'ECHEC'} temoin : {nom}")
            ok = ok and rouge
    print("BANC_LOG_DECLARE (enveloppe):", "VERT" if ok else "ROUGE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
