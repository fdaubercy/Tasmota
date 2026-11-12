# Étiquettes QR code : maquettes (2026-11-12)

Outil PC (tuile de l'annuaire, page 7970) : composer par env le QR code qui affiche l'identité d'une carte au téléphone,
l'imprimer (étiquette ou planche A4), l'afficher sur la page `/qrcode` de la carte. Spec :
`docs/superpowers/specs/2026-11-12-etiquettes-qrcode-design.md` ; plan : `tasks/plans/etiquettes-qrcode.md`.

**Modèle A retenu par l'utilisateur le 2026-11-12** (trois colonnes : cartes, contenu et style, aperçu), en clair et en
sombre. La planche suit `modele-P.png`.

- Images : `modele-A.png` (trois colonnes : cartes, contenu et style, aperçu), `modele-A-sombre.png`,
  `modele-B.png` (grande fenêtre d'aperçu, réglages en onglets), `modele-C.png` (tableau du parc, éditeur latéral),
  `modele-P.png` (planche A4, 25 mm, petit nom).
- Code : `maquettes_etiquettes_qr.html?m=A|B|C|P` et `&theme=sombre`. Libellés et taille modifiables : le texte lu et le
  verdict suivent. QR codes dessinés par qr-code-styling 1.5.0 (jsDelivr, maquette seulement), en `canvas`.

## Constats faits en dessinant les maquettes (à reprendre en A1)

1. qr-code-styling 1.5.0 en SVG donne les mêmes `id` de clipPath à tous les codes d'une page : avec plusieurs codes
   (planche), tous prennent les points du premier. La version retenue doit en être exempte, ou la page doit dessiner en
   `canvas` (l'export SVG reste possible par `getRawData("svg")` d'un code seul).
2. Dessinés petits (75 px), les points fondent en un carré plein : dessiner à 300 px au moins puis réduire.
3. Exemple réel : 4 lignes (hostname, IP, id ModBus, ligne libre) = 82 octets, version 8 en correction H (image au
   centre) : 0,44 mm par carré à 25 mm, verdict « limite ». Sans l'image (correction M), même texte : version 5.
