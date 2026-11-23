# Liens web

Tiré de `outils_docs/README.md` le 2026-11-23 (plan `binomes-berry`, A20). Aiguillage : `outils_docs/INDEX.md`.

## Liens web (page web)

`outils_docs/LIENS_WEB.md` *(généré)* réunit les liens web du dépôt : les outils locaux (ports 7000 à 7995), les liens externes cités dans les fichiers du fork, rangés par thème (Tasmota amont, GitHub tiers, Espressif, boutiques et fiches matériel, PCB, icônes, IA, autres) avec le fichier qui les cite, puis les documents fournis sous `outils_docs/` (PDF, manuels, outils Windows, raccourcis `URL.txt`). Il se régénère par `python outils_docs/scripts_python/outils_pc/genere_liens_web.py` (`--verifier` : code 1 si le fichier est en retard) ou par le bouton de la page. Sont écartés : bancs, bibliothèques tierces, persist, adresses IP du parc, adresses fictives de test, URL à identifiants, l'amont Tasmota.

Tuile « Liens web » de l'annuaire (groupe Dépôt et références, port 7905, `outils_pc/liens_web_web.py`, logique `liens_web.py`, page `liens_web_page.py`, banc `outils_pc/test_liens_web.py`) :

- recherche et filtres (thème, archivés ou non) sur tous les liens ;
- **Ajouter un lien** (adresse, titre, thème, note) : écrit `outils_docs/liens_web/liens_ajoutes.json`, repris par `LIENS_WEB.md` ; seul un lien ajouté se retire depuis la page (un lien cité dans un fichier se corrige dans ce fichier) ;
- **Archiver en PDF** : une adresse qui rend un PDF est copiée telle quelle ; une page HTML est imprimée en PDF par Chrome sans fenêtre (Chrome de `Program Files` requis). Les PDF vont dans `outils_docs/liens_web/archives/` avec leur `index.json`, **ignorés par git** (dépôt public : droits d'auteur et poids). Limites : 40 Mo, 90 s pour une page, hôtes publics seulement (hôte local, privé ou à identifiant refusé, redirections comprises). Le bouton « Ouvrir l'archive » sert le PDF en `sandbox`.

Les trois gestes qui écrivent ou téléchargent (`/ajouter`, `/archiver`, `/regenere`, plus `/retirer`) sont réservés à ce PC (en-tête `X-Liens`, même origine). Tuile et page sans accès réseau avant un clic. Pas encore de cible PlatformIO ni de tâche VS Code : lancer par l'annuaire (http://127.0.0.1:7600) ou `python outils_docs/scripts_python/outils_pc/liens_web_web.py`.
