"""Atelier des graphiques : liste des fichiers a televerser apres une ecriture, et lien vers la page Build (A6, spec §5, §7).

`etat_avant` se prend AVANT l'ecriture, `plan` APRES. Rien n'est ecrit ni envoye : la seule requete de carte est
`Br path.exists(...)` (lecture) et la seule requete locale une sonde TCP du port 7700.

Noms de fichiers = ceux de l'image du FS que liste la page Build (`build_fichiers.py::liste`) :
data/fs/X -> X, data/sd/Y -> sd/Y, fichier du dossier de la carte -> son nom (ex. pages_graphiques.json, autoexec.be).
"""

import json
import socket
import urllib.parse
from pathlib import Path

import atelier_graphiques_ecriture as age
import atelier_graphiques_series as ags
import fichiers_berry_etat as fbe
import fichiers_berry_ini as fbi

PORT_BUILD = 7700
URL_BUILD = f"http://127.0.0.1:{PORT_BUILD}/"
MESSAGE_BUILD = "La page Build ne repond pas : lancer la page Build par l'annuaire (http://127.0.0.1:7600), puis cliquer de nouveau."


def nom_fs(rel):
    """Nom dans le FS de la carte d'un fichier du depot sous data/fs ou data/sd."""
    rel = rel.replace("\\", "/")
    for prefixe, garde in (("data/fs/", ""), ("data/sd/", "sd/")):
        if rel.startswith(prefixe):
            return garde + rel[len(prefixe):]
    raise ValueError(f"fichier hors data/fs et data/sd : {rel!r}")


def _exclus(racine, env):
    return {Path(x.chemin).name for x in fbi.resout(fbi.lit_sections(racine), env, fbe.EXCLUDE)}


def _index(racine, env):
    chemin = Path(racine) / fbe.dossier_carte(env) / age.DESCRIPTION
    try:
        pages = json.loads(chemin.read_text(encoding="utf-8")).get("pages") or []
        return [(p.get("id"), p.get("titre"), p.get("acces", "bouton")) for p in pages]
    except (OSError, ValueError, AttributeError):
        return []


def etat_avant(racine, env):
    return {"exclus": _exclus(racine, env), "index": _index(racine, env)}


def existe_sur_carte(ip, fs, get):
    """True / False ; OSError / ValueError si la carte ne repond pas ou repond autre chose."""
    cmnd = urllib.parse.quote(f'Br import path path.exists("/{fs}")', safe="")
    reponse = json.loads(get(ip, "/cm?cmnd=" + cmnd, ags.DELAI).decode("utf-8", "replace")).get("Br")
    if str(reponse).lower() not in ("true", "false"):
        raise ValueError(f"reponse inattendue : {reponse!r}")
    return str(reponse).lower() == "true"


def build_actif(port=PORT_BUILD):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def url(env, fichiers, redemarrer):
    q = urllib.parse.urlencode({"env": env, "depuis": "atelier", "fichiers": ",".join(fichiers), "redemarrer": int(redemarrer)})
    return URL_BUILD + "?" + q


def plan(racine, env, destination, ecrits, avant, *, get, sonde=build_actif):
    """{fichiers, redemarrer, verification: carte|hors_ligne, notes, url, build_actif, message}. `ecrits` : chemins du depot."""
    racine, dossier = Path(racine), fbe.dossier_carte(env)
    ecrits = [e.replace("\\", "/") for e in ecrits]
    fichiers, notes = [], []
    for rel in ecrits:                                  # description, autoexec : fichiers du dossier de la carte qui existent encore
        if rel.startswith(dossier + "/") and (racine / rel).is_file():
            fichiers.append(rel[len(dossier) + 1:])
    moteur = age.MOTEUR_FICHIERS if destination == "graphiques" else age.FICHIERS_MOTEUR
    if destination == "graphiques" or (racine / dossier / age.DESCRIPTION).is_file():
        apres_exclus = _exclus(racine, env)
        ip = ags._carte(racine, env)[0]
        verifie = bool(ip)
        for rel in moteur:
            nom = Path(rel).name
            if nom in apres_exclus:
                continue                                # l'env ne l'embarque pas : rien a envoyer
            fs = nom_fs(rel)
            if nom in avant["exclus"]:
                fichiers.append(fs)                     # vient d'entrer dans le FS de l'env
            elif verifie:
                try:
                    if not existe_sur_carte(ip, fs, get):
                        fichiers.append(fs)
                except (OSError, ValueError):           # HTTPException est une OSError ; le reste = hors ligne
                    verifie = False
        if not verifie:
            notes.append("carte hors ligne ou adresse inconnue : presence des fichiers du moteur non verifiee"
                         " (seuls ceux qui entrent dans le FS de l'env sont listes)")
        verification = "carte" if verifie else "hors_ligne"
    else:
        verification = "carte"
    fichiers = list(dict.fromkeys(fichiers))
    redemarrer = int(dossier + "/autoexec.be" in ecrits or _index(racine, env) != avant["index"])
    actif = sonde()
    return {"fichiers": fichiers, "redemarrer": redemarrer, "verification": verification, "notes": notes,
            "url": url(env, fichiers, redemarrer), "build_actif": actif, "message": "" if actif else MESSAGE_BUILD}
