"""Page de repli d'un outil arrete : un service worker, enregistre par la page de l'outil sur SA propre origine
(http://127.0.0.1:<port>, contexte securise), repond a la place du serveur absent.

Sans lui, un onglet reste sur « connexion refusee » quand l'outil s'arrete (ou avant qu'il soit relance). Avec lui,
la navigation vers l'outil montre « <nom> est arrete » avec un lien vers l'annuaire (port 7600), et la page se
recharge seule des que l'outil repond de nouveau. Le worker ne garde rien en cache : il ne fait que rattraper un
echec reseau de navigation (les autres requetes, dont l'EventSource et les fetch, passent sans lui).
Limite : un service worker exige un contexte securise, donc 127.0.0.1 ou localhost ; depuis une autre adresse du
reseau, pas de repli (le navigateur affiche son erreur habituelle).
"""

import json

ENREGISTREMENT = ("<script>if('serviceWorker' in navigator)"
                  "navigator.serviceWorker.register('/sw.js').catch(function(){})</script>")

_PAGE = ("<!doctype html><html lang=fr><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
         "<title>{titre}</title><body style='font:16px sans-serif;margin:0;background:#111827;color:#f3f4f6'>"
         "<main style='max-width:34em;margin:12vh auto;padding:0 16px'><h1 style='font-size:22px'>{titre}</h1>"
         "<p id=m></p><p><a id=a style='color:#93c5fd' href='#'>Ouvrir l’annuaire</a></p>"
         "<p style='color:#9ca3af'>Cette page se recharge toute seule dès que l’outil répond.</p></main>"
         "<script>var p=location.port==='7600';"
         "document.getElementById('m').textContent=p?"
         "'Lancez la tâche VS Code « Outil : annuaire des outils », ou relancez-le depuis un terminal.':"
         "'Relancez-le depuis la tuile de l’annuaire (bouton Lancer).';"
         "if(p)document.getElementById('a').style.display='none';"
         "else document.getElementById('a').href=location.protocol+'//'+location.hostname+':7600/';"
         "setInterval(function(){fetch('/icone.svg',{cache:'no-store'}).then(function(r){if(r.ok)location.reload()})"
         ".catch(function(){})},3000)</script>")


def service_worker(nom):
    """Texte du worker de l'outil `nom` (le nom est insere par json.dumps dans le JS, puis echappe en HTML dans le worker)."""
    page = _PAGE.replace("{titre}", "{T}")
    return ("const NOM = " + json.dumps(nom, ensure_ascii=True) + ";\n"
            "const PAGE = " + json.dumps(page, ensure_ascii=True) + ".split('{T}').join(NOM.replace(/[&<>]/g, c => '&#' + c.charCodeAt(0) + ';') + ' est arrêté');\n"
            "self.addEventListener('install', () => self.skipWaiting());\n"
            "self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));\n"
            "self.addEventListener('fetch', e => {\n"
            "  if (e.request.mode !== 'navigate') return;\n"
            "  e.respondWith(fetch(e.request).catch(() => new Response(PAGE, {status: 503, headers: "
            "{'Content-Type': 'text/html; charset=utf-8', 'X-Repli': '1'}})));\n"
            "});\n")
