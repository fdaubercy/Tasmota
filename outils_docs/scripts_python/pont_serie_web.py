"""Petit serveur HTTP du pont serie (pont_serie.py), sur le MEME port que le TCP brut.

Le pont reconnait une requete HTTP a ses premiers octets ("GET ", "POST") et la confie ici :
    GET  /       page des logs colores (navigateur : http://127.0.0.1:7000)
    GET  /flux   flux en direct (Server-Sent Events) : les 500 derniers morceaux, puis la suite
    POST /cmd    corps = commande Tasmota, transmise a la carte (ex. "Status 4")

Securite : le pont n'ecoute que sur 127.0.0.1. Contre une page web malveillante qui viserait
127.0.0.1:7000/cmd depuis le navigateur, /cmd exige l'en-tete 'X-Pont: 1' (un en-tete personnalise
declenche une requete CORS preliminaire, a laquelle on ne repond pas) et refuse une autre Origine.
"""

import json

PAGE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Pont serie</title>
<style>
 body{margin:0;background:#1e1e1e;color:#d4d4d4;font:13px Consolas,monospace;display:flex;flex-direction:column;height:100vh}
 #barre{display:flex;gap:8px;padding:6px;background:#252526;border-bottom:1px solid #333;align-items:center}
 #cmd{flex:1;background:#3c3c3c;color:#fff;border:1px solid #555;padding:4px;font:inherit}
 #logs{flex:1;overflow:auto;padding:6px;white-space:pre-wrap;word-break:break-all}
 button,label{background:#0e639c;color:#fff;border:0;padding:4px 10px;cursor:pointer;font:inherit}
 label{background:none;padding:0} #etat{min-width:90px}
 .b{font-weight:bold}.d{opacity:.6}
 .c90{color:#808080}.c91{color:#f14c4c}.c92{color:#23d18b}.c93{color:#f5f543}.c94{color:#3b8eea}.c95{color:#d670d6}.c96{color:#29b8db}
 .c32{color:#0dbc79}.c33{color:#e5e510}.c34{color:#2472c8}.c35{color:#bc3fbc}.c36{color:#11a8cd}
</style></head><body>
<div id="barre"><span id="etat">connexion...</span>
 <input id="cmd" placeholder="Commande Tasmota (Entree pour envoyer), ex. Status 4" autocomplete="off">
 <label><input type="checkbox" id="suivre" checked> defilement auto</label>
 <input id="filtre" placeholder="filtre (texte)" size="14" style="background:#3c3c3c;color:#fff;border:1px solid #555;padding:4px;font:inherit">
 <button id="effacer">Effacer</button></div>
<div id="logs"></div>
<script>
const logs=document.getElementById('logs'),etat=document.getElementById('etat'),suivre=document.getElementById('suivre'),filtre=document.getElementById('filtre');
let classes=[],reste='';
function echappe(t){return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function enHtml(t){  // codes ANSI SGR -> <span class=...>
  let h='',i=0;const re=/\\x1b\\[([0-9;]*)m/g;let m;
  while((m=re.exec(t))){h+=bout(t.slice(i,m.index));i=re.lastIndex;
    for(const c of (m[1]||'0').split(';')){ if(c==='0'||c==='')classes=[]; else if(c==='1')classes.push('b'); else if(c==='2')classes.push('d'); else {classes=classes.filter(x=>x[0]!=='c');classes.push('c'+c);} }}
  return h+bout(t.slice(i));}
function bout(t){return t?(classes.length?'<span class="'+classes.join(' ')+'">'+echappe(t)+'</span>':echappe(t)):'';}
function ajoute(texte){
  const lignes=(reste+texte).split('\\n');reste=lignes.pop();
  const f=filtre.value.toLowerCase(),frag=document.createElement('span');let h='';
  for(const l of lignes){const propre=l.replace(/\\x1b\\[[0-9;]*m/g,'');const html=enHtml(l.replace(/\\r/g,''))+'\\n';
    if(!f||propre.toLowerCase().includes(f))h+=html;}
  if(!h)return;
  frag.innerHTML=h;logs.appendChild(frag);
  while(logs.childNodes.length>3000)logs.removeChild(logs.firstChild);
  if(suivre.checked)logs.scrollTop=logs.scrollHeight;}
function connecte(){const es=new EventSource('/flux');
  es.onopen=()=>{etat.textContent='connecte';etat.style.color='#23d18b';};
  es.onmessage=e=>ajoute(JSON.parse(e.data));
  es.onerror=()=>{etat.textContent='deconnecte';etat.style.color='#f14c4c';};}
document.getElementById('cmd').addEventListener('keydown',e=>{if(e.key!=='Enter')return;const v=e.target.value.trim();if(!v)return;
  fetch('/cmd',{method:'POST',headers:{'X-Pont':'1'},body:v}).then(r=>{if(r.ok)e.target.value='';else alert('refuse : '+r.status);});});
document.getElementById('effacer').onclick=()=>{logs.innerHTML='';};
connecte();
</script></body></html>
"""


def _lit_requete(client):
    """Lit la ligne de requete, les en-tetes et le corps (Content-Length). Renvoie (methode, chemin, entetes, corps)."""
    donnees = b""
    while b"\r\n\r\n" not in donnees:
        morceau = client.recv(4096)
        if not morceau or len(donnees) > 65536:
            return None
        donnees += morceau
    tete, corps = donnees.split(b"\r\n\r\n", 1)
    lignes = tete.decode("latin-1").split("\r\n")
    try:
        methode, chemin, _ = lignes[0].split(" ", 2)
    except ValueError:
        return None
    entetes = {}
    for ligne in lignes[1:]:
        if ":" in ligne:
            cle, valeur = ligne.split(":", 1)
            entetes[cle.strip().lower()] = valeur.strip()
    longueur = min(int(entetes.get("content-length", "0") or 0), 4096)
    while len(corps) < longueur:
        morceau = client.recv(4096)
        if not morceau:
            break
        corps += morceau
    return methode, chemin.split("?", 1)[0], entetes, corps[:longueur]


def _reponse(client, statut, type_contenu="text/plain; charset=utf-8", corps=b""):
    client.sendall((f"HTTP/1.1 {statut}\r\nContent-Type: {type_contenu}\r\n"
                    f"Content-Length: {len(corps)}\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n").encode() + corps)


def evenement_sse(texte):
    """Un morceau de logs colores -> un evenement Server-Sent Events (JSON : garde \\n et codes ANSI)."""
    return f"data: {json.dumps(texte)}\n\n".encode("utf-8")


def traite(pont, client, port_tcp):
    """Sert UNE requete HTTP. Pour /flux, garde la connexion ouverte (client inscrit dans pont.clients_web)."""
    requete = _lit_requete(client)
    if requete is None:
        return
    methode, chemin, entetes, corps = requete

    if methode == "GET" and chemin == "/":
        titre = f"<title>Pont serie {getattr(pont.port, 'port', '')} (:{port_tcp})</title>"
        _reponse(client, "200 OK", "text/html; charset=utf-8", PAGE.replace("<title>Pont serie</title>", titre).encode("utf-8"))
    elif methode == "GET" and chemin == "/flux":
        client.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nCache-Control: no-store\r\n"
                       b"Connection: keep-alive\r\n\r\n")
        pont.inscrit_web(client)          # envoie l'historique puis le direct
        try:
            while client.recv(1024):       # le navigateur n'envoie rien : attend la fermeture
                pass
        except OSError:
            pass
        pont.desinscrit_web(client)
    elif methode == "POST" and chemin == "/cmd":
        origine = entetes.get("origin", "")
        if entetes.get("x-pont") != "1" or (origine and origine not in (f"http://127.0.0.1:{port_tcp}", f"http://localhost:{port_tcp}")):
            _reponse(client, "403 Forbidden", corps=b"refuse")
            return
        commande = corps.decode("utf-8", "replace").strip().replace("\r", " ").replace("\n", " ")
        if commande:
            pont.port.write((commande + "\n").encode("utf-8"))
            print(f"commande web -> carte : {commande}")
        _reponse(client, "204 No Content")
    else:
        _reponse(client, "404 Not Found", corps=b"introuvable")
