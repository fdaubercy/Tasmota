# qr-code-styling : bibliothèque de dessin des QR codes

Utilisée par la page « Étiquettes QR code » (7970) et, compressée, par la page `/qrcode` des cartes (plan
`tasks/plans/etiquettes-qrcode.md`, A1). Copie locale : jamais chargée d'un CDN.

| | |
|---|---|
| Paquet | npm `qr-code-styling` 1.9.2 (publié le 2025-04-11, dernière version au 2026-11-12) |
| Licence | MIT, Copyright (c) 2019 Denys Kozak : `LICENSE-qr-code-styling.txt` (à garder avec le fichier) |
| Intégrité du tarball (registre) | `sha512-RgJaZJ1/RrXJ6N0j7a+pdw3zMBmzZU4VN2dtAZf8ZggCfRB5stEQ3IoDNGaNhYY3nnZKYlYSLl5YkfWN5dPutg==`, vérifiée le 2026-11-12 |
| Fichier | `qr-code-styling.min.js` = `package/lib/qr-code-styling.js` du tarball, octet pour octet (bundle UMD, 48 174 o) |
| sha256 du `.js` | `429de523c7563fc0647e618f5a8ea567d5a16412a13ef5d6a082b4502f5a54f9` |
| `.gz` des cartes (A6) | `gzip -9 -n` -> 14 032 o, sha256 `094ef5a2d3cf35e485fc3fc2a3bdd00d7c2fd99821020dd54270e5b54a96b1fb` |

## Vérifié le 2026-11-12 (page d'essai, Chrome)

- Aucune dépendance à charger : `qrcode-generator` est inclus dans le bundle (aucun `require`).
- Plusieurs codes SVG sur une même page : identifiants de `clipPath` propres à chaque code (`_instanceId`). Le défaut de la
  1.5.0 vu sur les maquettes (tous les codes prenaient les points du premier) n'existe plus.
- Codes de 75 px nets en SVG et en canvas.
- **Encodage : la bibliothèque n'écrit PAS d'UTF-8.** Sa fonction par défaut (`stringToBytesFuncs.default`) garde
  `255 & charCodeAt` : un caractère = un octet (Latin-1 tronqué). « é », « « » passent (Latin-1, encodage par défaut des
  QR codes) ; « ’ », « œ », « € » deviendraient des caractères de contrôle. La version UTF-8 existe dans le bundle mais
  n'est pas branchée. **Règle pour la page et la carte (A2 à A6)** : donner les octets UTF-8 et forcer le mode octet :
  `data: String.fromCharCode(...new TextEncoder().encode(texte))`, `qrOptions: {mode: "Byte", ...}`. Le texte vient
  toujours d'un JSON (jamais recopié dans du code JS : `\ ` y deviendrait une espace).
- Table de capacité ISO/IEC 18004 (mode octet, `etiquettes_qr_verdict.CAPACITE`) confrontée à la bibliothèque le
  2026-11-12 avec les octets UTF-8 : 80 cas sur 80 (versions 1 à 40, niveaux M et H, capacité et capacité + 1 ; au-delà de
  la version 40, la bibliothèque lève une erreur). Sans la conversion UTF-8, 80 écarts.

Empreintes du fichier en fins de ligne LF, tel qu'enregistré dans git. Avec `core.autocrlf`, la copie extraite peut passer
en CRLF : fabriquer le `.gz` à partir de l'objet git (`git show HEAD:outils_docs/etiquettes_qr/lib/qr-code-styling.min.js
| gzip -9 -n`), jamais de la copie de travail.

Mise à jour : nouvelle version vérifiée de la même façon (intégrité, licence, essai à plusieurs codes), puis ces empreintes
et celles de l'A6 refaites.
