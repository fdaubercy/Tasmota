"""Banc de l'import de polices de l'atelier des ecrans (atelier_ecrans_polices.py et routes /polices/*), plan A9.

UTILISATION (copie temporaire du depot ; ~1 min)
    "$USERPROFILE/.platformio/penv/Scripts/python.exe" outils_docs/scripts_python/outils_pc/test_atelier_ecrans_polices.py
Verifie : analyse de la police du depot (licence Apache reconnue, Latin-1 complet) ; Latin-1 incomplet detecte ;
refus : pas un TrueType, police tronquee, nom dangereux, licence non confirmee, build en cours, nom deja pris ; import :
police dans le dossier de la carte, licence HORS de ce dossier, catalogue regenere et a jour ; routes en base64 (corps
de plus de 256 Ko accepte sur /polices/*, refuse ailleurs ; 403 sans en-tete). Code de sortie 0 = vert.
"""
import base64
import shutil
import os
import struct
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atelier_ecrans_catalogue as cat     # noqa: E402
import atelier_ecrans_polices as aep       # noqa: E402
import test_atelier_ecrans_web as taw      # noqa: E402

ENV = "tasmota32s3-bureau-ecran-debits-pac"
DOSSIER = "data/bureau/tasmota32s3-ecran-debits-pac"
ECHECS = []


def verifie(obtenu, attendu, libelle):
    ok = obtenu == attendu
    print(("OK   " if ok else "KO   ") + libelle + ("" if ok else f"  (obtenu {obtenu!r}, attendu {attendu!r})"), flush=True)
    if not ok:
        ECHECS.append(libelle)


def refus(f, genre, motif, libelle):
    try:
        f()
    except genre as e:
        verifie(motif in str(e), True, libelle + ("" if motif in str(e) else f" [{e}]"))
        return
    verifie("pas de refus", "refus", libelle)


def police(cmap):
    """TrueType minimal fabrique a la main : tables cmap (donnee), glyf et name vides."""
    tables = {b"cmap": cmap, b"glyf": b"\0" * 4, b"name": struct.pack(">HHH", 0, 0, 6)}
    tete = b"\x00\x01\x00\x00" + struct.pack(">HHHH", len(tables), 0, 0, 0)
    off, recs, corps = 12 + 16 * len(tables), b"", b""
    for tag, data in sorted(tables.items()):
        recs += struct.pack(">4sIII", tag, 0, off + len(corps), len(data))
        corps += data
    return tete + recs + corps


def cmap12(groupes):
    """cmap format 12 (Windows, UCS-4) avec `groupes` plages 0..0x2FFF : chacune couvre tout le Latin-1."""
    sous = struct.pack(">HHIII", 12, 0, 16 + 12 * groupes, 0, groupes) + struct.pack(">III", 0, 0x2FFF, 0) * groupes
    return struct.pack(">HH", 0, 1) + struct.pack(">HHI", 3, 10, 12) + sous


def main():
    with tempfile.TemporaryDirectory(prefix="banc_atelier_polices_") as t:
        os.environ["OUTILS_TASMOTA_DOSSIER"] = str(Path(t) / "donnees")
        b = taw.Banc(t)
        racine = b.racine
        for rel in cat.SOURCES:                          # sources du firmware lues par cat.genere
            (racine / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(taw.DEPOT / rel, racine / rel)
        try:
            ttf = (racine / DOSSIER / "RobotoCondensed-Regular.ttf").read_bytes()
            a = aep.analyse("RobotoCondensed-Regular.ttf", ttf)
            verifie((a["libre"], a["manque"], "Apache" in a["licence"]), (True, "", True), "analyse : licence Apache reconnue, Latin-1 complet")
            verifie("".join(chr(c) for c in aep.manque_latin1(set(aep.LATIN1) - {0xE9, 0xB0})), "°é", "Latin-1 incomplet : é et ° manquants rendus")
            refus(lambda: aep.analyse("x.ttf", b"wOFF" + ttf[4:]), ValueError, "TrueType", "WOFF refuse")
            refus(lambda: aep.analyse("x.ttf", ttf[:5000]), ValueError, "tronquee", "police tronquee refusee")
            refus(lambda: aep.analyse("../x.ttf", ttf), ValueError, "nom de fichier", "nom avec chemin refuse")
            refus(lambda: aep.analyse("x.otf", ttf), ValueError, "nom de fichier", "extension autre que .ttf refusee")
            debut = time.monotonic()
            a = aep.analyse("Masse.ttf", police(cmap12(20000)))
            duree = time.monotonic() - debut
            verifie((a["manque"], duree < 2), ("", True), f"police a 20 000 groupes cmap : analysee en temps borne ({duree:.2f} s)")
            truquee = police(struct.pack(">HH", 0, 50))            # 50 sous-tables annoncees, 4 octets
            refus(lambda: aep.analyse("x.ttf", truquee), ValueError, "corrompue", "cmap annoncee plus longue que ses octets : refus propre")
            refus(lambda: aep.importe(racine, ENV, "Essai-Police.ttf", ttf, False, lambda: []), ValueError, "licence", "licence non confirmee refusee")
            refus(lambda: aep.importe(racine, ENV, "Essai-Police.ttf", ttf, True, lambda: ["upload"]), RuntimeError, "build", "build en cours refuse")
            refus(lambda: aep.importe(racine, ENV, "robotocondensed-regular.TTF".replace(".TTF", ".ttf"), ttf, True, lambda: []), RuntimeError,
                  "existe deja", "nom deja pris (casse ignoree) refuse")
            verifie((racine / DOSSIER / "Essai-Police.ttf").exists(), False, "apres les refus : rien d'ecrit")

            r = aep.importe(racine, ENV, "Essai-Police.ttf", ttf, True, lambda: [])
            verifie((racine / DOSSIER / "Essai-Police.ttf").read_bytes() == ttf, True, "import : police dans le dossier de la carte")
            lic = racine / aep.DOSSIER_LICENCES / "Essai-Police.licence.txt"
            verifie((lic.is_file(), "Apache" in lic.read_text(encoding="utf-8")), (True, True), "import : licence hors du dossier de la carte")
            noms = [p["nom"] for p in cat.charge(racine)["polices"]]
            verifie(("Essai-Police" in noms, cat.verifie(racine)), (True, []), "import : catalogue regenere et a jour")
            verifie(sorted(r["ecrits"]), sorted([f"{DOSSIER}/Essai-Police.ttf", f"{aep.DOSSIER_LICENCES}/Essai-Police.licence.txt", cat.CATALOGUE]),
                    "import : trois fichiers ecrits")

            gros = base64.b64encode(ttf + b"\0" * (200 * 1024)).decode()      # > 256 Ko une fois en base64
            s, r = b.requete("POST", "/polices/analyse", {"nom": "Gros.ttf", "contenu": gros})
            verifie((s, r.get("libre") if isinstance(r, dict) else r, bool(r.get("sites")) if isinstance(r, dict) else None), (200, True, True),
                    "POST /polices/analyse : corps de plus de 256 Ko accepte, sites rendus")
            verifie(b.requete("POST", "/apercu", {"env": ENV, "description": {"x": gros}})[0], 400, "corps de plus de 256 Ko refuse hors /polices/")
            verifie(b.requete("POST", "/polices/analyse", {"nom": "x.ttf", "contenu": "pas du base64 !"})[0], 400, "contenu non base64 -> 400")
            verifie(b.requete("POST", "/polices/analyse", {"nom": "x.ttf", "contenu": base64.b64encode(truquee).decode()})[0], 400,
                    "police corrompue -> 400 (pas 500)")
            verifie(b.requete("POST", "/polices/importer", {"env": ENV, "nom": "Autre.ttf", "contenu": gros, "licence_confirmee": True},
                              entetes={})[0], 403, "POST /polices/importer sans en-tete -> 403")
            verifie(b.requete("POST", "/polices/importer", {"env": "inconnu", "nom": "Autre.ttf", "contenu": gros, "licence_confirmee": True})[0],
                    400, "POST /polices/importer : env inconnu -> 400")
            s, r = b.requete("POST", "/polices/importer", {"env": ENV, "nom": "Autre.ttf", "contenu": base64.b64encode(ttf).decode(),
                                                            "licence_confirmee": True})
            verifie((s, (racine / DOSSIER / "Autre.ttf").is_file()), (200, True), "POST /polices/importer : police importee")
            s, r = b.requete("GET", "/police?nom=Autre")
            verifie((s, b.brut == ttf), (200, True), "GET /police : la police importee est servie a la page")
        finally:
            b.ferme()
    print(f"\n{len(ECHECS)} echec(s) : " + ("VERT" if not ECHECS else "ROUGE"))
    return 1 if ECHECS else 0


if __name__ == "__main__":
    sys.exit(main())
