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
- Nombre de modules (`_qr.getModuleCount()`) = table de capacité ISO/IEC 18004 en mode octet : 1 o -> 21, 35 o -> 29,
  50 o et 61 o -> 33 (correction M), 63 o -> 45 (correction H). Le verdict Python de l'A2 peut s'appuyer sur cette table.

Empreintes du fichier en fins de ligne LF, tel qu'enregistré dans git. Avec `core.autocrlf`, la copie extraite peut passer
en CRLF : fabriquer le `.gz` à partir de l'objet git (`git show HEAD:outils_docs/etiquettes_qr/lib/qr-code-styling.min.js
| gzip -9 -n`), jamais de la copie de travail.

Mise à jour : nouvelle version vérifiée de la même façon (intégrité, licence, essai à plusieurs codes), puis ces empreintes
et celles de l'A6 refaites.
