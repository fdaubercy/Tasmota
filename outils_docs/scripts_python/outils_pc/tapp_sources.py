"""Sources des extensions de la Fabrique d'extensions (tapp_web.py) : data/extensions/<nom>/, gabarits, manifeste, controle, fabrication.

Rien n'est ecrit hors de data/extensions/ ; aucune suppression ; une creation n'ecrase jamais. Les noms de fichiers listes viennent de
os.scandir, jamais du client. Le code Berry s'ecrit dans VS Code : la page n'edite que le manifeste.
Ce dossier n'est pas une carte : berry/carte_modules_berry.py::collecte l'ecarte, les autres lecteurs de data/*/* cherchent un _persist.json.
gen_tapp.py n'est pas reentrant (redirect_stdout, AVERTISSEMENTS, fichier preambule de verifie_berry) : tout controle et toute
construction passent par VERROU. Les lectures de carte ne le prennent jamais. Risque restant, non traite : le hook d'edition et ce module
ecrivent le meme preambule temporaire ; contenu identique tant que la liste des globales ne change pas.
Gabarits : copies des blocs de outils_docs/EXTENSIONS_TAPP.md (§ 5.2 et 5.3), test_tapp_web.py verifie l'egalite. Le document ne donne
pas le manifeste du gabarit B en entier (« meme forme ») : seul son nom vient de lui.
Banc : test_tapp_web.py.
"""

import json
import os
import re
import sys
import tempfile
import threading
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "berry"))     # gen_tapp vit dans berry/ (exception a la regle du meme dossier)
import gen_tapp  # noqa: E402

DOSSIER = "data/extensions"
MANIFESTE = "manifest.json"
DESTINATION = "/.extensions/{}.tapp"
# 31 caracteres : /.extensions/<nom>.tapp doit tenir dans les 49 d'un chemin Tasmota (xdrv_50_filesystem.ino, UFS_FILENAME_SIZE - 1)
RE_NOM = re.compile(r"[A-Za-z0-9_-]{1,31}")
RESERVES = re.compile(r"(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])", re.I)
CHAMPS = ("name", "version", "description", "min_tasmota")
VERROU = threading.Lock()

_MANIFESTE_A = r"""{
  "name": "Reception FS MQTT",
  "version": "0x1B0B0700",
  "description": "Charge le module solidifie fsMqtt sur une carte dont l'autoexec ne le charge pas",
  "min_tasmota": "0x0F010001"
}
"""
_AUTOEXEC_A = r"""# Extension sans .be embarque : le module est solidifie dans le firmware, l'extension ne fait que le charger.
# Differe apres /autoexec.be : le prologue de demarrage.be pose LOG_LEVEL_* et le persist dont logFonctions a besoin.
do
  tasmota.set_timer(1000, def ()
    import logFonctions
    try
      import fsMqtt
      logFonctions.log("EXT_FSMQTT: module charge par l'extension !", LOG_LEVEL_INFO)
    except .. as e, m
      logFonctions.log(f"EXT_FSMQTT_ERREUR: chargement impossible : {e} - {m} !", LOG_LEVEL_ERREUR)
    end
  end)
end
"""
_MANIFESTE_B = r"""{
  "name": "Mon extension",
  "version": "0x1B0B0700",
  "description": "Un driver, une commande et une regle, retires par unload()",
  "min_tasmota": "0x0F010001"
}
"""
_MODULE_B = r"""# Gabarit d'extension : un driver, une commande, une regle, tous retires par unload().
class Mon_ext
  static var REGLE = "mon_ext_connecte"

  def init()
    tasmota.add_driver(self)
    tasmota.add_cmd("MonExt", / cmd, idx, payload, payload_json -> self.commande(payload))
    tasmota.add_rule("Mqtt#Connected", /-> self.connecte(), self.REGLE)
  end

  def commande(payload)
    tasmota.resp_cmnd(f'{{"MonExt":"{payload}"}}')
  end

  def connecte()
    import logFonctions
    logFonctions.log("MON_EXT: MQTT connecte !", LOG_LEVEL_INFO)
  end

  def every_second()
    # appele par add_driver ; pas d'info ici (charte, regle 4)
  end

  # Appele par tasmota.unload_extension : retire TOUT ce qui a ete enregistre (rien ne l'est a ta place).
  def unload()
    tasmota.remove_cmd("MonExt")
    tasmota.remove_rule("Mqtt#Connected", self.REGLE)
    tasmota.remove_driver(self)
  end
end

return Mon_ext()
"""
_AUTOEXEC_B = r"""do                                      # pas de globale ajoutee
  import introspect
  var mon_ext = introspect.module('mon_ext', true)    # charge depuis l'archive, sans cache
  tasmota.add_extension(mon_ext)                      # chemin = tasmota.wd, valide pendant ce chargement seulement
end
"""
GABARITS = {
    "A": {"libelle": "Charger un module déjà dans le firmware",
          "explication": "Le plus simple : l'extension charge un module solidifié (fsMqtt dans le modèle). /ext l'affiche « Stopped » et ne peut pas l'arrêter.",
          "fichiers": {MANIFESTE: _MANIFESTE_A, "autoexec.be": _AUTOEXEC_A}},
    "B": {"libelle": "Module embarqué, arrêt possible",
          "explication": "L'archive porte son module : un driver, une commande, une règle, tous retirés par unload(). Run et Stop marchent dans /ext.",
          "fichiers": {MANIFESTE: _MANIFESTE_B, "mon_ext.be": _MODULE_B, "autoexec.be": _AUTOEXEC_B}},
}


def _base(racine):
    return (Path(racine) / DOSSIER).resolve()


def dossier(racine, nom):
    """Dossier source d'un nom valide (pas forcement existant) ; ValueError sinon. Le seul passage d'un nom venu du client."""
    if not isinstance(nom, str) or not RE_NOM.fullmatch(nom):
        raise ValueError("nom : 1 a 31 lettres sans accent, chiffres, - ou _ (le chemin sur la carte, /.extensions/<nom>.tapp, "
                         "ne doit pas depasser les 49 caracteres de Tasmota)")
    if RESERVES.fullmatch(nom):
        raise ValueError(f"nom : {nom} est reserve par Windows, en choisir un autre")
    base = _base(racine)
    cible = (base / nom).resolve()
    if cible.parent != base:                # jonction ou lien pose a la main : on ne suit pas
        raise ValueError(f"nom : {nom} pointe hors de {DOSSIER}")
    return cible


def existant(racine, nom):
    d = dossier(racine, nom)
    if not d.is_dir():
        raise LookupError(f"pas d'extension {nom} dans {DOSSIER}")
    return d


def fichier_tapp(racine, nom):
    return _base(racine) / f"{nom}.tapp"


def _etat_tapp(d, tapp, rel):
    if not tapp.is_file():
        return {"existe": False, "a_jour": False, "taille": 0, "chemin": rel}
    # shortcut: dates et non contenu, comme la consigne « plus ancien que ses sources » ; un git checkout peut donc tromper
    dates = [d.stat().st_mtime_ns]          # le dossier : un fichier supprime ne change que lui
    dates += [e.stat().st_mtime_ns for e in os.scandir(d)]
    return {"existe": True, "a_jour": tapp.stat().st_mtime_ns >= max(dates), "taille": tapp.stat().st_size, "chemin": rel}


def _fiche(racine, nom, d):
    return _etat_tapp(d, fichier_tapp(racine, nom), f"{DOSSIER}/{nom}.tapp")


def liste(racine):
    """{extensions: [{nom, tapp}], ignores: [dossiers au nom refuse]} ; un dossier absent n'est pas une erreur et n'est pas cree."""
    base, extensions, ignores = _base(racine), [], []
    if base.is_dir():
        for e in sorted(os.scandir(base), key=lambda x: x.name):
            if not e.is_dir():
                continue
            try:
                extensions.append({"nom": e.name, "tapp": _fiche(racine, e.name, dossier(racine, e.name))})
            except ValueError:
                ignores.append(e.name)
    return {"extensions": extensions, "ignores": ignores}


def detail(racine, nom):
    d = existant(racine, nom)
    fichiers = [{"nom": e.name, "taille": e.stat().st_size, "dossier": e.is_dir()} for e in sorted(os.scandir(d), key=lambda x: x.name)]
    champs, erreur = {c: "" for c in CHAMPS}, ""
    chemin = d / MANIFESTE
    if chemin.is_file():
        try:
            lu = json.loads(chemin.read_text(encoding="utf-8"))
            if not isinstance(lu, dict):
                raise ValueError("un objet JSON est attendu")
            champs.update({c: str(lu[c]) for c in CHAMPS if lu.get(c) is not None})
        except (OSError, ValueError) as e:
            erreur = f"{MANIFESTE} illisible : {e}. Le corriger dans VS Code."
    else:
        erreur = f"{MANIFESTE} absent : remplir le formulaire pour le créer."
    return {"nom": nom, "chemin": f"{DOSSIER}/{nom}", "fichiers": fichiers, "manifeste": champs, "manifeste_erreur": erreur,
            "tapp": _fiche(racine, nom, d), "destination": DESTINATION.format(nom)}


def cree(racine, nom, gabarit):
    d = dossier(racine, nom)
    if not isinstance(gabarit, str) or gabarit not in GABARITS:
        raise ValueError("gabarit : A ou B attendu")
    with VERROU:
        d.parent.mkdir(parents=True, exist_ok=True)
        if fichier_tapp(racine, nom).exists():
            raise RuntimeError(f"{nom}.tapp existe deja dans {DOSSIER} : la fabrication l'ecraserait, choisir un autre nom")
        try:
            os.mkdir(d)
        except FileExistsError:
            raise RuntimeError(f"{nom} existe deja dans {DOSSIER} : rien n'est ecrase, choisir un autre nom") from None
        for f, texte in GABARITS[gabarit]["fichiers"].items():
            (d / f).write_bytes(texte.encode("utf-8"))
    return detail(racine, nom)


def ecrit_manifeste(racine, nom, champs):
    """Ecrit les 4 champs du formulaire dans manifest.json, cles inconnues conservees, atomiquement ; ValueError : fichier intact."""
    d = existant(racine, nom)
    chemin = d / MANIFESTE
    with VERROU:
        existant_lu = {}
        if chemin.is_file():
            try:
                existant_lu = json.loads(chemin.read_text(encoding="utf-8"))
                if not isinstance(existant_lu, dict):
                    raise ValueError("un objet JSON est attendu")
            except ValueError as e:
                raise ValueError(f"{MANIFESTE} illisible ({e}) : le corriger dans VS Code, le formulaire ne l'ecrase pas") from None
        nouveau = dict(existant_lu)
        for c in CHAMPS:
            nouveau[c] = champs.get(c)
        if not isinstance(nouveau["description"], str):
            raise ValueError("description : texte attendu")
        gen_tapp.controle_manifeste(nouveau)
        # temporaire a cote du dossier source : un arret brutal n'en laisse pas dans l'archive
        fd, tmp = tempfile.mkstemp(suffix=".tmp", prefix=nom, dir=d.parent)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write((json.dumps(nouveau, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            os.replace(tmp, chemin)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    return detail(racine, nom)


def verifie(racine, nom):
    """Le verdict point par point, sans rien fabriquer."""
    d = existant(racine, nom)
    with VERROU:
        points, avertissements = gen_tapp.controle(d)
    return {"points": points, "avertissements": avertissements, "bon": all(p["motif"] is None for p in points)}


def fabrique(racine, nom):
    """Ecrit <nom>.tapp a cote du dossier ; ValueError (motif) : rien d'ecrit, l'ancien .tapp reste."""
    d = existant(racine, nom)
    with VERROU:
        gen_tapp.construit(d)
        avertissements = list(gen_tapp.AVERTISSEMENTS)
    return {"tapp": _fiche(racine, nom, d), "avertissements": avertissements}


def archive(racine, nom):
    """Octets du .tapp a envoyer ; RuntimeError si absent ou plus ancien que ses sources. os.replace de gen_tapp : lecture sans verrou."""
    d = existant(racine, nom)
    etat = _fiche(racine, nom, d)
    if not etat["existe"]:
        raise RuntimeError(f"{nom}.tapp n'existe pas : Fabriquer d'abord")
    if not etat["a_jour"]:
        raise RuntimeError(f"{nom}.tapp est plus ancien que ses sources : Fabriquer d'abord")
    return fichier_tapp(racine, nom).read_bytes()
