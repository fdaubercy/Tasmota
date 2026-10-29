"""Environnements PlatformIO de la page Build et televersement : liste, classement, port COM, IP OTA.

Lecture des sections `env:*` de platformio_tasmota_env32.ini, platformio_tasmota_env.ini,
platformio_tasmota_cenv.ini et platformio_override.ini (configparser SANS l'interpolation de
PlatformIO : `extends` est resolu a la main). L'ecriture du port COM reecrit le fichier ligne a
ligne, pour garder commentaires et alignement ; elle ne touche que platformio_tasmota_cenv.ini.
Aucun appel a pio : seuls les fichiers sont lus.
"""

import configparser
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

FICHIER_CENV = "platformio_tasmota_cenv.ini"
# Ordre des extra_configs de platformio.ini : une option d'un fichier plus tard l'emporte
FICHIERS_INI = ("platformio_tasmota_env.ini", "platformio_tasmota_env32.ini", "platformio_override.ini",
                FICHIER_CENV)
PRE_SCRIPT = "pre_utilitaires_platformio.py"    # charge par les bases ESP32 : il porte l'OTA
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
    fs_avec_firmware: bool = False   # un upload firmware par cable flashe aussi le FS (voir _fs_avec_firmware)
    fichiers_berry: bool = False     # env propose par la page « Fichiers Berry par env » (ESP32 du cenv)
    ip_source: str = ""              # "h" (WIFI_IP_ADDRESS) | "maitre" (esclave joint par le range extender) | ""


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
            if nom.startswith("env:"):
                toutes.setdefault(nom, {}).update(cp.items(nom))     # fusion option par option
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


def _ota(toutes, chaine, vus=()):
    """Vrai si les extra_scripts resolus de l'env chargent le pre-script (les ESP8266 non)."""
    for nom in chaine:
        valeur = toutes[nom].get("extra_scripts") or ""
        if not valeur.strip():
            continue
        if PRE_SCRIPT in valeur:
            return True
        for ref in re.findall(r"\$\{(env:[^.}]+)\.extra_scripts\}", valeur):
            if ref not in vus and ref in toutes and _ota(toutes, _chaine(toutes, ref), vus + (nom,)):
                return True
        return False       # la premiere section qui definit extra_scripts l'emporte
    return False


def _firmware(toutes, chaine):
    for nom in chaine:
        trouves = re.findall(r"-D\s*(FIRMWARE_\w+)", toutes[nom].get("build_flags") or "")
        if trouves:
            return trouves[-1]
    return ""


def _valeur(toutes, section, option, vus=()):
    """Option resolue comme PlatformIO : premiere section de la chaine `extends` qui la definit, puis
    substitution des references `${env:X.option}` (resolues de meme). "" si absente ou en boucle."""
    if section in vus:
        return ""
    brut = next((toutes[nom][option] for nom in _chaine(toutes, section) if option in toutes[nom]), None)
    if brut is None:
        return ""
    return re.sub(r"\$\{(env:[^.}]+)\.([^}]+)\}",
                  lambda m: _valeur(toutes, m.group(1), m.group(2), vus + (section,)), brut or "")


def _fs_avec_firmware(toutes, section, ota):
    """Vrai si un `-t upload` par cable flashe aussi le file system de cet env.

    Fait mesure dans pio-tools/post_esp32.py : a chaque edition des liens du firmware (toujours, puisque
    CFG_HOLDER change a chaque run), esp32_build_filesystem (l.139-245) reconstruit littlefs.bin des que
    custom_files_upload contient une entree autre que `no_files`, et l'upload esptool l'emporte
    (l.419-440). ESP32 seulement (`ota` : env qui charge le pre-script des bases ESP32) ; les ESP8266
    n'ont pas post_esp32.py.
    """
    if not ota:
        return False
    lignes = [l.strip() for l in _valeur(toutes, section, "custom_files_upload").splitlines()]
    return any(l and not l.startswith((";", "#")) and "no_files" not in l for l in lignes)


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
        ota = _ota(toutes, chaine)
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
        # Un safeboot de l'amont charge le pre-script (extends tasmota32_base) mais c'est l'image de secours
        # de la partition safeboot, pas un firmware a pousser par /u2 a la place de l'appli : pas d'OTA.
        ota_possible = ota and sous_groupe != "safeboot"
        ip, source = lit_ip_ota(texte_h, firmware), "h"
        if not ip and famille == "cartes" and ota_possible:
            ip, source = adresse_par_maitre(persist_carte(racine, nom)), "maitre"
        envs.append(Env(nom, famille, sous_groupe, port, herite, ip,
                        ota_possible, firmware, ecrivable, _fs_avec_firmware(toutes, section, ota),
                        ecrivable and any(s.startswith("env:tasmota32") for s in chaine),   # regle de envs_proposes
                        source if ip else ""))
    return envs


def adresse_par_maitre(persist):
    """`<ipMaitre>:<8080 + id - 1>` pour un esclave du range extender du maitre, "" sinon.

    Le maitre redirige ce port vers l'esclave:80 (RgxPort, routagePort de discoveryFonctions) ; son propre
    bloc a id 0 et pas d'ipMaitre. Un persist illisible ne donne pas d'adresse : l'IP reste a saisir.
    """
    try:
        bloc = json.loads(Path(persist).read_text(encoding="utf-8"))["serveur"]["rangeExtender"] if persist else {}
        ident, maitre = int(bloc.get("id") or 0), str(bloc.get("ipMaitre") or "")
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return ""
    if str(bloc.get("activation", "")).upper() != "ON" or ident < 1 or not maitre:
        return ""
    return f"{maitre}:{8080 + ident - 1}"


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
        while apres + 1 < fin and re.match(r"[ 	]+\S", lignes[apres + 1]):   # lignes de continuation
            apres += 1
        if not lignes[apres].endswith(("\n", "\r")):
            lignes[apres] += eol
        lignes.insert(apres + 1, f"upload_port             = {port}{eol}")
    shutil.copyfile(chemin, chemin.with_name(chemin.name + ".bak"))
    chemin.write_bytes("".join(lignes).encode("utf-8"))


FICHIER_OVERRIDE = "platformio_override.ini"


def ecrit_data_dir(racine, env):
    """Pose `data_dir` (section [platformio] de platformio_override.ini) sur le dossier de l'env, AVANT son pio run.

    PlatformIO lit ce fichier au demarrage, avant le pre-script qui le reecrit : sans cela, un buildfs lance seul
    prend le dossier de l'env du lancement precedent (P4 avec le FS de la cuve le 2026-10-26). Le pre-script pose
    aussi PROJECT_DATA_DIR pour le lancement en cours (build/test_data_dir.py) : ceci couvre en plus l'empreinte du
    projet et le cas d'un pre-script absent. Envs personnels (« Mes cartes ») seulement ; la ligne active existante
    est reecrite (commentaire et fin de ligne gardes), aucune n'est ajoutee. Rend le dossier pose, None sinon.
    """
    import fichiers_berry_etat                        # ici : fichiers_berry_ini importe build_envs (cycle)

    racine = Path(racine)
    if not any(e.nom == env and e.famille == "cartes" for e in liste_envs(racine)):
        return None
    try:
        dossier = fichiers_berry_etat.dossier_carte(env)
    except ValueError:                                  # nom sans tiret : pas de dossier de carte
        return None
    chemin = racine / FICHIER_OVERRIDE
    if not dossier or not chemin.is_file():
        return None
    lignes = chemin.read_bytes().decode("utf-8").splitlines(keepends=True)
    dans = False
    for i, ligne in enumerate(lignes):
        s = ligne.strip()
        if s.startswith("["):
            dans = s == "[platformio]"
            continue
        m = re.match(r"(data_dir\s*=\s*)([^\s;#]*)(.*)$", ligne, re.S) if dans else None
        if m:
            if m.group(2) == dossier:
                return None
            lignes[i] = m.group(1) + dossier + m.group(3)
            chemin.write_bytes("".join(lignes).encode("utf-8"))
            return dossier
    return None


def persist_carte(racine, env):
    """_persist.json de l'env au depot (data/<lieu>/<carte>/), None pour une base, un env sans tiret ou sans fichier."""
    import fichiers_berry_etat                        # ici : fichiers_berry_ini importe build_envs (cycle)

    try:
        dossier = fichiers_berry_etat.dossier_carte(env)
    except ValueError:
        return None
    chemin = Path(racine) / dossier / "_persist.json" if dossier else None
    return chemin if chemin and chemin.is_file() else None


def topic_carte(racine, env):
    """serveur.mqtt.topic du persist de l'env au depot (transport MQTT de l'onglet Fichiers) ; RuntimeError sinon."""
    chemin = persist_carte(racine, env)
    try:
        topic = (json.loads(chemin.read_text(encoding="utf-8")).get("serveur") or {}).get("mqtt", {}).get("topic") if chemin else None
    except (OSError, ValueError, AttributeError):
        topic = None
    if not topic:
        raise RuntimeError(f"Connexion MQTT : pas de serveur.mqtt.topic dans le persist de {env} au dépôt ; rien n'a été envoyé")
    return topic
