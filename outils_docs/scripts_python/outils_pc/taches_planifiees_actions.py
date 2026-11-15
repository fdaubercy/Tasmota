"""Route POST /geste de la page « Taches planifiees » (A4) : table des gestes par voie, validation, aiguillage vers taches_planifiees_gestes.

Corps : {"voie": "pc" | "github", "geste": ..., "valeur": ...}. Gestes :
    pc      active, desactive, heure (valeur "HH:MM"), lancer, arreter, envs (valeur = liste des envs EXCLUS)
    github  active, desactive, lancer, arreter, envs_apercu et envs (valeur = liste des envs EXCLUS ; envs ecrit le fichier du depot)
ValueError = 400 (entree invalide), RuntimeError = 409 (refus : build en cours, tache absente, GitHub injoignable...).
Tout ce qui touche l'exterieur passe par l'objet `etat` (schtasks, gh, appel HTTP, processus, racine du depot) : le banc y met des faux.
"""

import taches_planifiees_gestes as g


def executer(demande, etat):
    voie, geste, valeur = demande.get("voie"), demande.get("geste"), demande.get("valeur")
    if not isinstance(voie, str) or not isinstance(geste, str):
        raise ValueError("voie et geste attendus sous forme de texte")
    dossier = etat.dossier or g.nuit.dossier_donnees()
    if voie == "pc":
        port = g.nuit.lit_config(dossier)["port"]
        table = {
            "active": lambda: g.pc_active(True, etat.schtasks),
            "desactive": lambda: g.pc_active(False, etat.schtasks),
            "heure": lambda: g.pc_heure(str(valeur or ""), etat.schtasks),
            "lancer": lambda: g.pc_lancer(port, etat.appel, etat.lance, etat.eteinte, dossier),
            "arreter": lambda: g.pc_arreter(port, etat.appel),
            "envs": lambda: g.ecrit_exclus_pc(valeur, dossier, etat.racine),
        }
    elif voie == "github":
        table = {
            "active": lambda: g.github_active(True, etat.gh),
            "desactive": lambda: g.github_active(False, etat.gh),
            "lancer": lambda: g.github_lancer(etat.gh),
            "arreter": lambda: g.github_arreter(etat.gh),
            "envs_apercu": lambda: g.apercu_exclus_github(valeur, etat.racine),
            "envs": lambda: g.ecrit_exclus_github(valeur, etat.racine),
        }
    else:
        raise ValueError("voie inconnue (pc ou github attendu)")
    if geste not in table:
        raise ValueError(f"geste inconnu pour la voie {voie} : {geste}")
    with etat.verrou_gestes:                               # un geste a la fois : memes fichiers .tmp, memes controles de serie
        resultat = table[geste]()
    if voie == "github":
        etat.invalide()                                    # le cache de sante ne doit pas montrer l'etat d'avant le geste
    return {"ok": True, "resultat": resultat}
