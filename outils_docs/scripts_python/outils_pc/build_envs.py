"""Environnements PlatformIO de la page Build et televersement : liste, classement, port COM, IP OTA.

Lecture des sections `env:*` de platformio_tasmota_env32.ini, platformio_tasmota_env.ini,
platformio_tasmota_cenv.ini et platformio_override.ini (configparser SANS l'interpolation de
PlatformIO : `extends` est resolu a la main). L'ecriture du port COM reecrit le fichier ligne a
ligne, pour garder commentaires et alignement ; elle ne touche que platformio_tasmota_cenv.ini.
Aucun appel a pio : seuls les fichiers sont lus.
"""

import configparser
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

FICHIER_CENV = "platformio_tasmota_cenv.ini"
FICHIERS_INI = (FICHIER_CENV, "platformio_tasmota_env32.ini", "platformio_tasmota_env.ini",
                "platformio_override.ini")
BASE_OTA = "env:tasmota32_base"      # son pre-script porte l'OTA ; les ESP8266 n'en heritent pas
ENTETE_ENV = re.compile(r"\[env:([^\]]+)\]")
PORT_VALIDE = re.compile(r"COM\d{1,3}")
LANGUE = re.compile(r"tasmota(?:32)?-[A-Z]{2}")


@dataclass
class Env:
    nom: str
    famille: str          # "cartes" | "bases" | "amont"
    sous_groupe: str      # amont seulement : "safeboot" | "esp32" | "langues" | "esp8266"
    port: str             # upload_port COMn, "" si absent
    port_herite: bool     # le port vient d'un extends
    ip: str               # WIFI_IP_ADDRESS du .h, "" si absente ou 0.0.0.0
    ota_possible: bool
    firmware: str         # dernier -D FIRMWARE_* des build_flags
    ecrivable: bool       # defini dans platformio_tasmota_cenv.ini


def _lit_ini(chemin):
    cp = configparser.ConfigParser(interpolation=None, strict=False, delimiters=("=",),
                                   inline_comment_prefixes=("#", ";"), allow_no_value=True)
    cp.optionxform = str
    cp.read_string(chemin.read_text(encoding="utf-8", errors="ignore"))
    return cp


def _sections(racine):
    """({section: {option: valeur}} tous fichiers confondus, {section: fichier d'origine})."""
    toutes, origine = {}, {}
    for fichier in FICHIERS_INI:
        chemin = racine / fichier
        if not chemin.is_file():
            continue
        cp = _lit_ini(chemin)
        for nom in cp.sections():
            if nom.startswith("env:") and nom not in toutes:
                toutes[nom] = dict(cp.items(nom))
                origine[nom] = fichier
    return toutes, origine


def _chaine(toutes, nom, vus=()):
    """La section puis ses ancetres, dans l'ordre de priorite (la fille d'abord)."""
    if nom in vus or nom not in toutes:
        return []
    res = [nom]
    for parent in (toutes[nom].get("extends") or "").split(","):
        res += [s for s in _chaine(toutes, parent.strip(), vus + (nom,)) if s not in res]
    return res


def _firmware(toutes, chaine):
    for nom in chaine:
        trouves = re.findall(r"-D\s*(FIRMWARE_\w+)", toutes[nom].get("build_flags") or "")
        if trouves:
            return trouves[-1]
    return ""


def _port(toutes, chaine):
    for i, nom in enumerate(chaine):
        valeur = (toutes[nom].get("upload_port") or "").strip()
        if valeur:
            return (valeur if PORT_VALIDE.fullmatch(valeur) else ""), i > 0
    return "", False


def lit_ip_ota(texte_h, firmware):
    """WIFI_IP_ADDRESS du bloc `#if/#elif defined(<firmware>)` ; "" si absente ou 0.0.0.0.

    Meme algorithme que build/ota-files-uploader.py:_lire_ip_override (ce script fait
    Import("env") de SCons : il n'est pas importable).
    """
    if not firmware:
        return ""
    dans_bloc, profondeur = False, 0
    for ligne in texte_h.splitlines():
        s = ligne.strip()
        if not dans_bloc:
            if re.match(r"#\s*(?:el)?if\b", s) and re.search(
                    rf"defined\s*\(\s*{re.escape(firmware)}\s*\)", s):
                dans_bloc, profondeur = True, 0
            continue
        if re.match(r"#\s*(?:ifdef|ifndef|if)\b", s):
            profondeur += 1
        elif re.match(r"#\s*endif\b", s):
            if profondeur == 0:
                break
            profondeur -= 1
        elif re.match(r"#\s*elif\b", s) and profondeur == 0:
            break
        m = re.match(r'#\s*define\s+WIFI_IP_ADDRESS\s+"([\d.]+)"', s)
        if m:
            return "" if m.group(1) == "0.0.0.0" else m.group(1)
    return ""


def liste_envs(racine):
    racine = Path(racine)
    toutes, origine = _sections(racine)
    chemin_h = racine / "tasmota" / "user_config_override.h"
    texte_h = chemin_h.read_text(encoding="utf-8", errors="ignore") if chemin_h.is_file() else ""
    envs = []
    for section in toutes:
        nom = section[4:]
        if nom.endswith("_base"):          # tasmota32_base, tasmota32_idf55_base : pas des cibles
            continue
        chaine = _chaine(toutes, section)
        ota = BASE_OTA in chaine[1:]
        ecrivable = origine[section] == FICHIER_CENV
        sous_groupe = ""
        if ecrivable:
            famille = "bases" if "-base" in nom else "cartes"
        else:
            famille = "amont"
            if "safeboot" in nom:
                sous_groupe = "safeboot"
            elif LANGUE.fullmatch(nom):
                sous_groupe = "langues"
            else:
                sous_groupe = "esp32" if ota else "esp8266"
        port, herite = _port(toutes, chaine)
        firmware = _firmware(toutes, chaine)
        envs.append(Env(nom, famille, sous_groupe, port, herite, lit_ip_ota(texte_h, firmware),
                        ota, firmware, ecrivable))
    return envs


def ecrit_port(racine, env, port):
    """Pose `upload_port = <port>` dans la section de l'env (cenv seulement) ; "" retire la ligne active."""
    if port != "" and not PORT_VALIDE.fullmatch(port):
        raise ValueError(f"port invalide : {port!r} (attendu COMn)")
    chemin = Path(racine) / FICHIER_CENV
    lignes = chemin.read_bytes().decode("utf-8").splitlines(keepends=True)
    debut = next((i for i, l in enumerate(lignes)
                  if (m := ENTETE_ENV.fullmatch(l.strip())) and m.group(1) == env), None)
    if debut is None:
        raise ValueError(f"environnement non ecrivable (absent de {FICHIER_CENV}) : {env!r}")
    fin = next((i for i in range(debut + 1, len(lignes)) if lignes[i].startswith("[")), len(lignes))
    eol = "\r\n" if lignes[debut].endswith("\r\n") else "\n"
    actives = [i for i in range(debut + 1, fin) if re.match(r"upload_port\s*=", lignes[i])]
    if actives:
        i = actives[0]
        if port == "":
            del lignes[i]
        else:
            m = re.match(r"(upload_port\s*=\s*)(\S*)(.*)$", lignes[i], re.S)
            lignes[i] = m.group(1) + port + m.group(3)
    elif port != "":
        apres = next((i for i in range(debut + 1, fin) if re.match(r"extends\s*=", lignes[i])), debut)
        if not lignes[apres].endswith(("\n", "\r")):
            lignes[apres] += eol
        lignes.insert(apres + 1, f"upload_port             = {port}{eol}")
    shutil.copyfile(chemin, chemin.with_name(chemin.name + ".bak"))
    chemin.write_bytes("".join(lignes).encode("utf-8"))
