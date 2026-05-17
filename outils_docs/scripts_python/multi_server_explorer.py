"""
===========================================================
Multi-Server Explorer Python (Threaded & Web Interface)
===========================================================

- Multi-dossiers : mapper plusieurs chemins locaux à des URLs (/d1, /d2…)
- Mini-barre type explorateur avec breadcrumb
- Tri dynamique des colonnes (Nom / Taille / Modifié)
- Recherche instantanée
- Upload Drag & Drop + bouton "Choisir fichiers"
- Icônes selon le type de fichier (image, vidéo, PDF, texte, dossier)
- Dark / Light mode dynamique avec switch
- Pages d’erreur personnalisées
- Favicon intégré via Base64
- Port configurable (par défaut 80)
- Bouton "Arrêter le serveur" dans l’interface web
- Serveur lancé dans le thread principal pour que shutdown fonctionne

Utilisation en ligne de commande :
----------------------------------
python multi_server_explorer.py [param=value ...]

Paramètres possibles :
    ip=<IP>                Adresse IP du serveur (par défaut 0.0.0.0)
    port=<PORT>            Port HTTP (par défaut 80)
    dX=<chemin>            Dossiers à mapper (ex : d1="C:/site", d2="D:/partage")
    favicon=<chemin>       Fichier favicon (.ico) à utiliser

Exemple :
---------
python outils_docs/scripts_python/multi_server_explorer.py ip=0.0.0.0 port=80 d1="C:/mon_site" d2="D:/partage" favicon="C:/mon_site/favicon.ico"
python outils_docs/scripts_python/multi_server_explorer.py ip=0.0.0.0 port=80 d1=

Exemple dans un script Python dans un thread:
----------------------------------
    import sys
    import os
    import threading

    # Ajouter le chemin du dossier où se trouve multi_server_explorer.py
    server_folder = r"C:/Users/fdaub/Documents/Github/Tasmota/outils_docs/scripts_python"
    if server_folder not in sys.path:
        sys.path.append(server_folder)

    # Import du serveur
    from multi_server_explorer import run_server, MultiDirHandler

    # Paramètres du serveur
    ip = "0.0.0.0"
    port = 80
    mapping = {
        "/d1": r""
    }

    # Lancer le serveur dans un thread (non daemon pour que shutdown fonctionne) 
    server_thread = threading.Thread(target=run_server, kwargs={
        "ip": ip,
        "port": port,
        "mapping": mapping
    })
    server_thread.start()
    print(f"Serveur lancé dans un thread sur http://{ip}:{port}")

    # Thread pour gérer l'input console
    def input_thread():
        while True:
            cmd = input("Tapez 'exit' pour quitter le script principal : ")
            if cmd.strip().lower() == "exit":
                MultiDirHandler.SERVER_REF.shutdown()
                break

    threading.Thread(target=input_thread, daemon=True).start()

    # Attendre que le serveur se termine
    server_thread.join()
    print("Serveur arrêté, fin du script principal.")

Notes :
------
- Le bouton "Arrêter le serveur" arrête le serveur proprement via /stop
- Le script peut continuer à tourner grâce au threading
- Accessible sur le navigateur via http://<IP>:<PORT>/<dossier>

===========================================================
"""

import sys, os, mimetypes, re, base64
from http.server import SimpleHTTPRequestHandler, HTTPServer
from datetime import datetime
import threading

class MultiDirHandler(SimpleHTTPRequestHandler):
    MAPPING = {}
    SERVER_REF = None

    # Favicon intégré en Base64 (Tasmota)
    FAVICON_BASE64 = ("data:image/x-icon;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAQAAADZc7J/AAAABGdBTUEAALGPC/xhBQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAAmJLR0QA/4ePzL8AAAAJcEhZcwABOvYAATr2ATqxVzoAAAAHdElNRQfnAhAMAAoEg5UfAAACDklEQVRIx53Uz0tUURjG8Y+joWPUQsRVYlC0MVoUhJt+UIuICoSgQGvp3gKRMiihRYFJhNSyQIjoL6h9URBBQVCUhBpo0SYrvU3D3NPC6zB38g4zPnf13nOf73ncFTg0aVlFwy4ImC4LuBVBdX5blhpcK+12fBklFbMagkdh5bjFgSzNpfgVgxyS2RL4m91bQgMqyZFIBmwyLBI61lxB93aHfBqeQ2DvoheCyf1JUA8h4KfjiU1CeN2Ay58qzHBMuOl6eTBnDMb8H1ckZy5BALyez34ZNXmVF/bQa9WkAQrwLWtEkH5ixlApbMoSMJldX2K9WESJwJiEXV8c6llv+gu8ZfuF03IqX1AQXvsNOOTMAOOzGjkHWEl4q6nM0E9OtS9CxzXafnggVHkjo9xsMWBC90qqEBy4K3DvwH6PNGsOycmmo1oSj4oj8FOGpWUDSRBDnjDigYN6Vgm77U+116FEwZr7xAJJmq1C+XvXexKg2xD26btqJO9didOsJ2Pet/2JIBmKuqZ7N2+gdOlwJ7+sc9rAAAACV0RVh0ZGF0ZTpjcmVhdGUAMjAyMy0wMi0xNlQxMjowMDoxMCswMDowMKSeO0cAAAAldEVYdGRhdGU6bW9kaWZ5ADIwMjMtMDItMTZUMTI6MDA6MTArMDA6MDDVw4P7AAAAIHRFWHRzb2Z0d2FyZQBodHRwczovL2ltYWdlbWFnaWNrLm9yZ7zPHZ0AAAAYdEVYdFRodW1iOjpEb2N1bWVudDo6UGFnZXMAMaf/uy8AAAAYdEVYdFRodW1iOjpJbWFnZTo6SGVpZ2h0ADUxMAMTIwNjJCQn4+TlIAAABIdEVYdFRodW1iOjpVUkkAZmlsZTovLy4vdXBsb2Fkcy81Ni9ISzNSYlM1LzM5MTUvdGFzbW90YV9sb2dvX2ljb25fMjQ5NDQzLnBuZ2Kb4jAAAAAASUVORK5CYII=")

    ICONS = {
        "folder":"<svg width='20' height='20' viewBox='0 0 24 24'><path d='M3 7h4l2 3h12v9H3z'/></svg>",
        "image":"<svg width='20' height='20'><path d='M21 19V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2z'/><circle cx='8.5' cy='8.5' r='1.5'/><path d='M21 15l-5-5L5 21'/></svg>",
        "video":"<svg width='20' height='20'><polygon points='4,4 20,10 4,16'/></svg>",
        "pdf":"<svg width='20' height='20'><text x='0' y='15' font-size='15'>PDF</text></svg>",
        "text":"<svg width='20' height='20'><text x='0' y='15' font-size='15'>TXT</text></svg>",
        "other":"<svg width='20' height='20'><circle cx='10' cy='10' r='8'/></svg>"
    }

    # --- CORS ---
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    # --- Multi-dossiers ---
    def translate_path(self, path):
        for prefix, folder in self.MAPPING.items():
            if path.startswith(prefix):
                sub = path[len(prefix):] or "/"
                return os.path.join(folder, sub.lstrip("/\\"))
        return super().translate_path(path)

    # --- Upload POST simplifié ---
    def do_POST(self):
        content_type = self.headers.get('Content-Type','')
        if not content_type.startswith('multipart/form-data'):
            self.send_error(400,"Bad Request")
            return
        m = re.match(r'.*boundary=(.*)', content_type)
        if not m:
            self.send_error(400,"No boundary in multipart/form-data")
            return
        boundary = m.group(1).encode()
        length = int(self.headers.get('Content-Length',0))
        data = self.rfile.read(length)
        parts = data.split(b'--'+boundary)
        upload_path = None
        for prefix, folder in self.MAPPING.items():
            if self.path.startswith(prefix):
                upload_path = folder
                break
        if not upload_path:
            self.send_error(400,"Unknown upload path")
            return
        for part in parts:
            if b'Content-Disposition:' in part:
                try:
                    headers, file_data = part.split(b'\r\n\r\n',1)
                except ValueError:
                    continue
                file_data = file_data.rstrip(b'\r\n--')
                m = re.search(b'filename="(.+?)"', headers)
                if m:
                    filename = os.path.basename(m.group(1).decode(errors='ignore'))
                    if filename:
                        try:
                            with open(os.path.join(upload_path,filename),'wb') as f:
                                f.write(file_data)
                        except Exception as e:
                            print(f"Erreur écriture fichier : {e}")
        self.send_response(303)
        self.send_header('Location', self.path)
        self.end_headers()

    # --- Pages d’erreur ---
    def send_error(self, code, message=None, explain=None):
        self.send_response(code)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.end_headers()
        body=f"<html><head><title>{code} {message}</title></head><body style='background:#181818;color:#eee;padding:30px;font-family:Arial;'><h1>{code} - {message}</h1><hr><p>{explain or ''}</p></body></html>"
        try:
            self.wfile.write(body.encode('utf-8'))
        except:
            pass

    # --- GET requests ---
    def do_GET(self):
        if self.path=="/stop":
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Serveur arr\u00eat\u00e9.</h2></body></html>")
            threading.Thread(target=self.SERVER_REF.shutdown, daemon=True).start()
            return

        if self.path=="/favicon.ico":
            if self.FAVICON_BASE64:
                favicon_bytes = base64.b64decode(self.FAVICON_BASE64.split(",",1)[1])
                self.send_response(200)
                self.send_header("Content-Type","image/x-icon")
                self.send_header("Content-Length", str(len(favicon_bytes)))
                self.end_headers()
                try: self.wfile.write(favicon_bytes)
                except: pass
            else:
                self.send_response(204)
                self.end_headers()
            return

        return super().do_GET()

    # --- Index avec dark/light, upload, recherche, tri ---
    def list_directory(self,path):
        index_file=os.path.join(path,"index.html")
        if os.path.isfile(index_file):
            return open(index_file,"rb")
        try: entries=os.listdir(path)
        except OSError: self.send_error(404,"Répertoire inaccessible"); return None
        entries.sort(key=lambda x:x.lower())

        parts=self.path.strip("/").split("/")
        breadcrumb='<a href="/">root</a>'
        link_path=""
        for part in parts:
            if part:
                link_path+="/"+part
                breadcrumb+=f' / <a href="{link_path}">{part}</a>'

        html=["""<!DOCTYPE html><html><head><meta charset='utf-8'><title>Index</title>"""]
        if self.FAVICON_BASE64: html.append(f'<link rel="icon" type="image/x-icon" href="{self.FAVICON_BASE64}">')
        html.extend([
            "<style>body{font-family:Arial;padding:20px;transition:background 0.3s,color 0.3s;}table{width:100%;border-collapse:collapse;}th,td{padding:6px;text-align:left;border-bottom:1px solid #444;}th{cursor:pointer;}a{color:inherit;text-decoration:none;}#dropzone{border:2px dashed #6ab0ff;padding:20px;text-align:center;margin-bottom:10px;}#search{margin-bottom:10px;padding:6px;width:50%;}</style>",
            "<script>",
            "function updateTheme(){let t=document.body.dataset.theme||'dark';if(t==='dark'){document.body.style.background='#181818';document.body.style.color='#eee';}else{document.body.style.background='#f8f8f8';document.body.style.color='#222';}}",
            "function toggleTheme(){let c=document.body.dataset.theme||'dark';let n=c==='dark'?'light':'dark';document.body.dataset.theme=n;localStorage.setItem('theme',n);updateTheme();}",
            "function sortTable(n){let t=document.getElementById('ftable');let r=Array.from(t.rows).slice(1);r.sort((a,b)=>a.cells[n].innerText.localeCompare(b.cells[n].innerText));for(let x of r)t.appendChild(x);}",
            "function filterFiles(){let q=document.getElementById('search').value.toLowerCase();let t=document.getElementById('ftable');for(let r of t.rows){if(r.rowIndex===0) continue;let n=r.cells[0].innerText.toLowerCase();r.style.display=n.includes(q)?'':'none';}}",
            "function stopServer(){if(confirm('Voulez-vous vraiment arrêter le serveur ?')){fetch('/stop').then(_=>alert('Serveur arrêté')).catch(e=>alert('Erreur : '+e));}}",
            "window.addEventListener('DOMContentLoaded',()=>{document.body.dataset.theme=localStorage.getItem('theme')||'dark';updateTheme();let dz=document.getElementById('dropzone');dz.ondragover=e=>{e.preventDefault();dz.style.background='#444';};dz.ondragleave=e=>{dz.style.background='';};dz.ondrop=e=>{e.preventDefault();dz.style.background='';let f=new FormData();for(let x of e.dataTransfer.files)f.append('file',x);fetch(window.location.pathname,{method:'POST',body:f}).then(()=>location.reload());};});",
            "</script></head><body>",
            "<button onclick='toggleTheme()'>Toggle Dark/Light</button> ",
            "<button onclick='stopServer()'>Arrêter le serveur</button>",
            f"<div>{breadcrumb}</div><hr>",
            "<input type='text' id='search' onkeyup='filterFiles()' placeholder='Rechercher...'>",
            "<div id='dropzone'>Glisser & déposer des fichiers ici ou utilisez le bouton ci‑dessous</div>",
            "<form method='POST' enctype='multipart/form-data'><input type='file' name='file' multiple><input type='submit' value='Upload'></form><hr>",
            "<table id='ftable'><tr><th onclick='sortTable(0)'>Name</th><th onclick='sortTable(1)'>Size</th><th onclick='sortTable(2)'>Modified</th></tr>"
        ])

        for name in entries:
            full=os.path.join(path,name)
            link=name+"/" if os.path.isdir(full) else name
            if os.path.isdir(full): icon=self.ICONS["folder"]
            else:
                mime=mimetypes.guess_type(full)[0] or ""
                if mime.startswith("image"): icon=self.ICONS["image"]
                elif mime.startswith("video"): icon=self.ICONS["video"]
                elif mime=="application/pdf": icon=self.ICONS["pdf"]
                elif mime.startswith("text"): icon=self.ICONS["text"]
                else: icon=self.ICONS["other"]
            size="" if os.path.isdir(full) else f"{os.path.getsize(full)} B"
            mtime=datetime.fromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d %H:%M")
            html.append(f"<tr><td><a href='{link}'>{icon} {name}</a></td><td>{size}</td><td>{mtime}</td></tr>")

        html.append("</table></body></html>")
        html_bytes="\n".join(html).encode('utf-8')
        try: self.wfile.write(html_bytes)
        except: pass
        return None

def run_server(ip="0.0.0.0", port=80, mapping=None):
    server=HTTPServer((ip,port),MultiDirHandler)
    MultiDirHandler.MAPPING=mapping or {}
    MultiDirHandler.SERVER_REF=server
    print(f"Serveur lancé sur http://{ip}:{port} (visiter /stop ou bouton pour arrêter)")
    for url,path in MultiDirHandler.MAPPING.items():
        print(f"  {url} → {path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
    print("Serveur arrêté.")

if __name__=="__main__":
    ip, port, mapping = "0.0.0.0", 80, {}
    for arg in sys.argv[1:]:
        if "=" not in arg: continue
        key, value = arg.split("=",1)
        key,value = key.strip().lower(), value.strip().strip('"')
        if key=="ip": ip=value
        elif key=="port": port=int(value)
        else: mapping["/"+key]=value

    # Thread pour gérer l'input console
    def input_thread():
        while True:
            cmd = input("Tapez 'exit' pour quitter… ")
            if cmd.strip().lower() == "exit":
                MultiDirHandler.SERVER_REF.shutdown()
                break
    threading.Thread(target=input_thread, daemon=True).start()

    # Lancement du serveur dans le thread principal
    run_server(ip, port, mapping)
