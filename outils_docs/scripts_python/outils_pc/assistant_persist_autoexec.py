#!/usr/bin/env python3
"""Routes /autoexec* de l'Assistant persist (plan autoexec-bat, A5 et A7) ; assistant_persist_web.py ne fait que deleguer.
Les exceptions sont celles du serveur : ValueError -> 400, LookupError -> 404, RuntimeError -> 409.
  GET  /autoexec?env=             {texte (secrets en ***), empreinte, chemin, existe, avertissements, lignes (du texte masque)}
  GET  /autoexec/banque           la banque de commandes (autoexec_banque.charge)
  POST /autoexec/analyse          {env, texte}                                -> {avertissements}
  POST /autoexec/diff             {env, texte}                                -> autoexec_fichier.diff
  POST /autoexec/ecrit            {env, texte, empreinte, rouges_lus}         -> autoexec_fichier.ecrit
  POST /autoexec/banque/ajoute    {entree}                                    -> la banque a jour
  POST /autoexec/envoi/prepare    {env, transport=http|mqtt}                 -> autoexec_envoi.prepare (sur_carte masque)
  POST /autoexec/envoi            {env, jeton, rouges_lus, redemarrer, transport} -> autoexec_envoi.envoie
Env : une carte du parc seulement (assistant_persist_modification.cartes) ; nom mal forme -> 400, inconnu ou base -> 404.
L'analyse se fait sur le texte DEMASQUE cote serveur ; aucune reponse ne porte une valeur a secret (les messages
d'avertissement ne citent que le nom de la commande). Banc : test_assistant_persist_autoexec.py (logique d'envoi :
test_autoexec_envoi.py).
"""

import re

import assistant_persist_modification as apm2
import autoexec_analyse
import autoexec_banque
import autoexec_envoi
import autoexec_fichier

NOM_ENV = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


def _env(racine, demande):
    valeur = demande.get("env")
    if not isinstance(valeur, str) or not NOM_ENV.fullmatch(valeur) or ".." in valeur:
        raise ValueError("env : nom de carte attendu")
    if valeur not in [c["env"] for c in apm2.cartes(racine)]:
        raise LookupError(f"{valeur} n'est pas une carte du parc")
    return valeur


def _texte(demande):
    texte = demande.get("texte")
    if not isinstance(texte, str):
        raise ValueError("texte : chaine attendue")
    return texte


def get(racine, chemin, requete):
    if chemin == "/autoexec":
        env = _env(racine, requete)
        l = autoexec_fichier.lit(racine, env)
        return {**l, "avertissements": autoexec_fichier.avertissements(racine, env, autoexec_fichier.texte_disque(racine, env)),
                "lignes": autoexec_analyse.lignes(l["texte"])}
    if chemin == "/autoexec/banque":
        return autoexec_banque.charge(racine)
    raise LookupError(chemin)


def post(racine, chemin, demande, builds_en_cours):
    if chemin == "/autoexec/banque/ajoute":
        autoexec_banque.ajoute(racine, demande.get("entree"), builds_en_cours)
        return autoexec_banque.charge(racine)
    if chemin == "/autoexec/envoi/prepare":
        return autoexec_envoi.prepare(racine, _env(racine, demande), builds_en_cours,
                                      transport=demande.get("transport", "http"))
    if chemin == "/autoexec/envoi":
        return autoexec_envoi.envoie(racine, _env(racine, demande), demande.get("jeton"), demande.get("rouges_lus"),
                                     demande.get("redemarrer"), builds_en_cours, transport=demande.get("transport", "http"))
    if chemin not in ("/autoexec/analyse", "/autoexec/diff", "/autoexec/ecrit"):
        raise LookupError(chemin)
    env, texte = _env(racine, demande), _texte(demande)
    if chemin == "/autoexec/diff":
        return autoexec_fichier.diff(racine, env, texte)
    if chemin == "/autoexec/ecrit":
        empreinte = demande.get("empreinte")
        if not isinstance(empreinte, str):
            raise ValueError("empreinte : chaine attendue (recharger le fichier)")
        return autoexec_fichier.ecrit(racine, env, texte, empreinte, demande.get("rouges_lus"), builds_en_cours)
    disque = autoexec_fichier.texte_disque(racine, env)
    return {"avertissements": autoexec_fichier.avertissements(racine, env, autoexec_fichier.demasque(texte, disque))}
