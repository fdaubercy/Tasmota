"""Petit serveur HTTP du pont serie (pont_serie.py), sur le MEME port que le TCP brut.

Le pont reconnait une requete HTTP a ses premiers octets ("GET ", "POST") et la confie ici :
    GET  /        page des logs colores + commandes du port serie (http://127.0.0.1:7000)
    GET  /flux    flux en direct (Server-Sent Events) : etat du port, historique, puis la suite.
                  Evenements : message (texte colore), 'note' (messages du pont, echo des envois),
                  'octets' (octets bruts recus, en hexa : vue Reception = Hex), 'etat'.
    GET  /etat    etat du port serie + ports presents (reliste les ports a chaque appel)
    POST /ouvrir  corps JSON {"port": "COM11", "vitesse": 115200} : ouvre (ou rouvre) le port serie
    POST /fermer  ferme le port serie (le libere pour un flash) ; le serveur et la page restent en marche
    POST /cmd     corps = commande Tasmota, transmise a la carte (ex. "Status 4") suivie de \\n
    POST /envoi   corps JSON, sur le modele du moniteur serie de VS Code :
                  {"mode": "texte", "donnees": "Status 4", "finLigne": "aucune|LF|CR|CRLF"}
                  {"mode": "hex", "donnees": "01 06 00 01 01 00", "crc": true}   (CRC16 ModBus ajoute)
                  {"mode": "binaire", "donnees": "00000001 00000110", "crc": false}
    POST /terminal lance un terminal supplementaire (pont secondaire, port serie ferme) sur le premier
                  port TCP libre ; reponse JSON {"url": "http://127.0.0.1:7001/"}, que la page ouvre
                  dans un nouvel onglet (bouton « + Terminal »)

Securite : le pont n'ecoute que sur 127.0.0.1. Contre une page web malveillante qui viserait
127.0.0.1:7000 depuis le navigateur, chaque POST exige l'en-tete 'X-Pont: 1' (un en-tete personnalise
declenche une requete CORS preliminaire, a laquelle on ne repond pas) et refuse une autre Origine.
"""

import json
import re
import string
import time

FINS_LIGNE = {"aucune": b"", "LF": b"\n", "CR": b"\r", "CRLF": b"\r\n"}
MAX_ENVOI = 1024        # octets par envoi

PAGE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Pont serie</title>
<style>
 body{margin:0;background:#1e1e1e;color:#d4d4d4;font:13px Consolas,monospace;display:flex;flex-direction:column;height:100vh}
 .barre{display:flex;flex-wrap:wrap;gap:8px;padding:6px;background:#252526;border-bottom:1px solid #333;align-items:center}
 input,select{background:#3c3c3c;color:#fff;border:1px solid #555;padding:4px;font:inherit}
 input:disabled,select:disabled{opacity:.5}
 #cmd{flex:1;min-width:200px}
 #logs{flex:1;overflow:auto;padding:6px;white-space:pre-wrap;word-break:break-all}
 button{background:#0e639c;color:#fff;border:0;padding:4px 10px;cursor:pointer;font:inherit}
 button:disabled{opacity:.5;cursor:default}
 #bascule.ouvert{background:#a1260d} #bascule.ferme{background:#16825d}
 .pastille{display:inline-block;width:10px;height:10px;border-radius:50%;background:#808080;margin-right:4px}
 #infoPort,#nomPont{color:#9d9d9d}
 .b{font-weight:bold}.d{opacity:.6}
 .c90{color:#808080}.c91{color:#f14c4c}.c92{color:#23d18b}.c93{color:#f5f543}.c94{color:#3b8eea}.c95{color:#d670d6}.c96{color:#29b8db}
 .c32{color:#0dbc79}.c33{color:#e5e510}.c34{color:#2472c8}.c35{color:#bc3fbc}.c36{color:#11a8cd}
</style></head><body>
<div class="barre">
 <span title="liaison page <-> pont"><span class="pastille" id="pastilleWeb"></span><span id="etatWeb">connexion...</span></span>
 <label>Port <select id="port" title="ports serie presents (USB d'abord)"></select></label>
 <button id="rafraichir" title="relister les ports serie">&#x21bb;</button>
 <label>Vitesse <select id="vitesse"></select></label>
 <button id="bascule" class="ferme">Demarrer</button>
 <span><span class="pastille" id="pastillePort"></span><span id="infoPort">port ferme</span></span>
 <span style="flex:1"></span>
 <span id="nomPont" title="port TCP de ce terminal (http://127.0.0.1:port)"></span>
 <button id="nouveau" title="ouvre un terminal supplementaire, avec ses propres reglages (autre ESP32)">+ Terminal</button>
</div>
<div class="barre">
 <select id="modeEnvoi" title="format de la saisie envoyee"><option value="texte">Texte</option><option value="hex">Hex</option><option value="binaire">Binaire</option></select>
 <input id="cmd" autocomplete="off" title="Entree pour envoyer ; fleches haut/bas : historique">
 <select id="finLigne" title="fin de ligne ajoutee en mode Texte"><option value="aucune">Aucune</option><option value="LF" selected>LF</option><option value="CR">CR</option><option value="CRLF">CRLF</option></select>
 <label id="blocCrc" title="ajoute les 2 octets du CRC16 ModBus a la fin"><input type="checkbox" id="crc"> CRC ModBus</label>
</div>
<div class="barre">
 <label>Reception <select id="recep" title="affichage des octets recus"><option value="texte">Texte</option><option value="hex">Hex</option></select></label>
 <input id="filtre" placeholder="filtre (texte)" size="14">
 <label><input type="checkbox" id="suivre" checked> defilement auto</label>
 <button id="effacer">Effacer</button>
</div>
<div id="logs"></div>
<script>
const $=id=>document.getElementById(id);
const logs=$('logs'),suivre=$('suivre'),filtre=$('filtre'),selPort=$('port'),selVitesse=$('vitesse'),bascule=$('bascule'),cmd=$('cmd');
const modeEnvoi=$('modeEnvoi'),finLigne=$('finLigne'),crc=$('crc'),recep=$('recep');
let classes=[],reste='',etat={ouvert:false},tampon=[],historique=[],posHisto=0;
const AIDES={texte:'Commande Tasmota (Entree pour envoyer), ex. Status 4',
  hex:'Octets en hexadecimal (Entree pour envoyer), ex. 01 06 00 01 01 00',
  binaire:'Octets en binaire (Entree pour envoyer), ex. 00000001 00000110'};
function lit(cle,defaut){try{return localStorage.getItem('pont.'+cle)||defaut;}catch(e){return defaut;}}
function ecrit(cle,valeur){try{localStorage.setItem('pont.'+cle,valeur);}catch(e){}}
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
function enHex(o){  // octets recus -> lignes de 16 octets : heure, hexa, ASCII
  const oct=o.hex.match(/../g)||[];let s='';
  for(let i=0;i<oct.length;i+=16){const p=oct.slice(i,i+16);
    const asc=p.map(x=>{const c=parseInt(x,16);return c>=32&&c<127?String.fromCharCode(c):'.';}).join('');
    s+='\\x1b[90m'+o.t+'\\x1b[0m \\x1b[92mRX\\x1b[0m '+p.join(' ').toUpperCase().padEnd(47)+'  |'+asc+'|\\n';}
  return s;}
// k : 'm' texte de la carte, 'n' note du pont (toujours visible), 'o' octets bruts (vue Hex)
function visible(k){return k==='n'||(k==='m')===(recep.value==='texte');}
function affiche(k,d){ajoute(k==='o'?enHex(d):d);}
function recoit(k,d){tampon.push([k,d]);if(tampon.length>6000)tampon.splice(0,1000);if(visible(k))affiche(k,d);}
function redessine(){logs.innerHTML='';classes=[];reste='';for(const [k,d] of tampon)if(visible(k))affiche(k,d);}
function majModeEnvoi(){const m=modeEnvoi.value;cmd.placeholder=AIDES[m];
  finLigne.style.display=m==='texte'?'':'none';$('blocCrc').style.display=m==='texte'?'none':'';}
function remplitPorts(e){
  const choisi=selPort.value||e.port;selPort.innerHTML='';
  const ports=e.ports.slice();
  if(e.port&&!ports.some(p=>p.port===e.port))ports.unshift({port:e.port,description:'(port courant)',usb:false});
  if(!ports.length){const o=new Option('aucun port detecte','');selPort.add(o);}
  for(const p of ports)selPort.add(new Option(p.port+' - '+p.description+(p.usb?' (USB)':''),p.port));
  if([...selPort.options].some(o=>o.value===(e.ouvert?e.port:choisi)))selPort.value=e.ouvert?e.port:choisi;}
function remplitVitesses(e){
  const choisie=selVitesse.value||String(e.vitesse);selVitesse.innerHTML='';
  const vs=e.vitesses.slice();if(!vs.includes(e.vitesse))vs.push(e.vitesse);vs.sort((a,b)=>a-b);
  for(const v of vs)selVitesse.add(new Option(v+' bauds',String(v)));
  selVitesse.value=e.ouvert?String(e.vitesse):choisie;}
function appliqueEtat(e){
  etat=e;remplitPorts(e);remplitVitesses(e);
  selPort.disabled=selVitesse.disabled=e.ouvert;cmd.disabled=!e.ouvert;
  bascule.textContent=e.ouvert?'Arreter':'Demarrer';bascule.className=e.ouvert?'ouvert':'ferme';
  bascule.disabled=!e.ouvert&&!selPort.value;
  $('pastillePort').style.background=e.ouvert?'#23d18b':'#808080';
  $('infoPort').textContent=e.ouvert?(e.port+' @ '+e.vitesse+' bauds'):'port ferme';
  $('nomPont').textContent='terminal :'+e.tcp;
  document.title='Pont serie '+(e.ouvert?e.port:'(ferme)')+' (:'+e.tcp+')';}
function poste(url,corps){return fetch(url,{method:'POST',headers:{'X-Pont':'1','Content-Type':'application/json'},body:corps===undefined?'':corps})
  .then(r=>r.text().then(t=>{if(!r.ok)ajoute('\\x1b[91m[page] '+(t||r.status)+'\\x1b[0m\\n');return r.ok;}));}
function releve(){return fetch('/etat').then(r=>r.json()).then(appliqueEtat);}
bascule.onclick=()=>{bascule.disabled=true;
  (etat.ouvert?poste('/fermer'):poste('/ouvrir',JSON.stringify({port:selPort.value,vitesse:parseInt(selVitesse.value)})))
  .finally(()=>releve());};
$('rafraichir').onclick=releve;
$('nouveau').onclick=()=>{  // onglet ouvert DANS le clic (sinon bloque comme popup), dirige une fois le pont pret
  const w=window.open('','_blank');$('nouveau').disabled=true;
  try{w.document.title='Pont serie';w.document.body.style.cssText='background:#1e1e1e;color:#d4d4d4;font:13px Consolas,monospace';
    w.document.body.textContent='lancement du terminal...';}catch(e){}
  fetch('/terminal',{method:'POST',headers:{'X-Pont':'1'}})
  .then(r=>r.ok?r.json():r.text().then(t=>{throw new Error(t||r.status);}))
  .then(d=>{if(w)w.location=d.url;else ajoute('\\x1b[93m[page] onglet bloque : ouvrir '+d.url+'\\x1b[0m\\n');})
  .catch(e=>{if(w)w.close();ajoute('\\x1b[91m[page] '+e.message+'\\x1b[0m\\n');})
  .finally(()=>{$('nouveau').disabled=false;});};
selPort.addEventListener('focus',()=>{if(!etat.ouvert)releve();});
selPort.addEventListener('change',()=>{bascule.disabled=!selPort.value;});
cmd.addEventListener('keydown',e=>{
  if(e.key==='ArrowUp'||e.key==='ArrowDown'){if(!historique.length)return;e.preventDefault();
    posHisto=Math.max(0,Math.min(historique.length,posHisto+(e.key==='ArrowUp'?-1:1)));
    cmd.value=historique[posHisto]||'';return;}
  if(e.key!=='Enter')return;const v=cmd.value;if(!v.trim())return;
  const corps={mode:modeEnvoi.value,donnees:v,finLigne:finLigne.value,crc:crc.checked};
  poste('/envoi',JSON.stringify(corps)).then(ok=>{if(!ok)return;
    if(historique[historique.length-1]!==v)historique.push(v);if(historique.length>100)historique.shift();
    posHisto=historique.length;cmd.value='';});});
for(const [el,cle] of [[modeEnvoi,'mode'],[finLigne,'fin'],[recep,'recep']]){el.value=lit(cle,el.value);
  el.addEventListener('change',()=>{ecrit(cle,el.value);if(el===recep)redessine();else majModeEnvoi();cmd.focus();});}
crc.checked=lit('crc','0')==='1';crc.addEventListener('change',()=>ecrit('crc',crc.checked?'1':'0'));
majModeEnvoi();
$('effacer').onclick=()=>{logs.innerHTML='';tampon=[];classes=[];reste='';};
function connecte(){const es=new EventSource('/flux');
  es.onopen=()=>{$('etatWeb').textContent='pont connecte';$('pastilleWeb').style.background='#23d18b';};
  es.onmessage=e=>recoit('m',JSON.parse(e.data));
  es.addEventListener('note',e=>recoit('n',JSON.parse(e.data)));
  es.addEventListener('octets',e=>recoit('o',JSON.parse(e.data)));
  es.addEventListener('etat',e=>appliqueEtat(JSON.parse(e.data)));
  es.onerror=()=>{$('etatWeb').textContent='pont injoignable';$('pastilleWeb').style.background='#f14c4c';};}
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


def _texte(client, statut, message):
    _reponse(client, statut, corps=message.encode("utf-8"))


def evenement_sse(texte):
    """Un morceau de logs colores -> un evenement Server-Sent Events (JSON : garde \\n et codes ANSI)."""
    return f"data: {json.dumps(texte)}\n\n".encode("utf-8")


def evenement_etat(etat):
    """Etat du port serie -> evenement SSE nomme 'etat' (met a jour les commandes de toutes les pages)."""
    return f"event: etat\ndata: {json.dumps(etat)}\n\n".encode("utf-8")


def evenement_note(texte):
    """Message du pont (etat du port, echo d'un envoi) : affiche quelle que soit la vue de reception."""
    return f"event: note\ndata: {json.dumps(texte)}\n\n".encode("utf-8")


def evenement_octets(octets):
    """Octets bruts recus, horodates a la milliseconde -> evenement SSE 'octets' (vue Reception = Hex)."""
    instant = time.time()
    heure = time.strftime("%H:%M:%S", time.localtime(instant)) + f".{int(instant % 1 * 1000):03d}"
    return f"event: octets\ndata: {json.dumps({'t': heure, 'hex': octets.hex()})}\n\n".encode("utf-8")


# ---------------------------------------------------------------------- envoi (texte / hex / binaire)
def crc_modbus(octets):
    """CRC16 ModBus (polynome 0xA001, depart 0xFFFF), octet de poids faible en premier."""
    crc = 0xFFFF
    for octet in octets:
        crc ^= octet
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return bytes((crc & 0xFF, crc >> 8))


def _jetons(texte):
    return [jeton for jeton in re.split(r"[\s,;:]+", texte.strip()) if jeton]


def octets_hex(texte):
    """'01 06 0001', '0x01,0x06', '1 6' -> octets. Un jeton de plus de 2 chiffres doit en avoir un nombre pair."""
    resultat = bytearray()
    for jeton in _jetons(texte):
        chiffres = jeton[2:] if jeton.lower().startswith("0x") else jeton
        if not chiffres or any(c not in string.hexdigits for c in chiffres) or (len(chiffres) > 2 and len(chiffres) % 2):
            raise ValueError(f"hexadecimal invalide : '{jeton}'")
        resultat += bytes.fromhex(chiffres.zfill(2))
    return bytes(resultat)


def octets_binaires(texte):
    """'00000001 00000110', '0b101' -> octets. Un jeton de plus de 8 bits doit en avoir un multiple de 8."""
    resultat = bytearray()
    for jeton in _jetons(texte):
        bits = jeton[2:] if jeton.lower().startswith("0b") else jeton
        if not bits or set(bits) - {"0", "1"} or (len(bits) > 8 and len(bits) % 8):
            raise ValueError(f"binaire invalide : '{jeton}' (groupes de 8 bits au plus)")
        resultat += bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8)) if len(bits) > 8 else bytes((int(bits, 2),))
    return bytes(resultat)


def prepare_envoi(demande):
    """Corps JSON de /envoi -> (octets a ecrire, description pour l'echo). ValueError si la saisie est invalide."""
    if not isinstance(demande, dict):
        raise ValueError("corps JSON attendu")
    mode, donnees = demande.get("mode", "texte"), str(demande.get("donnees", ""))
    if mode == "texte":
        nom_fin = demande.get("finLigne", "LF")
        if nom_fin not in FINS_LIGNE:
            raise ValueError(f"fin de ligne inconnue : {nom_fin}")
        texte = donnees.replace("\r", " ").replace("\n", " ")
        octets = texte.encode("utf-8") + FINS_LIGNE[nom_fin]
        description = f"texte : {texte}" + (f" + {nom_fin}" if FINS_LIGNE[nom_fin] else "")
    elif mode in ("hex", "binaire"):
        octets = octets_hex(donnees) if mode == "hex" else octets_binaires(donnees)
        if not octets:
            raise ValueError("aucun octet a envoyer")
        suite = ""
        if demande.get("crc") is True:
            somme = crc_modbus(octets)
            octets += somme
            suite = f", CRC ModBus {somme.hex(' ').upper()} ajoute"
        description = f"{mode} : {octets.hex(' ').upper()} ({len(octets)} octets{suite})"
    else:
        raise ValueError(f"mode inconnu : {mode} (texte, hex ou binaire)")
    if not octets or len(octets) > MAX_ENVOI:
        raise ValueError(f"envoi vide ou trop long (1 a {MAX_ENVOI} octets)")
    return octets, description


def _autorise(entetes, port_tcp):
    """POST accepte seulement depuis la page du pont (en-tete X-Pont, meme origine)."""
    origine = entetes.get("origin", "")
    return entetes.get("x-pont") == "1" and (
        not origine or origine in (f"http://127.0.0.1:{port_tcp}", f"http://localhost:{port_tcp}"))


def traite(pont, client, port_tcp):
    """Sert UNE requete HTTP. Pour /flux, garde la connexion ouverte (client inscrit dans pont.clients_web)."""
    requete = _lit_requete(client)
    if requete is None:
        return
    methode, chemin, entetes, corps = requete

    if methode == "GET" and chemin == "/":
        _reponse(client, "200 OK", "text/html; charset=utf-8", PAGE.encode("utf-8"))
    elif methode == "GET" and chemin == "/etat":
        _reponse(client, "200 OK", "application/json", json.dumps(pont.etat()).encode("utf-8"))
    elif methode == "GET" and chemin == "/flux":
        client.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nCache-Control: no-store\r\n"
                       b"Connection: keep-alive\r\n\r\n")
        pont.inscrit_web(client)          # envoie l'etat, l'historique, puis le direct
        try:
            while client.recv(1024):       # le navigateur n'envoie rien : attend la fermeture
                pass
        except OSError:
            pass
        pont.desinscrit_web(client)
    elif methode == "POST" and chemin in ("/ouvrir", "/fermer", "/cmd", "/envoi", "/terminal"):
        if not _autorise(entetes, port_tcp):
            _texte(client, "403 Forbidden", "refuse")
            return
        if chemin == "/terminal":
            ok, resultat = pont.lance_terminal()
            if ok:
                _reponse(client, "200 OK", "application/json",
                         json.dumps({"url": f"http://127.0.0.1:{resultat}/"}).encode("utf-8"))
            else:
                _texte(client, "503 Service Unavailable", resultat)
        elif chemin == "/fermer":
            _texte(client, "200 OK", pont.ferme()[1])
        elif chemin == "/ouvrir":
            try:
                demande = json.loads(corps.decode("utf-8") or "{}")
                port, vitesse = str(demande["port"]).strip(), int(demande["vitesse"])
                if not port or len(port) > 200 or not 50 <= vitesse <= 5000000:
                    raise ValueError
            except (ValueError, KeyError, TypeError):
                _texte(client, "400 Bad Request", "attendu : {\"port\": \"COM11\", \"vitesse\": 115200}")
                return
            ok, message = pont.ouvre(port, vitesse)
            _texte(client, "200 OK" if ok else "409 Conflict", message)
        elif chemin == "/envoi":
            try:
                octets, description = prepare_envoi(json.loads(corps.decode("utf-8") or "{}"))
            except (ValueError, TypeError) as erreur:      # JSONDecodeError herite de ValueError
                _texte(client, "400 Bad Request", str(erreur))
                return
            if not pont.ecrit(octets):
                _texte(client, "409 Conflict", "port serie ferme : cliquer sur Demarrer")
                return
            print(f"envoi web -> carte : {description}")
            pont.diffuse(f"\x1b[95m[envoi] {description}\x1b[0m\n", note=True)
            _reponse(client, "204 No Content")
        else:
            commande = corps.decode("utf-8", "replace").strip().replace("\r", " ").replace("\n", " ")
            if commande and not pont.ecrit((commande + "\n").encode("utf-8")):
                _texte(client, "409 Conflict", "port serie ferme : cliquer sur Demarrer")
                return
            if commande:
                print(f"commande web -> carte : {commande}")
            _reponse(client, "204 No Content")
    else:
        _texte(client, "404 Not Found", "introuvable")
