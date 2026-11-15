"""Genere outils_docs/LIENS_WEB.md : tous les liens web cites dans les fichiers du fork.

Sources lues : fichiers suivis par git de tasks/, outils_docs/, docs/, .claude/, data/, CLAUDE.md et des
deux .ini (jamais l'amont Tasmota). Ecarts : bancs, bibliotheques tierces (/lib/), persist et config decodee,
adresses fictives de test, noms d'hote locaux, URLs a identifiants.
Les documents telecharges (PDF, docx, exe, video) sont listes d'apres le disque, avec le contenu des URL.txt.

    python outils_docs/scripts_python/outils_pc/genere_liens_web.py [--verifier]

--verifier : code 1 si LIENS_WEB.md n'est pas a jour (rien n'est ecrit).
"""
import collections
import ipaddress
import json
import re
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
SORTIE = RACINE / "outils_docs" / "LIENS_WEB.md"
AJOUTES = RACINE / "outils_docs" / "liens_web" / "liens_ajoutes.json"   # liens saisis dans la page de l'annuaire (outil « Liens web »)
DOSSIERS = ["tasks", "outils_docs", "docs", ".claude", "data", "CLAUDE.md",
            "platformio_override.ini", "platformio_tasmota_cenv.ini"]
BINAIRES = (".png", ".jpg", ".jpeg", ".gz", ".ttf", ".xlsx", ".xlsm", ".pdf", ".docx", ".bmp", ".ico", ".pptx",
            ".woff2", ".exe", ".wmv", ".svg", ".bin", ".dll", ".zip")
FICHIERS_IGNORES = re.compile(r"(^|/)(test_[^/]*|banc_[^/]*|bouchons_berry|lib|sauvegardes_cartes)/|"
                              r"(^|/)(test_|banc_)[^/]*$|organigramme_plans/|liens_web/|persist|config_decodee|LIENS_WEB\.md|/LICENSE$")
HOTES_IGNORES = re.compile(r"evil|exemple|example|monserveur|proprio|\.local$|\.lan$|^localhost$|"
                           r"w3\.org|openxmlformats|schemas\.microsoft|json-schema\.org|unlicense|shields\.io|nsis\.sf\.net")
URL = re.compile(r"https?://[^\s<>\"'`)\]}\\,;*|]+")
OUTILS = [  # (port, nom) : repris de CLAUDE.md, carte des documents
    (7000, "Pont serie"), (7100, "Sniffeur / publieur MQTT"), (7200, "Serveur syslog"), (7300, "Sniffeur ModBus"),
    (7350, "Sniffeur I2C"), (7400, "Testeur UDP maitre/esclave"), (7500, "Synchro du fork"),
    (7600, "Annuaire des outils"), (7700, "Build et televersement"), (7800, "Fichiers Berry par env"),
    (7900, "Assistant persist"), (7905, "Liens web"), (7910, "Sondes en cours"), (7920, "Taches planifiees"),
    (7915, "Plan de la maison"), (7930, "Catalogue d'icones"), (7940, "Cartes simulees"), (7950, "Atelier des graphiques"),
    (7960, "Atelier des ecrans"), (7970, "Etiquettes QR code"), (7980, "Fabrique d'extensions"),
    (7985, "Atelier des visuels d'accueil"), (7990, "Organigramme des plans"), (7995, "Menage du depot")]
CATEGORIES = [  # (titre, fragments de domaine ou de debut d'URL) ; premier qui correspond
    ("Ce fork (fdaubercy)", ("github.com/fdaubercy", "fdaubercy.github.io")),
    ("Tasmota amont : depot, documentation, OTA", ("github.com/arendst", "tasmota.github.io", "ota.tasmota.com",
                                                  "templates.blakadder", "tasmota.com")),
    ("Depots et projets GitHub tiers", ("github.com", "githubusercontent", "gist.github", "github.io")),
    ("Espressif (puces, ESP-IDF, esp-hosted)", ("espressif.com", "esp-idf", "espboards.dev")),
    ("Fabricants, boutiques, fiches materiel", ("waveshare", "amazon.", "aliexpress", "openelab", "devices.esphome",
                                               "cnx-software", "atomic14", "ozeki", "crccalc")),
    ("PCB, fabrication, KiCad", ("jlcpcb", "pcbway", "kicad")),
    ("Icones, polices, images, design", ("pictogrammers", "fonts.g", "iconify", "lucide", "phosphor", "tabler",
                                         "simpleicons", "lvgl.io", "material")),
    ("IA et fournisseurs de modeles", ("openrouter", "aistudio", "mistral", "anthropic", "google.com", "openai")),
    ("Bibliotheques chargees par les pages (CDN)", ("cdn.", "cdnjs", "unpkg")),
    ("Wikipedia et references", ("wikipedia",)),
    ("Pages Claude (artifacts publies)", ("claude.ai",)),
]


def fichiers():
    sortie = subprocess.run(["git", "ls-files", *DOSSIERS], cwd=RACINE, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", check=True).stdout
    for f in sortie.splitlines():
        if f and not f.lower().endswith(BINAIRES) and not FICHIERS_IGNORES.search(f):
            yield f


def utile(u):
    h = re.match(r"https?://([^/:?#]+)", u)
    if not h or any(c in u for c in "%{$([@\\") or u.count("://") > 1:
        return False
    hote = h.group(1)
    if "." not in hote or HOTES_IGNORES.search(hote.lower()):
        return False
    try:
        ipaddress.ip_address(hote)
        return False  # adresses IP (cartes du parc, boucle locale) : pas des liens a retrouver
    except ValueError:
        return True


def collecte():
    liens = collections.defaultdict(set)
    for f in fichiers():
        try:
            texte = (RACINE / f).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for u in URL.findall(texte):
            u = u.rstrip(".:!?")
            if utile(u):
                liens[u].add(f)
    return liens


def categorie(u):
    bas = u.lower()
    for titre, frags in CATEGORIES:
        if any(fr in bas for fr in frags):
            return titre
    return "Autres sites"


def documents():
    """PDF, Word, executables, videos et URL.txt tels qu'ils sont sur le disque (suivis par git)."""
    sortie = subprocess.run(["git", "ls-files", "outils_docs"], cwd=RACINE, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", check=True).stdout
    par_dossier = collections.defaultdict(list)
    for f in sortie.splitlines():
        nom = Path(f).name
        if nom.startswith("~$"):
            continue
        if nom.lower().endswith((".pdf", ".docx", ".doc", ".exe", ".wmv", ".xlsm", ".zip")) or nom == "URL.txt":
            par_dossier[str(Path(f).parent).replace("\\", "/")].append(nom)
    return par_dossier


def ajoutes():
    """Liens saisis a la main : [{url, titre, categorie, note, date}] ; fichier absent ou illisible = aucun."""
    try:
        d = json.loads(AJOUTES.read_text(encoding="utf-8"))
        return [x for x in d if isinstance(x, dict) and utile(str(x.get("url", "")))]
    except (OSError, ValueError):
        return []


def ecrit():
    liens = collecte()
    groupes = collections.defaultdict(list)
    for u in sorted(liens, key=str.lower):
        groupes[categorie(u)].append(u)
    ordre = [c[0] for c in CATEGORIES] + ["Autres sites"]
    m = ["# Liens web du depot", "",
         "> Fichier GENERE par `outils_docs/scripts_python/outils_pc/genere_liens_web.py` : ne pas l'editer a la main,",
         "> relancer le script (`--verifier` = code 1 si ce fichier est en retard). Les liens viennent des fichiers du fork",
         "> (`tasks/`, `outils_docs/`, `docs/`, `.claude/`, `data/`, `CLAUDE.md`, les deux `.ini`), jamais de l'amont Tasmota.",
         "> Sont ecartes : bancs, bibliotheques tierces, persist, adresses IP du parc, adresses fictives de test.", "",
         "## 1. Outils du depot (pages locales, a lancer depuis l'annuaire)", "",
         "Annuaire : http://127.0.0.1:7600 (tuile de chaque outil, lance et arrete). Adresse `127.0.0.1` depuis ce PC.", "",
         "| Port | Outil |", "|---|---|"]
    m += [f"| {p} | http://127.0.0.1:{p} : {n} |" for p, n in OUTILS]
    m += ["", "## 2. Liens externes cites dans le depot", ""]
    for titre in ordre:
        if titre not in groupes:
            continue
        m += [f"### {titre} ({len(groupes[titre])})", ""]
        for u in groupes[titre]:
            f = sorted(liens[u])
            plus = f" (+{len(f) - 1})" if len(f) > 1 else ""
            m.append(f"- <{u}>  \n  cite dans `{f[0]}`{plus}")
        m.append("")
    manuels = ajoutes()
    if manuels:
        m += [f"### Liens ajoutes a la main ({len(manuels)})", ""]
        for x in manuels:
            m.append(f"- <{x['url']}>  \n  {x.get('titre') or ''} ({x.get('categorie') or 'Autres sites'}) {x.get('note') or ''}".rstrip())
        m.append("")
    m += ["## 3. Documents telecharges ou fournis (dans le depot)", "",
          "Fiches constructeur, manuels, outils Windows : a retrouver sous `outils_docs/`.", ""]
    for dossier, noms in sorted(documents().items()):
        m += [f"### `{dossier}/`", ""] + [f"- {n}" for n in sorted(noms)] + [""]
    for u in sorted(RACINE.glob("outils_docs/**/URL.txt")):
        m += [f"Raccourci `{u.relative_to(RACINE).as_posix()}` : " + u.read_text(encoding="utf-8", errors="ignore").strip(), ""]
    return "\n".join(m).rstrip() + "\n"


def main():
    texte = ecrit()
    if "--verifier" in sys.argv:
        a_jour = SORTIE.exists() and SORTIE.read_text(encoding="utf-8") == texte
        print("a jour" if a_jour else "en retard : relancer genere_liens_web.py")
        return 0 if a_jour else 1
    SORTIE.write_text(texte, encoding="utf-8", newline="\n")
    print(f"{SORTIE.relative_to(RACINE)} : {texte.count(chr(10))} lignes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
