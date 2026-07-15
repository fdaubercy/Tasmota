# Leçons — dépôt Tasmota (fork personnel)

Format : `[YYYY-MM-DD] | ce qui s'est mal passé | règle à suivre la prochaine fois`
Append uniquement — ne jamais supprimer d'entrée existante.

---

[2026-07-15] | J'ai caractérisé le dépôt en cherchant de la **documentation** (`.doc_for_ai/`, `*.md`) et j'ai conclu « le dépôt est bien fourni pour Berry » sans avoir vu `data/fs/` — soit ~10 800 lignes de Berry écrites par l'utilisateur, le vrai sujet. | Avant de décrire un dépôt, chercher **le code de l'utilisateur**, pas sa doc : `git status --porcelain`, `git diff --stat upstream/<branche>`, et un `find` de l'extension métier (`*.be`) en excluant les dossiers amont (`lib/`, `vendor/`). La doc décrit l'outil ; le diff vs upstream décrit ce que la personne fait vraiment.

[2026-07-15] | J'ai décrit `outils_docs/` comme « un dossier de notes personnelles / journal de config ». C'est faux : c'est l'atelier — scripts Berry perso, 14 scripts Python d'outillage (dont `gen_tapp.py`, `ota-files-uploader.py`), docs de protocoles (MODBUS, UDP) et schémas de branchement. J'avais lu son seul `README.md` et extrapolé au dossier entier. | Ne jamais qualifier un dossier à partir d'un seul fichier lu. Lister l'arborescence (`find <dir> -maxdepth 2`) avant d'en énoncer la nature. Un `README.md` décrit rarement ce que contient réellement le dossier.

[2026-07-15] | Sur la base de cette lecture incomplète, j'ai proposé une skill « routeur » qui n'aurait fait que renvoyer vers `.doc_for_ai/BERRY_TASMOTA.md` — inutile pour quelqu'un qui connaît l'API mieux que la doc. La bonne skill devait encoder **son framework** (paire `controleXxx.be`/`xxxFonctions.be`, contrat `autoexec.be`, flags `_persist.json`). | Avant de concevoir un outil « pour aider à coder dans X », trouver et lire ce que la personne a **déjà écrit** dans X. La valeur d'une skill est dans les conventions maison, pas dans la doc publique — celle-ci se contente d'être citée en second rideau.

[2026-07-15] | J'ai failli signaler `UBE_BERRY_DEBUG_GC` (`user_config_override.h:615`) comme un bug — coquille pour `USE_`. C'est bien une coquille amont, mais **cohérente** avec son site d'usage (`xdrv_52_9_berry.ino:297`) : l'option fonctionne, et la « corriger » la casserait. Rattrapé de justesse en vérifiant. | Un identifiant qui « a l'air » d'une faute de frappe n'est un bug que si sa **définition et son usage divergent**. Toujours `grep` le site d'usage avant de qualifier une coquille de défaut. Dans un fork, une bizarrerie amont cohérente est un contrat, pas une erreur.

[2026-07-15] | Point de méthode validé (pas une erreur) : les sous-agents ont rapporté que le `return` de `gestionFileFolder.be:317` était commenté, rendant la garde d'activation de `autoexec.be` inopérante. Conclusion à fort impact — je l'ai relue moi-même dans le fichier avant de l'inscrire dans la skill, et elle était exacte. | Toute conclusion de sous-agent qui devient une **règle** (documentée, réutilisée, ou qui oriente du code) se vérifie dans le fil principal avant d'être écrite. Le résumé d'un sous-agent est une piste, pas une preuve.

## Règles actives (résumé à relire en début de session)

1. Chercher le code de l'utilisateur (`git status`, diff vs upstream, `find *.be`) **avant** de décrire le dépôt.
2. Lister une arborescence avant de qualifier un dossier ; ne pas extrapoler depuis un seul fichier.
3. Encoder les conventions maison, pas la doc publique.
4. Vérifier le site d'usage avant de déclarer une coquille bugguée.
5. Relire soi-même toute conclusion de sous-agent qui devient une règle.
