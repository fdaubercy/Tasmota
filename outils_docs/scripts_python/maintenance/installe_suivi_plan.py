r"""
=============================================================================
  installe_suivi_plan.py  -  Installe l'extension VS Code « Suivi du plan »
=============================================================================

UTILISATION
-----------
  python installe_suivi_plan.py                    Construit le .vsix et l'installe (si besoin).
  python installe_suivi_plan.py --etat             Diagnostic seul, ne modifie rien.
  python installe_suivi_plan.py --verifier         Installe si besoin PUIS prouve l'installation.
  python installe_suivi_plan.py --construire <dos> Construit seulement le .vsix dans <dos>.
  python installe_suivi_plan.py --mod              Installe aussi le mod Claude suivi-plan.

A LANCER UNE FOIS PAR POSTE apres un clone, puis apres chaque modification de l'extension
ou du parseur. Idempotent : si la version ET les fichiers installes sont deja ceux du depot,
il affiche « deja a jour » et ne fait rien.

CE QUE C'EST
------------
L'extension (outils_docs/vscode/suivi-plan/, JS pur, sans dependance ni build) affiche
l'avancement d'un plan tasks/plans/<chantier>.md (format : tasks/plans/_FORMAT.md) dans une
vue a droite de l'editeur, et « Plan 74 % » dans la barre d'etat. Le calcul vient du parseur
UNIQUE du mod Claude, .claude/mods/suivi-plan/hooks/parseur-plan.mjs, dont le .vsix embarque
une COPIE : apres une modification du parseur, relancer ce script (--etat compare les sha256).

Le .vsix est construit avec zipfile (ni vsce ni node) : [Content_Types].xml,
extension.vsixmanifest, extension/ = l'extension sauf ses bancs (test_*.js) + la copie du parseur ;
puis `code --install-extension <vsix> --force --profile <profil du depot>`. Les extensions VS Code
sont PAR PROFIL : le profil est celui que storage.json associe au dossier du depot (« Frederic »),
et --verifier le prouve aussi dans son extensions.json. --mod : `claude.cmd plugin marketplace add
<depot>/.claude/mods` si absente, puis `claude.cmd plugin install|update suivi-plan@mods-tasmota`.

REPLI SI VS CODE REFUSE LE .vsix
--------------------------------
Extraire extension/ du .vsix (--construire <dos>, puis l'ouvrir comme un zip) dans
    %USERPROFILE%\.vscode\extensions\fdaubercy.suivi-plan-<version>\
(package.json a la racine de ce dossier), puis redemarrer VS Code.

EN DEVELOPPEMENT
----------------
    code --extensionDevelopmentPath=<depot>\outils_docs\vscode\suivi-plan <depot>
L'extension lit alors le parseur directement dans .claude/mods/suivi-plan/hooks/.
Bancs : node outils_docs/vscode/suivi-plan/test_rendu.js et test_conversations.js
=============================================================================
"""
import argparse
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace", line_buffering=True)

RACINE = Path(__file__).resolve().parents[3]
DOSSIER_EXT = RACINE / "outils_docs" / "vscode" / "suivi-plan"
PARSEUR = RACINE / ".claude" / "mods" / "suivi-plan" / "hooks" / "parseur-plan.mjs"
EXCLUS = {"test_rendu.js", "test_conversations.js"}
IDENT = "fdaubercy.suivi-plan"
TYPES = {".json": "application/json", ".js": "application/javascript",
         ".mjs": "application/javascript", ".css": "text/css", ".md": "text/markdown",
         ".vsixmanifest": "text/xml", ".xml": "text/xml"}


def sha(octets: bytes) -> str:
    return hashlib.sha256(octets).hexdigest()


def version_depot() -> str:
    return json.loads((DOSSIER_EXT / "package.json").read_text(encoding="utf-8"))["version"]


def fichiers_extension() -> dict:
    """Fichiers a embarquer : {chemin relatif (/) : octets}, parseur compris."""
    r = {}
    for f in sorted(DOSSIER_EXT.rglob("*")):
        if f.is_file() and f.name not in EXCLUS and "__pycache__" not in f.parts:
            r[f.relative_to(DOSSIER_EXT).as_posix()] = f.read_bytes()
    r["parseur-plan.mjs"] = PARSEUR.read_bytes()
    return r


# ── Outils externes (code.cmd, claude.cmd) ───────────────────────────────────

def outil(*noms):
    return next((c for c in map(shutil.which, noms) if c), None)


def lance(exe, *args, timeout=180):
    """Lance exe (un .cmd marche avec subprocess.run sous Windows ; sinon repli cmd /c)."""
    for cmd in ([exe, *args], ["cmd", "/c", exe, *args]):
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=timeout)
            return p.returncode, (p.stdout or "") + (p.stderr or "")
        except OSError:
            continue
    return 127, f"impossible de lancer {exe}"


def profil_depot():
    """Profil VS Code associe au dossier du depot : (nom, id), ou (None, None) = profil par defaut.
    Les extensions sont PAR PROFIL : installee sans --profile, l'extension n'existe que dans le
    profil par defaut, invisible depuis le depot ouvert sous « Frederic » (constate le 2026-10-18)."""
    import os
    from urllib.parse import unquote
    stockage = Path(os.environ.get("APPDATA", "")) / "Code" / "User" / "globalStorage" / "storage.json"
    try:
        d = json.loads(stockage.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, None
    cible = "file:///" + str(RACINE).replace("\\", "/").lower()
    assoc = d.get("profileAssociations", {}).get("workspaces", {})
    ident = next((v for k, v in assoc.items() if unquote(k).lower().rstrip("/") == cible), None)
    nom = next((p.get("name") for p in d.get("userDataProfiles", []) if p.get("location") == ident), None)
    return (nom, ident) if nom else (None, None)


def options_profil(profil):
    return ["--profile", profil] if profil else []


def liste_du_profil(ident) -> bool:
    """Preuve independante de la CLI : l'extension figure dans extensions.json du profil."""
    import os
    f = (Path(os.environ.get("APPDATA", "")) / "Code" / "User" / "profiles" / ident / "extensions.json") if ident \
        else Path.home() / ".vscode" / "extensions" / "extensions.json"
    try:
        return any(e.get("identifier", {}).get("id", "").lower() == IDENT
                   for e in json.loads(f.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return False


def version_installee(code, profil=None):
    rc, sortie = lance(code, "--list-extensions", "--show-versions", *options_profil(profil))
    for ligne in sortie.splitlines():
        if ligne.strip().lower().startswith(IDENT + "@"):
            return ligne.strip().split("@", 1)[1]
    return None


def dossier_installe(version):
    return Path.home() / ".vscode" / "extensions" / f"{IDENT}-{version}"


def ecarts_installes(version) -> list:
    """Fichiers du depot absents ou differents dans l'extension installee (package.json exclu :
    VS Code y ajoute ses metadonnees ; la version le couvre)."""
    d = dossier_installe(version)
    return [rel for rel, octets in fichiers_extension().items() if rel != "package.json" and
            (not (d / rel).is_file() or sha((d / rel).read_bytes()) != sha(octets))]


# ── Construction du .vsix ────────────────────────────────────────────────────

def manifeste(version: str) -> str:
    pkg = json.loads((DOSSIER_EXT / "package.json").read_text(encoding="utf-8"))
    def xml(t):
        return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    desc = xml(pkg.get("description", ""))
    return f"""<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011" xmlns:d="http://schemas.microsoft.com/developer/vsx-schema-design/2011">
  <Metadata>
    <Identity Language="en-US" Id="suivi-plan" Version="{version}" Publisher="fdaubercy" />
    <DisplayName>{xml(pkg.get("displayName", "suivi-plan"))}</DisplayName>
    <Description xml:space="preserve">{desc}</Description>
    <Tags></Tags>
    <Categories>Other</Categories>
    <GalleryFlags>Public</GalleryFlags>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="{xml(pkg["engines"]["vscode"])}" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionDependencies" Value="" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionPack" Value="" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionKind" Value="workspace" />
      <Property Id="Microsoft.VisualStudio.Code.LocalizedLanguages" Value="" />
    </Properties>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code" />
  </Installation>
  <Dependencies />
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />
  </Assets>
</PackageManifest>
"""


def construit(dossier: Path) -> Path:
    version = version_depot()
    fichiers = fichiers_extension()
    exts = sorted({Path(r).suffix.lower() for r in fichiers} | {".vsixmanifest"})
    types = "".join(f'<Default Extension="{e}" ContentType="{TYPES.get(e, "application/octet-stream")}"/>'
                    for e in exts)
    dossier.mkdir(parents=True, exist_ok=True)
    vsix = dossier / f"{IDENT}-{version}.vsix"
    with zipfile.ZipFile(vsix, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="utf-8"?>\n'
                   f'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">{types}</Types>\n')
        z.writestr("extension.vsixmanifest", manifeste(version))
        for rel, octets in fichiers.items():
            z.writestr("extension/" + rel, octets)
    return vsix


# ── Diagnostic ───────────────────────────────────────────────────────────────

def etat(code, profil):
    """Affiche l'etat ; rend (version installee, a jour ?)."""
    v_depot = version_depot()
    print(f"  Extension du depot   : {IDENT} {v_depot}  ({DOSSIER_EXT})")
    print(f"  Profil VS Code       : {profil or 'par defaut'} (celui du depot)")
    if not code:
        print("  VS Code              : commande `code` introuvable dans le PATH")
        return None, False
    v = version_installee(code, profil)
    print(f"  Extension installee  : {v or 'absente'} (dans ce profil)")
    print(f"  Parseur source       : {sha(PARSEUR.read_bytes())[:16]}  ({PARSEUR.relative_to(RACINE)})")
    if not v:
        return None, False
    emb = dossier_installe(v) / "parseur-plan.mjs"
    print(f"  Parseur embarque     : {sha(emb.read_bytes())[:16] if emb.is_file() else 'absent'}  ({emb})")
    ecarts = ecarts_installes(v)
    if ecarts:
        print(f"  Fichiers differents  : {', '.join(ecarts)}")
    a_jour = v == v_depot and not ecarts
    print(f"  Bilan                : {'a jour' if a_jour else 'A METTRE A JOUR'}")
    return v, a_jour


def etat_mod():
    claude = outil("claude.cmd", "claude")
    if not claude:
        print("  Mod Claude           : commande `claude` introuvable")
        return None, False
    rc, sortie = lance(claude, "plugin", "list", timeout=60)
    present = "suivi-plan" in sortie
    print(f"  Mod Claude suivi-plan: {'installe' if present else 'absent'}")
    return claude, present


def installe(code, profil) -> bool:
    with tempfile.TemporaryDirectory(prefix="suivi-plan-") as tmp:
        vsix = construit(Path(tmp))
        print(f"  .vsix construit : {vsix.name} ({vsix.stat().st_size} octets), profil {profil or 'par defaut'}")
        return montre(*lance(code, "--install-extension", str(vsix), "--force", *options_profil(profil))) == 0


def montre(rc, sortie):
    print("  " + sortie.strip().replace("\n", "\n  "))
    return rc


def installe_mod():
    claude, present = etat_mod()
    if not claude:
        return 1
    marche = "mods-tasmota" in lance(claude, "plugin", "marketplace", "list", timeout=60)[1]
    montre(*(lance(claude, "plugin", "marketplace", "update", "mods-tasmota", timeout=120) if marche else
             lance(claude, "plugin", "marketplace", "add", str(RACINE / ".claude" / "mods"), timeout=120)))
    rc = montre(*lance(claude, "plugin", "update" if present else "install", "suivi-plan@mods-tasmota", timeout=180))
    return 0 if rc == 0 else 1


def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--etat", action="store_true")
    p.add_argument("--verifier", action="store_true")
    p.add_argument("--mod", action="store_true")
    p.add_argument("--construire", metavar="DOSSIER")
    p.add_argument("-h", "--help", action="store_true")
    a = p.parse_args()
    if a.help:
        print(__doc__)
        return 0
    if not PARSEUR.is_file():
        print(f"[X] Parseur introuvable : {PARSEUR}")
        return 1

    if a.construire:
        vsix = construit(Path(a.construire).resolve())
        print(f"[OK] {vsix}")
        with zipfile.ZipFile(vsix) as z:
            for info in z.infolist():
                print(f"  {info.file_size:>7}  {info.filename}")
        return 0

    code = outil("code.cmd", "code")
    profil, ident = profil_depot()
    print("\nSuivi du plan - etat\n")
    v, a_jour = etat(code, profil)
    if a.etat:
        etat_mod()
        print("\n--etat : rien n'a ete modifie.")
        return 0 if a_jour else 1
    if not code:
        print("\n[X] Installer la commande `code` (VS Code : Shell Command: Install 'code' command in PATH).")
        return 1

    rc = 0
    if a_jour:
        print("\n[OK] Extension deja a jour.")
    else:
        print("\nInstallation\n")
        if not installe(code, profil):
            print("[X] Installation refusee : voir le repli dans --help.")
            return 1
    if a.verifier:
        v, attendu = version_installee(code, profil), version_depot()
        ecarts = [e for e in ecarts_installes(v) if e != "parseur-plan.mjs"] if v else ["extension absente"]
        emb = dossier_installe(v) / "parseur-plan.mjs" if v else None
        ok_parseur = bool(emb and emb.is_file() and sha(emb.read_bytes()) == sha(PARSEUR.read_bytes()))
        print(f"\nVerification\n\n  {IDENT}@{v} liste : {'OUI' if v == attendu else 'NON (attendu ' + attendu + ')'}")
        print(f"  parseur embarque = source : {'OUI' if ok_parseur else 'NON'}")
        print(f"  autres fichiers identiques : {'OUI' if not ecarts else 'NON : ' + ', '.join(ecarts)}")
        dans_profil = liste_du_profil(ident)
        print(f"  dans extensions.json du profil {profil or 'par defaut'} : {'OUI' if dans_profil else 'NON'}")
        rc = 0 if (v == attendu and ok_parseur and not ecarts and dans_profil) else 1
        print("\n[OK] Installation prouvee. Recharger les fenetres VS Code ouvertes (Developer: Reload Window)."
              if rc == 0 else "\n[X] Installation non conforme.")
    if a.mod:
        print("\nMod Claude\n")
        rc = installe_mod() or rc
    return rc


if __name__ == "__main__":
    sys.exit(main())
