"""Barre commune des pages d'outils (acces_web.habille) : retour a l'annuaire, liste des outils en cours, signal de fin.

Chaque outil sert `GET /_barre.json` (apres le controle d'acces habituel) : les outils vivants d'apres les fiches de
presence (%LOCALAPPDATA%/outils_tasmota/presence, PID verifie), avec « occupe » pour ceux qui exposent une route
`route_occupe` du registre (Build, Synchro du fork : `{"en_cours": true}` pendant un lancement). La barre interroge
cette route toutes les 4 s ; quand un outil passe d'occupe a libre, elle affiche « <nom> : termine », met le titre de
l'onglet a jour et, si l'utilisateur a clique « Notifications », envoie une notification du navigateur.
Tout texte venu du registre ou d'une fiche passe par textContent (jamais innerHTML).
"""

import json
import threading
import time
import urllib.request

PORT_ANNUAIRE = 7600
COULEUR = "#1f2937"
_CACHE = {"t": 0.0, "donnees": None}
_VERROU = threading.Lock()
_SANS_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _occupe(port, route):
    """True si GET 127.0.0.1:port+route repond en_cours: true ; toute erreur = libre (la barre n'est qu'un indicateur)."""
    try:
        with _SANS_PROXY.open(f"http://127.0.0.1:{int(port)}{route}", timeout=0.6) as r:
            return bool(json.loads(r.read().decode("utf-8")).get("en_cours"))
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def outils_vivants():
    """[{id, nom, port, occupe}] des outils dont la fiche de presence est vivante, dans l'ordre du registre."""
    import acces_web
    import annuaire_registre as reg
    par_nom = {o.nom_acces: (i, o) for i, o in enumerate(reg.OUTILS)}
    trouves = []
    try:
        fiches = sorted(acces_web.dossier_presence().glob("*.json"))
    except OSError:
        return []
    for chemin in fiches:
        try:
            fiche = json.loads(chemin.read_text(encoding="utf-8"))
            ordre, outil = par_nom[fiche["nom"]]
            port = int(fiche["port"])
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if acces_web.pid_vivant(fiche.get("pid")):
            trouves.append((ordre, {"id": outil.id, "nom": outil.nom, "port": port,
                                    "occupe": _occupe(port, outil.route_occupe) if outil.route_occupe else False}))
    return [t[1] for t in sorted(trouves, key=lambda t: t[0])]


def barre_json():
    """Corps de /_barre.json, garde 2 s (plusieurs pages ouvertes interrogent chacune toutes les 4 s)."""
    with _VERROU:
        if _CACHE["donnees"] is None or time.monotonic() - _CACHE["t"] > 2.0:
            _CACHE["donnees"] = json.dumps({"outils": outils_vivants()}, ensure_ascii=False)
            _CACHE["t"] = time.monotonic()
        return _CACHE["donnees"]


_STYLE_LIEN = "color:#fff;text-decoration:none;padding:3px 10px;display:block"
_HTML = (
    "<nav id='barre-outils' aria-label='Outils' style='flex:none;position:sticky;top:0;z-index:9999;background:" + COULEUR
    + ";color:#fff;font:13px sans-serif;padding:6px 16px;display:flex;gap:12px;align-items:center'>"
    "<a id='barre-retour' style='color:#fff' href='#'>← Annuaire</a>"
    "<span style='opacity:.7'>{nom}</span>"
    "<span style='position:relative'><button id='barre-encours' type='button' aria-expanded='false' "
    "style='background:none;border:1px solid #6b7280;color:#fff;border-radius:4px;padding:1px 8px;font:inherit;cursor:pointer'>"
    "En cours</button><div id='barre-liste' style='display:none;position:absolute;left:0;top:26px;min-width:220px;"
    "background:" + COULEUR + ";border:1px solid #6b7280;border-radius:4px;padding:4px 0'></div></span>"
    "<span role='status'><span id='barre-toast' style='display:none;background:#065f46;border-radius:4px;padding:1px 10px'></span></span>"
    "<span id='barre-notif' style='display:none;margin-left:auto;align-items:center;gap:8px;border:1px solid #6b7280;"
    "border-radius:14px;padding:2px 8px 2px 10px;color:#9ca3af'>"
    "<svg id='barre-cl-off' viewBox='0 0 24 24' width='16' height='16' fill='none' stroke='currentColor' stroke-width='2' "
    "stroke-linecap='round' stroke-linejoin='round'><path d='M8.7 3A6 6 0 0 1 18 8a21.3 21.3 0 0 0 .6 5'/>"
    "<path d='M17 17H3s3-2 3-9a4.67 4.67 0 0 1 .3-1.7'/><path d='M10.3 21a1.94 1.94 0 0 0 3.4 0'/><path d='m2 2 20 20'/></svg>"
    "<svg id='barre-cl-on' viewBox='0 0 24 24' width='16' height='16' fill='none' stroke='currentColor' stroke-width='2' "
    "stroke-linecap='round' stroke-linejoin='round' style='display:none'><path d='M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9'/>"
    "<path d='M10.3 21a1.94 1.94 0 0 0 3.4 0'/></svg>"
    "<span id='barre-bloc' style='display:none;font-size:12px;color:#fbbf24'>Bloquées par le navigateur : cadenas de l’adresse, Notifications, Autoriser</span>"
    "<button id='barre-sw' type='button' role='switch' aria-checked='false' aria-label='Notifications'></button></span></nav>"
    "<style>#barre-sw{position:relative;width:38px;height:22px;border-radius:11px;border:0;padding:0;background:#6b7280;cursor:pointer}"
    "#barre-sw::after{content:'';position:absolute;top:2px;left:2px;width:18px;height:18px;border-radius:50%;background:#fff;"
    "transition:transform .2s}#barre-sw[aria-checked=true]{background:#2ea043}"
    "#barre-sw[aria-checked=true]::after{transform:translateX(16px)}</style>"
    "<script>(function(){"
    "var a=document.getElementById('barre-retour'),h=location.hostname,bar=document.getElementById('barre-outils');"
    "if(location.port==='" + str(PORT_ANNUAIRE) + "'||(!{partage}&&!(h==='127.0.0.1'||h==='localhost'||h==='[::1]')))"
    "{bar.style.display='none';return}"
    "a.href=location.protocol+'//'+h+':" + str(PORT_ANNUAIRE) + "/';"
    "var btn=document.getElementById('barre-encours'),liste=document.getElementById('barre-liste'),"
    "toast=document.getElementById('barre-toast'),notif=document.getElementById('barre-notif'),prec=null,titre=document.title;"
    "btn.onclick=function(){var o=liste.style.display==='none';liste.style.display=o?'block':'none';"
    "btn.setAttribute('aria-expanded',o?'true':'false')};"
    "var sw=document.getElementById('barre-sw'),clOn=document.getElementById('barre-cl-on'),clOff=document.getElementById('barre-cl-off');"
    "function pref(){try{return localStorage.getItem('barre-notif')}catch(e){return null}}"
    "function actif(){return !!window.Notification&&Notification.permission==='granted'&&pref()!=='0'}"
    "function peint(){var v=actif(),t=v?'Désactiver les notifications':'Activer les notifications';"
    "sw.setAttribute('aria-checked',v?'true':'false');sw.title=t;notif.title=t;notif.style.color=v?'#3fb950':'#9ca3af';"
    "clOn.style.display=v?'':'none';clOff.style.display=v?'none':'';document.getElementById('barre-bloc').style.display=(window.Notification&&Notification.permission==='denied')?'':'none'}"
    "function fixe(v){try{localStorage.setItem('barre-notif',v?'1':'0')}catch(e){}peint()}"
    "function avertit(m){toast.textContent=m;toast.style.display='';setTimeout(function(){toast.style.display='none'},6000)}"
    "if(window.Notification){notif.style.display='inline-flex';peint();"
    "sw.onclick=function(){if(actif()){fixe(false);return}"
    "if(Notification.permission==='granted'){fixe(true)}"
    "else if(Notification.permission==='default'){Notification.requestPermission().then(function(p){if(p==='granted')fixe(true);else peint()})}"
    "else avertit('Notifications bloquées dans les réglages du navigateur')}}"
    "var avant=null,mine=null,rt=null;"
    "function rend(){if(mine!==null&&document.title===mine)document.title=avant;mine=null;avant=null}"
    "function fini(nom){toast.textContent=nom+' : terminé';toast.style.display='';"
    "if(mine===null)avant=document.title;mine='Terminé : '+nom+' - '+avant;document.title=mine;"
    "try{if(actif())new Notification(nom,{body:'Terminé',tag:'fin-'+nom})}catch(e){}"
    "clearTimeout(rt);rt=setTimeout(function(){toast.style.display='none';rend()},15000)}"
    "addEventListener('focus',rend);"
    "document.addEventListener('visibilitychange',function(){if(!document.hidden){rend();poll()}});"
    "document.addEventListener('keydown',function(e){if(e.key==='Escape'&&liste.style.display!=='none')btn.onclick()});"
    "document.addEventListener('click',function(e){if(liste.style.display!=='none'&&!liste.contains(e.target)&&e.target!==btn)btn.onclick()});"
    "function maj(o){btn.textContent='En cours : '+o.length;liste.textContent='';"
    "o.forEach(function(x){var l=document.createElement('a');"
    "l.href=location.protocol+'//'+h+':'+x.port+'/';l.setAttribute('style','" + _STYLE_LIEN + "');"
    "l.textContent=(x.occupe?'● ':'')+x.nom+(x.occupe?' (occupé)':'');liste.appendChild(l)});"
    "if(prec)o.forEach(function(x){if(prec[x.id]===true&&!x.occupe)fini(x.nom)});"
    "prec={};o.forEach(function(x){prec[x.id]=x.occupe})}"
    "function poll(){fetch('/_barre.json',{cache:'no-store'}).then(function(r){return r.ok?r.json():null})"
    ".then(function(d){if(d&&Array.isArray(d.outils))maj(d.outils)}).catch(function(){})}"
    "poll();setInterval(poll,4000)})()</script>")


def html(nom, partage):
    """Barre inseree apres <body> ; `nom` est echappe par l'appelant."""
    return _HTML.replace("{nom}", nom).replace("{partage}", "true" if partage else "false")
