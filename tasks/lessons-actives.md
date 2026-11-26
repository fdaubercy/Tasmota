<!-- lessons-actives source_lignes=270 date=2026-11-23 -->
# Leçons actives — Tasmota (synthèse ; détail dans lessons.md, retrouvable par la date)

## Builds et pio
- Tester l'absence de pio/scons DANS la commande qui édite `data/` ou lance un outil lourd (sonde Chrome, banc), abandon sinon. Filtrer par nom d'exécutable, sans compter sa propre ligne. Compiler par la page Build (:7700), jamais pio direct ni `--list-targets` ; la fin d'un scons n'est pas l'absence de build (garde_build) | dernier incident 2026-11-14 | récidives 16
## Sessions parallèles et git
- Dépôt partagé : `git commit -- <chemins>`, relire `git show --stat HEAD`, pousser `<sha>:development`, jamais stash/checkout/reset ni `git add -A`. Un fichier ou commit inconnu est d'une autre session ; après une limite, ListAgents et journal reprise_limite avant d'écrire | dernier incident 2026-11-14 | récidives 17 -> proposer un contrôle mécanique (hook ou banc)
## Secrets
- Ne jamais imprimer de dict serveur/wifi/mqtt/ftp, de ligne `#define` de mot de passe, ni de contexte `-A/-B` : clés nommées une à une, numéros de ligne, ou `grep -viE "pass|pwd|mdp|key|token"` en dernier. Sous-agent : interdire `git diff` en clair sur user_config_override.h et les persist. Contrôle de secrets lancé seul, lu, puis commit au message suivant (agent controleur-secrets). Accord avant de modifier ces fichiers | dernier incident 2026-11-23 | récidives 13
## Preuve et faux vert
- Un vert doit montrer quelle ligne l'a rendu vert : témoin qui DOIT échouer, mutant, entrée de test copiée sur l'écrivain réel, jamais dérivée de la constante testée. Lancer le banc et lire son code de sortie ; relancer les bancs qui copient un module modifié ; tester le branchement de production d'une dépendance injectée | dernier incident 2026-11-15 | récidives 16 -> proposer un contrôle mécanique (hook ou banc)
## Affirmer seulement ce qui est lu
- Comportement d'un runtime, d'un rôle, d'une clé de persist, d'un blocage : chemin et ligne dans le code (appelants, lecteur de la clé, garde), jamais le bon sens ni une doc ou un sous-agent. Relire la sortie entière et la chronologie ; lire la fin d'un journal avant de le citer | dernier incident 2026-11-21 | récidives 15 -> proposer un contrôle mécanique (hook ou banc)
## Berry solidifié
- Aucune variable nommée comme un builtin (format, str, int...), pas de `{n,m}` dans une regex, fonction appelée par `xxxFonctions.nom` et `import` en tête, globale ajoutée à `globs`, module ajouté à `custom_berry_solidify` de chaque env. Seuls berry.exe strict, l'agent verificateur-solidification et la page Build prouvent la solidification, pas les bancs | dernier incident 2026-11-23 | récidives 20
## Persist et cartes en ligne
- Changer un persist de carte : supprimer persist et autoexec, redémarrer, renvoyer, relire (ou recharger Berry avant Restart). `Topic`/`Hostname` en dernier. Avant flash : CFG_HOLDER, AdcParam, réglages propres relevés ; relire la carte réelle avant de copier une config. Br avec socket : jamais sur une carte en difficulté | dernier incident 2026-11-21 | récidives 11
## FS OTA
- Comparer la place libre (UfsFree) et l'identité de l'image avant l'envoi ; supprimer les anciens fichiers absents de l'image, exclure persist et .be solidifiés | dernier incident 2026-11-23 | récidives 5
## Commits
- Inclure override.ini, user_config_override.h et modules.h ; aucun trailer Co-Authored-By ; message multiligne selon le shell ; ne rien exclure en silence ; commit partiel recalculé, pas un diff appliqué | dernier incident 2026-11-17 | récidives 12 -> proposer un contrôle mécanique (hook ou banc)
## Pages web et sondes
- Voir la page dans Chrome (mesures, pas HTML lu) ; sondes qui attendent une condition ; relancer l'outil avant l'essai utilisateur ; une largeur de colonne est commune à la table | dernier incident 2026-11-14 | récidives 10
## Écriture de fichiers
- `\b` et `\n` via heredoc se corrompent : outil Edit ou chaîne brute, puis grep des caractères de contrôle | dernier incident 2026-11-15 | récidives 5
## Langue
- Message final en français malgré les rapports anglais | dernier incident 2026-10-12 | récidives 3 -> proposer un contrôle mécanique (hook ou banc)
