"""Banc de genere_schema_persist.py : cles posees par le code (CLES_DU_CODE), contrat relaisLie, grafana facultative.

    python outils_docs/scripts_python/berry/test_genere_schema_persist.py      (code 0 = VERT)

Schema genere en memoire depuis les persists du depot (rien n'est ecrit). Une valeur hors vocabulaire n'est refusee
que si la cle est decrite : sans CLES_DU_CODE ni le contrat, `additionalProperties` accepterait "oui" (temoin).
"""
import copy
import sys

import genere_schema_persist as g

schema, _ = g.genere(g.liste_persists())
echecs = []


def verifie(objet, attendu_ok, titre, cle=None):
    """attendu_ok faux : l'erreur doit citer `cle` (sinon le refus viendrait d'ailleurs)."""
    erreurs = list(g.valide(objet, schema))
    ok = not erreurs if attendu_ok else any(cle in e for e in erreurs)
    print(("OK  " if ok else "KO  ") + titre + ("" if ok else " : " + str(erreurs[:2])))
    if not ok:
        echecs.append(titre)


def capteurs_lies(d):
    """Capteurs d'un persist qui portent un relaisLie (blocs de modules non objets ignores)."""
    for bloc in d.get("modules", {}).values():
        env = bloc.get("environnement") if isinstance(bloc, dict) else None
        capteurs = env.get("capteurs") if isinstance(env, dict) else None
        for c in (capteurs.values() if isinstance(capteurs, dict) else []):
            if isinstance(c, dict) and isinstance(c.get("relaisLie"), dict):
                yield c


chemin = next((p for p in g.liste_persists() if any(capteurs_lies(g.charge(p)))), None)
if chemin is None:
    raise SystemExit("aucun capteur avec relaisLie dans les persists du depot")
base = g.charge(chemin)


def capteur(suspendu=None, desactive=None):
    """Copie du persist de depart, cles posees sur son premier capteur lie."""
    d = copy.deepcopy(base)
    c = next(capteurs_lies(d))
    if suspendu is not None:
        c["suspendu"] = suspendu
    if desactive is not None:
        c["relaisLie"]["desactiveCapteurs"] = desactive
    return d


print("persist de depart : " + g.nom_carte(chemin))
verifie(capteur(), True, "persist reel tel quel : valide")
verifie(capteur(suspendu="ON"), True, "suspendu ON accepte")
verifie(capteur(suspendu="oui"), False, "suspendu hors ON/OFF refuse (cle decrite par CLES_DU_CODE)", "suspendu")
verifie(capteur(desactive="ON"), True, "relaisLie.desactiveCapteurs ON accepte")
verifie(capteur(desactive="Oui"), False, "relaisLie.desactiveCapteurs hors ON/OFF refuse (contrat)", "desactiveCapteurs")

# grafana facultative : un persist reel qui la porte, sans elle, reste valide
porteur = next(p for p in g.liste_persists() if "grafana" in g.charge(p).get("diverses", {}).get("historique", {}))
d = copy.deepcopy(g.charge(porteur))
del d["diverses"]["historique"]["grafana"]
verifie(d, True, "diverses.historique sans grafana : valide (" + g.nom_carte(porteur) + ")")

print("BANC_SCHEMA_PERSIST : " + ("VERT" if not echecs else "ROUGE (%i echec(s))" % len(echecs)))
sys.exit(1 if echecs else 0)
