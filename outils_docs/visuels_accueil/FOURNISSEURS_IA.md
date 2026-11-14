# Fournisseurs IA pour l'assistant de l'atelier des visuels (A9)

Consultation du 2026-11-14. Notes de recherche, rien n'a ete envoye, aucun compte ni cle cree. Les chiffres des offres gratuites
changent souvent : les relire dans la console du service avant de regler `plafond` dans `config.json`.

## Tableau

| Fournisseur | URL de base (chat completions) | Limites gratuites | Depassement | En-tetes de quota | Donnees pour l'entrainement (offre gratuite) | UE / France |
|---|---|---|---|---|---|---|
| Google Gemini API | `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions` | Par PROJET (pas par cle), RPM, TPM et RPD, reset des RPD a minuit heure du Pacifique. Valeurs par modele visibles seulement dans AI Studio (connexion requise), non verifiees | 429 `RESOURCE_EXHAUSTED` | Non documentes | OUI hors EEE/Suisse/UK ; NON dans l'EEE (conditions « payantes » appliquees au gratuit) | Disponible ; protection renforcee pour la France |
| Mistral (AI Studio, plan Experiment) | `https://api.mistral.ai/v1/chat/completions` | Non publiees dans la doc ; renvoi vers la console admin (limites). Sources tierces : ~1 req/s, 500 000 tokens/min, non confirme | 429 (non verifie en detail) | Non verifies | OUI par defaut, desactivable (Admin Console, menu Privacy) | Editeur francais, UE |
| OpenRouter (modeles `:free`) | `https://openrouter.ai/api/v1/chat/completions` | 20 req/min ; 50 req/jour (moins de 10 credits achetes), 1000/jour (10 credits ou plus), au niveau du COMPTE | 429 `rate_limit_exceeded` | `X-RateLimit-Limit/Remaining/Reset` seulement sur le 429 propre a OpenRouter ; `Retry-After` si fourni ; `GET /api/v1/key` donne le reste du jour (UTC) | Depend du fournisseur amont du modele `:free` ; OpenRouter ne stocke pas les prompts par defaut | Service americain, modeles tiers |
| Ollama (local) | `http://127.0.0.1:11434/api/generate` (deja code) | Aucune | Aucun | Aucun | Rien ne sort du PC | Local |

## Gemini

- Sources : https://aistudio.google.com/docs/rate-limits, /docs/terms, /docs/openai, /docs/image-understanding (anciennes adresses `ai.google.dev/gemini-api/docs/...` redirigees ici).
- Limites : « appliquees par projet, pas par cle API » ; depasser UN seul de RPM, TPM ou RPD suffit a declencher l'erreur. Les valeurs par modele ne sont plus dans la page publique ; les blogs tiers donnent de 20 a 1500 requetes/jour selon le modele et la date : ne pas s'y fier.
- Image : requete totale (texte + octets en ligne) limitee a 20 Mo ; PNG, JPEG, WebP, HEIC, HEIF. Largement au-dessus de notre plafond de 10 Mo.
- Donnees : hors EEE/Suisse/UK, le contenu du gratuit est utilise pour ameliorer les produits et peut etre lu par des relecteurs humains. Dans l'EEE, en Suisse et au Royaume-Uni, les conditions des services payants (pas d'entrainement) s'appliquent aussi au gratuit, d'apres les conditions lues.
- Compatibilite OpenAI : bearer token, `image_url` en data URL comme dans `ApiExterne` : compatible tel quel. Le nom du modele est a lire sur l'endpoint de liste (les noms cites par la page n'etaient pas fiables). Compatibilite « en beta ».

## Mistral

- Sources : https://docs.mistral.ai/capabilities/vision/ (lue) ; page d'aide Mistral sur le plan Experiment (illisible par le lecteur de pages, 404, connue seulement par un extrait de recherche).
- Modeles vision cites par la doc : `mistral-large-2512`, `mistral-medium-2508`, `mistral-small-2506`, `ministral-3b/8b/14b-2512` (alias `-latest`).
- Entrainement : l'aide Mistral indique que les requetes du plan Experiment peuvent servir a entrainer les modeles, avec desactivation possible dans l'Admin Console.
- DIFFERENCE DE FORMAT : l'exemple officiel passe `"image_url": "<url>"` (CHAINE), pas `{"url": ...}` comme OpenAI. On n'a pas pu verifier si l'objet OpenAI est aussi accepte ni si une data URL base64 est acceptee dans ce champ. A tester avec une vraie cle avant de promettre la compatibilite.
- Taille d'image et nombre d'images : non trouves.

## OpenRouter

- Sources : https://openrouter.ai/docs/api-reference/limits (lue), https://openrouter.ai/docs/guides/privacy/data-collection (lue).
- Les modeles gratuits ont un identifiant finissant par `:free` ; ceux qui lisent les images varient dans le temps : lire la liste du site (filtre entree image) au moment du choix.
- 429 : corps `{"error": {"code": 429, "message": "Rate limit exceeded", "metadata": {"error_type": "rate_limit_exceeded"}}}`. Un 429 peut aussi venir du fournisseur amont (`error.metadata.provider_code`). En flux, l'erreur arrive en evenement SSE (`finish_reason: "error"`), sans code HTTP : sans objet pour nous (`stream` non utilise).
- Les reponses reussies n'ont pas d'en-tetes `X-RateLimit-*`.
- Donnees : OpenRouter ne stocke pas prompts et reponses sauf option activee ; la reutilisation pour l'entrainement par le fournisseur amont d'un modele gratuit n'est pas tranchee par la page lue. Reglage de compte « ZDR only » pour exclure les endpoints a retention.
- Taille d'image et UE : non verifies.

## Ollama

- `/api/generate` avec `images: [base64]` : c'est ce que fait deja `Ollama.demande` (source : doc de l'API Ollama, github.com/ollama/ollama/blob/main/docs/api.md).
- Modeles vision de la bibliotheque (ollama.com/library, tailles de telechargement lues) :
  - `qwen2.5vl` : 3b 3,2 Go ; 7b (latest) 6,0 Go ; 32b 21 Go ; 72b 49 Go.
  - `llama3.2-vision` : 11b (latest) 7,8 Go ; 90b 55 Go.
  - `gemma3` : 4b (latest) 3,4 Go ; 12b 8,2 Go ; 27b 17 Go (texte + image sauf 1b et 270m).
  - Le defaut du code, `llava`, n'a pas ete reverifie.
- Memoire : la bibliotheque ne donne pas d'exigence de RAM. Ordre de grandeur : taille du telechargement plus quelques Go pour le contexte et l'image (VRAM ou RAM). Non mesure. Un 7b en 6 Go tourne sur un GPU de 8 Go ou en RAM (lent sans GPU).
- Qualite : ces modeles decrivent une photo, mais produire un SVG propre est une autre affaire. Non essaye.

## Points qui changent le code

1. `LimiteAtteinte` : `_post` ne lit que `Retry-After` sur 429. Suffisant pour OpenRouter (quand fourni) ; Gemini ne documente pas d'en-tete, donc `reprise` reste `None`, le rouge dure jusqu'a minuit (deja le comportement). Aucune lecture d'en-tete de quota a ajouter.
2. Un 429 peut venir d'un fournisseur amont derriere OpenRouter : meme traitement (rouge, pas de reessai), rien a changer.
3. Mistral : `image_url` en chaine dans leur exemple. `ApiExterne` envoie l'objet `{"url": ...}`. Si le test reel echoue, ajouter une option de format (chaine ou objet) dans les reglages du fournisseur.
4. Gemini : l'URL doit etre le chemin complet `.../v1beta/openai/chat/completions` (le code poste sur l'URL telle quelle, sans suffixe). Idem OpenRouter et Mistral : l'utilisateur doit saisir l'URL complete, pas la base. A dire dans l'aide de la page.
5. Taille : le plafond de 10 Mo du code est sous les limites connues (Gemini 20 Mo par requete) ; le base64 ajoute un tiers, a garder en tete pour Mistral et OpenRouter dont la limite n'est pas connue.
6. Confirmation avant envoi : le message doit citer l'entrainement possible (Mistral gratuit par defaut, Gemini hors EEE).

## Non verifie

- Valeurs de limites gratuites de Gemini (page AI Studio derriere connexion) et de Mistral (console admin) : seulement des chiffres de blogs.
- Pages d'aide Mistral : 404 pour le lecteur, statut d'entrainement lu dans un extrait de recherche.
- Mistral : format de la data URL base64, taille maximale d'image, en-tetes de quota, forme du 429.
- OpenRouter : liste actuelle des modeles `:free` avec vision, politique d'entrainement par modele, taille d'image.
- Ollama : exigences memoire reelles, comportement de `llava` aujourd'hui.
- Le lecteur de pages resume avec un petit modele : certains noms de modeles recus (Gemini, liste Ollama) semblaient incoherents et n'ont pas ete retenus.
