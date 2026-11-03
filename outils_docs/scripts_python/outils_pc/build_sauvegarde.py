"""Onglet « Sauvegarde configuration » de la page build (plan sauvegarde-config-cartes, 2026-11-03).

Une sauvegarde est le /dl d'une carte (settings.ino::SettingsConfigBackup : Settings + fichiers .drvset*), rangee dans
outils_docs/sauvegardes_cartes/<env>/AAAAMMJJ-HHMMSS_<origine>.dmp avec sa fiche .json. Le dossier est ignore par git :
un .dmp porte les mots de passe Wi-Fi et MQTT en clair, et le depot est public.

  prend        /dl de la carte (esclave `IP:port` : redirection du maitre posee et identite verifiee d'abord ;
               `mqtt://<topic>` : par le broker, build_sauvegarde_mqtt) ; une prise automatique lance `purge`
  liste        sauvegardes d'un env, de la plus recente a la plus ancienne
  parametres   parametres d'une sauvegarde par groupe decode-config, mots de passe remplaces par ***
  copie        nouvelle sauvegarde « modifiee » ; l'originale n'est jamais reecrite (decode_config.ecrit_copie)
  compare      ecarts entre deux sauvegardes, ou entre une sauvegarde et la carte en ligne
  restaure     sauvegarde « avant restauration », puis /rs + /u2, retour de la carte, ecarts relus
  supprime     sauvegardes choisies effacees (.dmp et fiche) ; tous les noms controles avant d'en effacer un
  purge        sauvegardes automatiques (avant flash, avant restauration) de plus de GARDE_JOURS au-dela des
               GARDE_NOMBRE plus recentes de chaque origine ; jamais une manuelle ni une modifiee. Seulement si la
               case « purge automatique » de l'onglet est cochee (REGLAGES, cochee par defaut)
Le persist et l'autoexec.bat reposent leurs reglages a chaque demarrage : ils l'emportent sur une valeur restauree ;
`reposes` dit lesquels, pour les marquer dans la page.
Banc : test_build_sauvegarde.py.
"""

import base64
import hashlib
import http.client
import json
import re
import tempfile
import time
from pathlib import Path

import build_envs
import build_sauvegarde_mqtt
import decode_config
from build_ota_http import _attend_retour, _get, _page_en_echec, _poste
from build_ota_maitre import joint_par_maitre

DOSSIER = Path("outils_docs") / "sauvegardes_cartes"
ORIGINES = {"manuelle": "manuelle", "avant-flash": "avant flash", "avant-restauration": "avant restauration",
            "modifiee": "modifiée"}
NOM = re.compile(r"\d{8}-\d{6}_(" + "|".join(ORIGINES) + r")\.dmp")
ENV = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*")       # ni "." ni ".." : rien hors de sauvegardes_cartes/
SECRET = re.compile(r"pwd|password|pwassword|token|precfgkey")   # sta_pwd, rgx_pwassword_esp32, zb_precfgkey_l...
MASQUE = "***"
NON_EDITABLES = ("header", "settings", "config_version")
PLATEFORME = 0xF36                   # Settings->config_version : ESP32, S3, P4... (settings.ino::SettingsConfigRestore)
DELAI = 20.0
MQTT = "mqtt://"                     # adresse « mqtt://<topic> » : la carte est jointe par le broker
AUTOMATIQUES = ("avant-flash", "avant-restauration")
GARDE_NOMBRE, GARDE_JOURS = 5, 90
CONFIG_PERSIST = Path("data") / "fs" / "configGlobal.be"   # applique le persist au demarrage (testeParam, tasmota.cmd)
SANS_COMMANDE = {"adc_param32": ["ADCPARAM"], "adc_param": ["ADCPARAM"]}   # decode-config ne leur donne pas de commande
REGLAGES = DOSSIER / "reglages.json"   # {"purge_auto": bool}, commun a toutes les cartes
ETAPES = ("Sauvegarde « avant restauration » de la carte", "Envoi de la configuration",
          "Redémarrage de la carte, attente de son retour", "Relecture et comparaison des écarts")
EN_COURS = {}                        # env -> {etape, etapes, debut} pendant une restauration, lu par la page
_CACHE = {}                          # (chemin, date) -> parametres decodes : decode-config prend 5 a 10 s


def dossier(racine, env):
    if not ENV.fullmatch(env or ""):
        raise ValueError("nom d'env invalide")
    return Path(racine) / DOSSIER / env


def _chemin(racine, env, fichier):
    if not NOM.fullmatch(fichier or ""):
        raise ValueError("nom de sauvegarde invalide")
    chemin = dossier(racine, env) / fichier
    if not chemin.is_file():
        raise ValueError(f"sauvegarde absente : {fichier}")
    return chemin


def _fiche(chemin, donnees, origine, adresse, source=""):
    v = decode_config.version(donnees)
    n = chemin.name                  # AAAAMMJJ-HHMMSS_<origine>.dmp : la date de la prise, pas celle du fichier
    fiche = {"fichier": n, "date": f"{n[6:8]}/{n[4:6]}/{n[:4]} {n[9:11]}:{n[11:13]}",
             "version": decode_config.nom_version(v), "editable": decode_config.editable(v), "origine": ORIGINES[origine],
             "adresse": adresse, "taille": len(donnees), "source": source}
    chemin.with_suffix(".json").write_text(json.dumps(fiche, ensure_ascii=False, indent=1), encoding="utf-8")
    return fiche


def _nouveau(racine, env, origine):
    d = dossier(racine, env)
    d.mkdir(parents=True, exist_ok=True)
    while True:                      # deux sauvegardes dans la meme seconde (manuelle puis avant restauration)
        chemin = d / f"{time.strftime('%Y%m%d-%H%M%S')}_{origine}.dmp"
        if not chemin.exists():
            return chemin
        time.sleep(1)


def _mqtt():
    """(client non connecte, MqttPassword de la carte) : broker et mot de passe de user_config_override.h."""
    import build_ota_mqtt
    import sniffeur_mqtt
    return build_ota_mqtt.client_par_defaut(), sniffeur_mqtt.lit_config_broker().get("MQTT_PASS", "")


def lit_carte(adresse, env, persist_env, joint=None):
    """/dl de la carte (bytes) ; RuntimeError si la reponse n'est pas une configuration."""
    if adresse.startswith(MQTT):
        client, mot_de_passe = _mqtt()
        donnees = build_sauvegarde_mqtt.lit(client, adresse[len(MQTT):], mot_de_passe)
    else:
        if ":" in adresse:           # esclave joint par le maitre
            (joint or joint_par_maitre)(adresse, persist_env, env, lambda _: None)
        donnees = _get(adresse, "/dl", DELAI)
    if len(donnees) < 4096 or not decode_config.crc_valide(donnees):
        raise RuntimeError(f"la carte {adresse} n'a pas rendu de configuration par /dl ({len(donnees)} o)")
    return donnees


def prend(racine, env, adresse, origine, persist_env=None, joint=None):
    donnees = lit_carte(adresse, env, persist_env, joint)
    chemin = _nouveau(racine, env, origine)
    chemin.write_bytes(donnees)
    fiche = _fiche(chemin, donnees, origine, adresse)
    if origine in AUTOMATIQUES and purge_auto(racine):
        try:
            purge(racine, env)
        except (OSError, ValueError):
            pass                     # la sauvegarde est prise ; une purge manquee attendra la suivante
    return fiche


def liste(racine, env):
    fiches = []
    for chemin in sorted(dossier(racine, env).glob("*.dmp"), reverse=True):
        try:
            fiches.append(json.loads(chemin.with_suffix(".json").read_text(encoding="utf-8")))
        except (OSError, ValueError):
            fiches.append({"fichier": chemin.name, "origine": "?", "version": "?", "editable": False})
    return [f for f in fiches if NOM.fullmatch(f.get("fichier", ""))]


def commande(mot):
    """Nom normalise d'une commande Tasmota, comme decode_config_groupes : SO56/SetOption56 -> SETOPTION56, Timer3 -> TIMER."""
    m = re.fullmatch(r"([A-Za-z_]+?)(\d*)", mot)
    if not m:
        return None                  # I2CDriver7, %s... : pas une commande lisible
    nom = "SETOPTION" if m.group(1).upper() == "SO" else m.group(1).upper()
    return nom + m.group(2) if nom == "SETOPTION" else nom


def commandes_lignes(texte):
    """{commande normalisee: telle qu'ecrite} des lignes d'un autoexec.bat (Backlog compris, ; = commentaire en tete)."""
    noms = {}
    for ligne in texte.splitlines():
        if ligne.strip().startswith(";"):
            continue
        for partie in ligne.split(";"):
            mots = partie.split()
            if mots and re.fullmatch(r"backlog\d*", mots[0], re.I):
                mots = mots[1:]
            if mots and (n := commande(mots[0])):
                noms.setdefault(n, mots[0])
    return noms


def commandes_persist(texte):
    """Commandes que configGlobal.be pose depuis le persist : testeParam("X"...), tasmota.cmd("X ..."), ["MqttHost", "hote"]."""
    textes = re.findall(r'(?:testeParam|tasmota\.cmd)\((?:string\.format\()?"([^"]*)"', texte)
    textes += re.findall(r'\[\s*"([A-Z]\w*)",\s*"\w+"\s*\]', texte)
    return commandes_lignes("\n".join(textes))


def reposes(cles, autoexec, persist, commandes=None):
    """{cle: texte} des parametres qu'une commande de l'autoexec.bat ou du persist repose a chaque demarrage."""
    commandes = commandes if commandes is not None else decode_config.disposition()["commandes"]
    res = {}
    for cle in cles:
        noms = set(commandes.get(cle, [])) | set(SANS_COMMANDE.get(cle, []))
        par = [f"{source} ({', '.join(sorted(lignes[n] for n in noms & set(lignes)))})"
               for source, lignes in (("autoexec.bat", autoexec), ("persist", persist)) if noms & set(lignes)]
        if par:
            res[cle] = "reposé à chaque démarrage par " + " et ".join(par)
    return res


def _demarrage(racine, env):
    """Commandes de l'autoexec.bat de la carte et du persist au depot ; vides pour une base ou un env sans dossier."""
    import fichiers_berry_etat       # ici : fichiers_berry_ini importe build_envs (cycle, comme build_envs.persist_carte)

    try:
        d = fichiers_berry_etat.dossier_carte(env)
    except ValueError:
        d = None
    if not d:
        return {}, {}
    lit = lambda p: p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
    # shortcut: tout configGlobal.be est compte des qu'il y a un persist, meme une cle vide qu'il ne pose pas ;
    # a affiner si une marque trompe
    persist = commandes_persist(lit(Path(racine) / CONFIG_PERSIST)) if (Path(racine) / d / "_persist.json").is_file() else {}
    return commandes_lignes(lit(Path(racine) / d / "autoexec.bat")), persist


def _decode(chemin):
    cle = (str(chemin), chemin.stat().st_mtime_ns)
    if cle not in _CACHE:
        _CACHE[cle] = decode_config.decode(chemin)
    return _CACHE[cle]


def _masque(cle, valeur):
    return MASQUE if SECRET.search(cle) and valeur else valeur


def parametres(racine, env, fichier, groupes=None):
    """{version, editable, groupes: {groupe: {cle: valeur}}, fichiers: {nom: taille}, message}."""
    chemin = _chemin(racine, env, fichier)
    v = decode_config.version(chemin.read_bytes())
    res = {"fichier": fichier, "version": decode_config.nom_version(v), "editable": decode_config.editable(v),
           "groupes": {}, "fichiers": {}, "reposes": {}, "message": ""}
    try:
        valeurs = _decode(chemin)
    except (ValueError, RuntimeError) as erreur:
        res["message"] = str(erreur)
        res["editable"] = False
        return res
    groupes = groupes if groupes is not None else decode_config.groupes()
    for cle, valeur in sorted(valeurs.items()):
        if cle not in NON_EDITABLES:
            g = groupes.get(cle) or "Divers"
            res["groupes"].setdefault("Divers" if g == "*" else g, {})[cle] = _masque(cle, valeur)
    res["fichiers"] = {nom: len(base64.b64decode(d)) for nom, d in (valeurs.get("settings") or {}).items()}
    try:
        res["reposes"] = reposes(valeurs, *_demarrage(racine, env))
    except (OSError, RuntimeError):
        res["reposes"] = {}          # marques seulement : leur echec ne cache pas les parametres
    return res


def copie(racine, env, fichier, modifs):
    """Nouvelle sauvegarde « modifiee » = fichier + modifs ; un mot de passe laisse a *** garde sa valeur."""
    if not isinstance(modifs, dict):
        raise ValueError("modifications attendues sous forme d'objet")
    interdites = sorted(set(modifs) & set(NON_EDITABLES))
    if interdites:
        raise ValueError(f"non modifiables ici : {', '.join(interdites)}")
    modifs = {k: v for k, v in modifs.items() if not (SECRET.search(k) and v == MASQUE)}
    if not modifs:
        raise ValueError("aucune modification")
    source = _chemin(racine, env, fichier)
    dest = _nouveau(racine, env, "modifiee")
    decode_config.ecrit_copie(source, dest, modifs)
    return _fiche(dest, dest.read_bytes(), "modifiee", "", source=fichier)


def _ecarts(a, b):
    ecarts = []
    for cle in sorted(set(a) | set(b)):
        if cle in decode_config.NON_COMPARES or a.get(cle) == b.get(cle):
            continue
        if cle == "settings":
            for nom in sorted(set(a.get(cle) or {}) | set(b.get(cle) or {})):
                if (a.get(cle) or {}).get(nom) != (b.get(cle) or {}).get(nom):
                    ecarts.append({"cle": nom, "a": "…", "b": "…"})
            continue
        ecarts.append({"cle": cle, "a": _masque(cle, a.get(cle)), "b": _masque(cle, b.get(cle))})
    return ecarts


def compare(racine, env, fichier, autre="", adresse="", persist_env=None, joint=None, carte=None):
    """Ecarts de `fichier` a `autre` (sauvegarde) ou a la carte en ligne (`adresse`, /dl jamais enregistre ;
    `carte` : ce /dl deja lu)."""
    a = _decode(_chemin(racine, env, fichier))
    if autre:
        return {"ecarts": _ecarts(a, _decode(_chemin(racine, env, autre)))}
    donnees = carte or lit_carte(adresse, env, persist_env, joint)
    with tempfile.TemporaryDirectory() as t:
        carte = Path(t) / "carte.dmp"
        carte.write_bytes(donnees)
        return {"ecarts": _ecarts(a, decode_config.decode(carte))}


def empreinte(racine, env, fichier):
    return hashlib.sha256(_chemin(racine, env, fichier).read_bytes()).hexdigest()[:16]


def restaure(racine, env, fichier, adresse, jeton, persist_env=None, joint=None,
             retour=(120.0, 8.0, 2.0)):
    """Restaure `fichier` sur la carte. Une sauvegarde « avant restauration » est prise d'abord ; `jeton` =
    empreinte(fichier) lue avec les ecarts confirmes par l'utilisateur. -> {avant, ecarts} (ecarts relus apres)."""
    chemin = _chemin(racine, env, fichier)
    donnees = chemin.read_bytes()
    if jeton != empreinte(racine, env, fichier):
        raise RuntimeError("la sauvegarde a changé depuis la confirmation : relire les écarts")
    try:
        return _restaure(racine, env, chemin, donnees, adresse, persist_env, joint, retour)
    finally:
        EN_COURS.pop(env, None)


def _etape(env, numero):
    EN_COURS[env] = {"etape": numero, "etapes": ETAPES, "debut": EN_COURS.get(env, {}).get("debut", time.time())}


def _restaure(racine, env, chemin, donnees, adresse, persist_env, joint, retour):
    fichier = chemin.name
    _etape(env, 0)
    avant = prend(racine, env, adresse, "avant-restauration", persist_env, joint)
    if decode_config.settings(donnees)[PLATEFORME] != decode_config.settings(
            (dossier(racine, env) / avant["fichier"]).read_bytes())[PLATEFORME]:
        raise RuntimeError("sauvegarde d'une autre puce (ESP32, S3, P4...) que la carte : rien n'est envoyé")
    relue = None
    _etape(env, 1)
    try:
        if adresse.startswith(MQTT):
            client, mot_de_passe = _mqtt()
            build_sauvegarde_mqtt.ecrit(client, adresse[len(MQTT):], mot_de_passe, donnees, chemin.name)
            _etape(env, 2)
            relue = _attend_retour_mqtt(adresse, env, retour)
        else:
            _get(adresse, "/rs?", DELAI)     # page de restauration : prepare l'envoi de configuration (UPL_SETTINGS)
            try:
                statut, texte = _poste(adresse, "/u2", "u2", chemin.name, donnees, DELAI)
            except (OSError, http.client.HTTPException):
                statut, texte = 200, ""      # coupee en redemarrant : la relecture apres le retour juge
            if _page_en_echec(statut, texte):
                raise RuntimeError(f"la carte a refusé la configuration (HTTP {statut})")
            _etape(env, 2)
            _attend_retour(adresse, retour[0], retour[1], retour[2], 5.0)
    except RuntimeError as erreur:
        raise RuntimeError(f"{erreur} ; sauvegarde d'avant : {avant['fichier']}") from None
    ecarts = []
    _etape(env, 3)
    try:
        ecarts = compare(racine, env, fichier, adresse=adresse, persist_env=persist_env, joint=joint, carte=relue)["ecarts"]
    except (ValueError, RuntimeError, OSError):
        pass                         # version non lisible : la restauration est faite, les ecarts ne sont pas relus
    return {"avant": avant, "ecarts": ecarts}


def _attend_retour_mqtt(adresse, env, retour):
    """Configuration relue par le broker apres le redemarrage (retour = delai total, attente avant, intervalle)."""
    fin = time.monotonic() + retour[0]
    time.sleep(retour[1])
    while True:
        try:
            return lit_carte(adresse, env, None)
        except (RuntimeError, OSError) as erreur:
            if time.monotonic() > fin:
                raise RuntimeError(f"la carte n'est pas revenue sur le broker en {retour[0]:.0f} s ({erreur})") from None
        time.sleep(retour[2])


def supprime(racine, env, fichiers):
    """Efface les sauvegardes `fichiers` (.dmp et fiche .json) -> {supprimees}. Un nom invalide : rien n'est efface."""
    if not isinstance(fichiers, list) or not fichiers:
        raise ValueError("aucune sauvegarde choisie")
    chemins = [_chemin(racine, env, str(f)) for f in dict.fromkeys(fichiers)]
    for chemin in chemins:
        chemin.unlink()
        chemin.with_suffix(".json").unlink(missing_ok=True)
    return {"supprimees": [c.name for c in chemins]}


def purge(racine, env, maintenant=None):
    """Efface les sauvegardes automatiques trop anciennes (voir la docstring du module) -> noms effaces."""
    limite = time.strftime("%Y%m%d-%H%M%S", time.localtime((maintenant or time.time()) - GARDE_JOURS * 86400))
    effacees = []
    for origine in AUTOMATIQUES:
        noms = sorted((p.name for p in dossier(racine, env).glob(f"*_{origine}.dmp") if NOM.fullmatch(p.name)),
                      reverse=True)
        effacees += [n for n in noms[GARDE_NOMBRE:] if n[:15] < limite]
    return supprime(racine, env, effacees)["supprimees"] if effacees else []


def purge_auto(racine):
    try:
        return json.loads((Path(racine) / REGLAGES).read_text(encoding="utf-8")).get("purge_auto", True) is not False
    except (OSError, ValueError, AttributeError):
        return True                  # case jamais touchee, ou fichier illisible : la purge reste active


def pose_purge_auto(racine, valeur):
    if not isinstance(valeur, bool):
        raise ValueError("purge_auto attendu : vrai ou faux")
    chemin = Path(racine) / REGLAGES
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps({"purge_auto": valeur}), encoding="utf-8")
    return {"purge_auto": valeur}


def liste_json(racine, env):
    """Sauvegardes de l'env, reglage de purge, et l'etape d'une restauration en cours (relue par la page)."""
    return {"sauvegardes": liste(racine, env), "decode_config": decode_config.utilisable(),
            "purge_auto": purge_auto(racine), "restauration": EN_COURS.get(env)}


def parametres_json(racine, env, fichier):
    return dict(parametres(racine, env, fichier), jeton=empreinte(racine, env, fichier))


def traite_post(chemin, demande, serie, racine, verrou, adresse_carte):
    """Routes POST de build_web ; None si `chemin` n'en est pas une. `adresse_carte(demande)` : adresse validee.

      /sauvegarde/prendre    {env, adresse}                  -> fiche de la nouvelle sauvegarde
      /sauvegarde/comparer   {env, fichier, autre | adresse} -> {ecarts, jeton}
      /sauvegarde/copier     {env, fichier, modifs}          -> fiche de la copie modifiee
      /sauvegarde/restaurer  {env, fichier, adresse, jeton}  -> {avant, ecarts}
      /sauvegarde/supprimer  {env, fichiers}                 -> {supprimees}
      /sauvegarde/reglages   {purge_auto}                    -> {purge_auto} (case de l'onglet, toutes les cartes)
    `transport: "mqtt"` dans la demande : la carte est jointe par le broker (topic du persist au depot), pas par `adresse`.
    """
    operations = {"/sauvegarde/prendre", "/sauvegarde/comparer", "/sauvegarde/copier", "/sauvegarde/restaurer",
                  "/sauvegarde/supprimer"}
    if chemin == "/sauvegarde/reglages":
        return pose_purge_auto(racine, demande.get("purge_auto"))
    if chemin not in operations:
        return None
    env, fichier = str(demande.get("env") or ""), str(demande.get("fichier") or "")
    persist = build_envs.persist_carte(racine, env)
    if demande.get("transport") == "mqtt":
        adresse_carte = lambda _: MQTT + build_envs.topic_carte(racine, env)
    if serie.envoi_en_cours() and chemin not in ("/sauvegarde/copier", "/sauvegarde/supprimer"):   # sans la carte
        raise RuntimeError("un envoi est en cours : réessayer après")
    # shortcut: un lancement demarre pendant une restauration n'est pas refuse ; a bloquer si cela arrive
    if not verrou.acquire(blocking=False):
        raise RuntimeError("une autre opération de sauvegarde est en cours")
    try:
        if chemin == "/sauvegarde/prendre":
            return prend(racine, env, adresse_carte(demande), "manuelle", persist)
        if chemin == "/sauvegarde/supprimer":
            return supprime(racine, env, demande.get("fichiers"))
        if chemin == "/sauvegarde/copier":
            return copie(racine, env, fichier, demande.get("modifs"))
        if chemin == "/sauvegarde/comparer":
            autre = str(demande.get("autre") or "")
            res = compare(racine, env, fichier, autre=autre, adresse="" if autre else adresse_carte(demande),
                          persist_env=persist)
            return dict(res, jeton=empreinte(racine, env, fichier))
        return restaure(racine, env, fichier, adresse_carte(demande), str(demande.get("jeton") or ""), persist)
    except (OSError, http.client.HTTPException) as erreur:
        raise RuntimeError(f"carte injoignable : {erreur}") from None
    finally:
        verrou.release()
