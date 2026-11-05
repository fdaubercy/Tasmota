# Onglet « autoexec.bat » de l'Assistant persist : maquettes

Demande du 2026-11-03 (plan `tasks/plans/energie-differentiel.md`, A14) : modifier facilement ou ajouter des lignes dans
l'`autoexec.bat` d'une carte, avec une banque de commandes. **Modèle C retenu** (avec un ajout du A : clic sur un avertissement → sa ligne, survol du point de marge). **Réalisé** le 2026-11-05 : mode
d'emploi dans `outils_docs/README.md`, § « Onglet « autoexec.bat » ».

- `modele-A.png` : le fichier en texte libre, avertissements dans la marge sous la ligne, banque à droite (« Insérer »).
- `modele-B.png` : une ligne = une commande, rangées par section (titres tirés des commentaires) ; ajout guidé par un
  formulaire tiré de la banque (minuterie : heure, jours, relais, action), aperçu de la ligne avant l'ajout.
- `modele-C.png` : texte à gauche, analyse en liste dessous, assistant d'ajout à droite, diff et envoi en bas.
- `maquettes_autoexec.html` : code des maquettes (`?modele=A|B|C`). Lignes du différentiel, avertissements en exemple
  (la ligne `Hostname` et la faute `WebSesnor2` n'existent pas dans le vrai fichier).

## Décisions de l'utilisateur (2026-11-03)

- Onglet de l'Assistant persist (page 7900).
- Après « Enregistrer » : diff confirmé, fichier du dépôt écrit, **puis envoi proposé** à la carte en OTA (moteur de
  l'onglet Fichiers de la page build). La carte l'exécute au prochain démarrage.
- Avertissements : redémarrage à répétition (liste tirée du code Tasmota, `restart_flag = 2`, + cas vécus), doublon
  avec le persist (`build_sauvegarde::POSEES`), secret en clair (dépôt public), commande inconnue.
- Banque de commandes : fichier JSON du dépôt ; chaque commande ajoutée par l'utilisateur la complète.
- Les deux usages comptent : être protégé des erreurs, et écrire vite une commande dont on ignore la syntaxe.
