"""Bandeau de sante global de la page « Taches planifiees » : (niveau, phrase) d'apres les voies PC et GitHub.

rouge = probleme prouve (workflow desactive, run planifie trop vieux, Actions coupees) ; orange = non verifie (gh indisponible)
ou echec d'env / de la derniere nuit PC ; vert = tout ce qui est lisible est sain.
"""


def bandeau(pc, gh):
    if gh["alertes"]:
        return "rouge", gh["alertes"][0]
    if not gh["ok"]:
        return "orange", "GitHub non verifie : " + gh["pannes"][0].split(" : ", 1)[-1]
    if gh["pannes"]:
        return "orange", "GitHub partiellement verifie : " + gh["pannes"][0]
    if gh["echecs"]:
        return "orange", f"{len(gh['echecs'])} job(s) en echec dans le dernier run GitHub."
    d = pc["dernier"]
    if d and "illisible" in d:
        return "orange", f"Resultat PC illisible ({d['illisible']})."
    if d and d.get("code") not in (0, None):
        return "orange", "La derniere compilation de nuit sur le PC n'est pas passee (code %s)." % d.get("code")
    return "vert", "GitHub : Build_custom actif, dernier run planifie recent. PC : rien d'anormal."
