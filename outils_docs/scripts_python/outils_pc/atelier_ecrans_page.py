"""Page de l'atelier des ecrans (port 7960), servie par atelier_ecrans_web.py sur GET /.

PROVISOIRE (plan atelier-ecrans A6, premiere moitie) : titre et script vide ; la vraie page (en-tete, canevas, palette,
proprietes, tableau des objets, fichiers generes) remplace ce texte en A6b. Le titre `<title>Atelier des écrans</title>`
est lu par build/cible_atelier_ecrans.py::repond (MARQUE) : le garder tel quel.
"""

PAGE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Atelier des écrans</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: system-ui, sans-serif; margin: 2em; }
</style>
</head>
<body>
<h1>Atelier des écrans</h1>
<p>Page en construction : les routes du serveur sont prêtes (GET /cartes, /catalogue, /description, /valeurs, /police ;
POST /apercu, /capture).</p>
<script>
</script>
</body>
</html>
"""
