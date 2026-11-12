"""Import d'une police .ttf dans l'atelier des ecrans (plan atelier-ecrans A9, skill lvgl-haspmota references/polices.md).

`analyse(nom, octets)` lit les tables `name` (famille, licence, URL de licence) et `cmap` (caracteres couverts) d'un
TrueType et rend ce qu'il manque du Latin-1 (U+0020-007E, U+00A0-00FF, ° compris). `importe` ecrit la police dans le
dossier de la carte (`data/<lieu>/<carte>/<nom>.ttf` : elle part sur le FS, `ecranFonctions.rangePolices` la range sous
`/sd/polices/` au demarrage), son texte de licence HORS du dossier de la carte (`outils_docs/atelier_ecrans/polices/`,
le dossier de la carte part en flash), puis regenere le catalogue (`atelier_ecrans_catalogue.genere`), en une
Transaction ; refus pendant un build, licence non confirmee par l'utilisateur, Latin-1 incomplet, nom deja pris.
shortcut: .ttf seulement (pas de .bin LVGL par taille : catalogue, validateur et generateurs ne les connaissent pas) ;
la police s'ajoute a la carte choisie, les autres cartes ne l'ont pas sur leur FS.
"""
import json
import re
import struct

import atelier_ecrans_catalogue as cat
import atelier_ecrans_ecriture as aee
import fichiers_berry_etat as fbe
import fichiers_berry_sauvegarde as fbs
from pathlib import Path

TAILLE_MAX = 3 * 1024 * 1024
NOM = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.ttf")
DOSSIER_LICENCES = "outils_docs/atelier_ecrans/polices"
LATIN1 = list(range(0x20, 0x7F)) + list(range(0xA0, 0x100))
LICENCES_LIBRES = ("SIL Open Font License", "OFL", "Apache License", "apache.org/licenses", "scripts.sil.org/OFL",
                   "openfontlicense.org", "Ubuntu Font Licence", "public domain")
SITES = [("Google Fonts", "https://fonts.google.com"), ("Font Squirrel (licences « 100 % free »)", "https://www.fontsquirrel.com"),
         ("Convertisseur LVGL (polices .bin, pas encore importables ici)", "https://lvgl.io/tools/fontconverter")]


def _tables(b):
    if len(b) < 12 or b[:4] not in (b"\x00\x01\x00\x00", b"true"):
        raise ValueError("ce n'est pas une police TrueType (.ttf) : en-tete inattendu (OpenType CFF, WOFF ou autre refuses)")
    n = struct.unpack(">H", b[4:6])[0]
    if len(b) < 12 + 16 * n:
        raise ValueError("police tronquee (table des tables)")
    tables = {}
    for i in range(n):
        tag, _, off, ln = struct.unpack(">4sIII", b[12 + 16 * i:28 + 16 * i])
        if off + ln > len(b):
            raise ValueError(f"police tronquee (table {tag.decode('latin-1')})")
        tables[tag.decode("latin-1")] = b[off:off + ln]
    return tables


def _noms(t):
    """{nameID: texte} de la table name (Windows Unicode d'abord, puis Mac Roman)."""
    if len(t) < 6:
        return {}
    nb, debut = struct.unpack(">HH", t[2:6])
    res = {}
    for i in range(nb):
        if 6 + 12 * (i + 1) > len(t):
            break
        plat, enc, lang, nid, ln, off = struct.unpack(">HHHHHH", t[6 + 12 * i:18 + 12 * i])
        brut = t[debut + off:debut + off + ln]
        if plat in (0, 3):
            texte = brut.decode("utf-16-be", errors="replace")
        elif plat == 1 and nid not in res:
            texte = brut.decode("mac_roman", errors="replace")
        else:
            continue
        if plat == 3 or nid not in res:
            res[nid] = texte
    return res


def _cmap(t):
    """Points de code du Latin-1 couverts (sous-tables format 4 et 12, plateforme Unicode ou Windows) : chaque plage est
    ramenee a 0x20..0xFF, sinon 280 000 groupes d'un fichier de 3 Mo coutent des milliards d'insertions."""
    if len(t) < 4:
        return set()
    nb = struct.unpack(">H", t[2:4])[0]
    codes = set()
    for i in range(nb):
        plat, enc, off = struct.unpack(">HHI", t[4 + 8 * i:12 + 8 * i])
        if plat not in (0, 3) or off + 4 > len(t):
            continue
        fmt = struct.unpack(">H", t[off:off + 2])[0]
        if fmt == 4:
            segx2 = struct.unpack(">H", t[off + 6:off + 8])[0]
            ends = struct.unpack(f">{segx2 // 2}H", t[off + 14:off + 14 + segx2])
            starts = struct.unpack(f">{segx2 // 2}H", t[off + 16 + segx2:off + 16 + 2 * segx2])
            for s, e in zip(starts, ends):
                if s != 0xFFFF:
                    codes.update(range(max(s, 0x20), min(e, 0xFF) + 1))
        elif fmt == 12:
            ngroups = struct.unpack(">I", t[off + 12:off + 16])[0]
            for g in range(ngroups):
                s, e, _ = struct.unpack(">III", t[off + 16 + 12 * g:off + 28 + 12 * g])
                codes.update(range(max(s, 0x20), min(e, 0xFF) + 1))
    return codes


def manque_latin1(codes):
    return [c for c in LATIN1 if c not in codes and c != 0xAD]      # trait d'union conditionnel : jamais dessine


def analyse(nom, octets):
    """{"nom", "fichier", "famille", "licence", "url_licence", "libre", "manque", "poids"} ; ValueError si refusee."""
    if not isinstance(nom, str) or not NOM.fullmatch(nom):
        raise ValueError("nom de fichier attendu : lettres, chiffres, - ou _, fini par .ttf (64 caracteres au plus)")
    if len(octets) > TAILLE_MAX:
        raise ValueError(f"police trop lourde ({len(octets) // 1024} Ko, {TAILLE_MAX // 1024} Ko au plus sur le FS)")
    try:
        t = _tables(octets)
        if "cmap" not in t or "name" not in t or "glyf" not in t:
            raise ValueError("police incomplete (tables cmap, name ou glyf absentes)")
        noms, codes = _noms(t["name"]), _cmap(t["cmap"])
    except struct.error as e:                     # table annoncee plus longue que ses octets : 400, pas 500
        raise ValueError(f"police corrompue ({e})") from e
    licence, url = noms.get(13, "").strip(), noms.get(14, "").strip()
    libre = any(m.lower() in (licence + " " + url).lower() for m in LICENCES_LIBRES)
    return {"nom": nom[:-4], "fichier": nom, "famille": noms.get(1, "?") + " " + noms.get(2, ""), "licence": licence,
            "url_licence": url, "libre": libre, "manque": "".join(chr(c) for c in manque_latin1(codes)),
            "poids": len(octets)}


def importe(racine, env, nom, octets, licence_confirmee, builds_en_cours):
    """{"ecrits", "analyse"} ; ValueError (police refusee) ou RuntimeError (build en cours, nom deja pris)."""
    a = analyse(nom, octets)
    if a["manque"]:
        raise ValueError("caracteres francais absents de la police (Latin-1 incomplet) : " + a["manque"][:40])
    if not licence_confirmee:
        raise ValueError("licence a confirmer (OFL, Apache 2.0... : libre d'usage) avant l'import")
    aee.refuse_build(builds_en_cours)
    racine = Path(racine)
    if any(p.name.lower() == nom.lower() for p in racine.glob("data/*/*/*.ttf")):
        raise RuntimeError(f"une police {nom} existe deja dans le depot : renommer le fichier")
    rel = f"{fbe.dossier_carte(env)}/{nom}"
    texte_licence = (f"Police : {a['famille']}\nFichier : {nom}\nImportee par l'atelier des ecrans pour {env}\n"
                     f"Licence (table name, nameID 13) :\n{a['licence'] or '(absente de la police)'}\n"
                     f"URL de licence (nameID 14) : {a['url_licence'] or '(absente)'}\n"
                     "Licence confirmee par l'utilisateur dans la page.\n").encode("utf-8")
    rel_licence = f"{DOSSIER_LICENCES}/{nom[:-4]}.licence.txt"
    (racine / DOSSIER_LICENCES).mkdir(parents=True, exist_ok=True)
    with fbs.Transaction(racine, "atelier-ecrans-police") as tr:
        tr.ecrit(rel, octets)                    # d'abord la police : cat.genere la lit dans data/*/*/*.ttf
        tr.ecrit(rel_licence, texte_licence)
        tr.ecrit(cat.CATALOGUE, (json.dumps(cat.genere(racine), ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    return {"ecrits": [rel, rel_licence, cat.CATALOGUE], "analyse": a}
