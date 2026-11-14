"""Organigramme des plans (tasks/plans/*.md) : donnees, page web (vue arbre) et PowerPoint.

Sources : l'en-tete de chaque plan (statut, objectif, famille, parent, liens, spec) + les dates du
premier et du dernier commit git du fichier (repli : cree/maj de l'en-tete) + le % des cases cochees.
Sorties dans outils_docs/organigramme_plans/ :
  plans.json                 donnees (relues par le script PowerPoint)
  index.html                 page autonome, clic sur un plan = detail, lien vers le plan et son spec
  organigramme-plans.pptx    synthese (frise) + une diapo par famille (necessite Node + pptxgenjs,
                             voir organigramme_pptx.mjs ; ignore avec un avertissement s'il manque)
Usage : python organigramme_plans.py [--verifier | --publier]
  --verifier : code 1 si les sorties sont en retard
  --publier  : pousse la page sur GitHub Pages (branche `etiquettes`, fichier organigramme.html, SANS forcer ; meme
               plomberie git que etiquettes_qr_publication : l'arbre de travail et `development` ne bougent pas).
               Adresses IPv4 masquees, robots noindex. Url : https://fdaubercy.github.io/Tasmota/organigramme.html
"""
import json
import os
import re
import subprocess
import sys

RACINE = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 3))
SORTIE = os.path.join(RACINE, "outils_docs", "organigramme_plans")
GITHUB = "https://github.com/fdaubercy/Tasmota/blob/development/"
URL_PAGES = "https://fdaubercy.github.io/Tasmota/organigramme.html"
FAMILLES = {  # cle de l'en-tete -> libelle ; l'ordre est celui des diapos
    "build": "Build et outils PC", "methode": "Méthode et audits", "modbus-reseau": "ModBus, réseau, matériel",
    "cave": "Cave et nouveaux envs", "debits-energie": "Débits et énergie", "graphiques-ecrans": "Graphiques, écrans, visuels"}


def _dates_git():
    """Un seul `git log` pour tous les plans : {chemin: (ajout, dernier)} ; le plus recent vient en premier."""
    r = subprocess.run(["git", "log", "--name-status", "--format=@%as", "--", "tasks/plans"],
                       capture_output=True, text=True, encoding="utf-8", cwd=RACINE)
    jour, dates = "", {}
    for ligne in r.stdout.splitlines():
        if ligne.startswith("@"):
            jour = ligne[1:]
        elif "	" in ligne:
            statut, chemin = ligne.split("	")[0], ligne.split("	")[-1]
            dernier, ajout = dates.get(chemin, (jour, ""))
            dates[chemin] = (dernier, jour if statut.startswith("A") else ajout)
    return dates


def lis_plan(nom, dates):
    chemin = f"tasks/plans/{nom}.md"
    t = open(os.path.join(RACINE, chemin), encoding="utf-8").read().replace("\r\n", "\n")
    m = re.match(r"---\n(.*?)\n---\n", t, re.S)
    meta = {}
    for ligne in m.group(1).split("\n"):
        k, _, v = ligne.partition(":")
        meta[k.strip()] = re.sub(r"\s+#\s.*$", "", v).strip()
    faites = len(re.findall(r"^\s*- \[x\]", t, re.M))
    total = faites + len(re.findall(r"^\s*- \[ \]", t, re.M))
    dernier, ajout = dates.get(chemin, ("", ""))
    liste = lambda c: [x.strip() for x in meta.get(c, "").split(",") if x.strip()]
    return {
        "nom": nom, "titre": meta.get("titre", nom), "objectif": meta.get("objectif", ""),
        "statut": meta.get("statut", "actif"), "famille": meta.get("famille", ""),
        "parent": meta.get("parent", ""), "liens": liste("liens"), "specs": liste("spec"),
        "cree": ajout or meta.get("cree", ""),
        "maj": max(dernier, meta.get("maj", "")),
        "pct": round(100 * faites / total) if total else 0, "etapes": f"{faites}/{total}",
        "url": GITHUB + chemin, "urls_spec": [GITHUB + "docs/superpowers/specs/" + s for s in liste("spec")]}


def donnees():
    noms = sorted(f[:-3] for f in os.listdir(os.path.join(RACINE, "tasks", "plans"))
                  if f.endswith(".md") and not f.startswith("_"))
    dates = _dates_git()
    plans = [lis_plan(n, dates) for n in noms]
    connus = {p["nom"] for p in plans}
    for p in plans:  # une cle de lien qui ne designe aucun plan est une faute de frappe : on la signale
        for q in p["liens"] + ([p["parent"]] if p["parent"] else []):
            if q not in connus:
                print(f"AVERTISSEMENT {p['nom']} : lien vers un plan inconnu « {q} »", file=sys.stderr)
        if p["famille"] not in FAMILLES:
            print(f"AVERTISSEMENT {p['nom']} : famille « {p['famille']} » inconnue", file=sys.stderr)
    return {"familles": FAMILLES, "plans": sorted(plans, key=lambda p: (p["cree"], p["nom"]))}


PAGE = r"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Organigramme des plans</title><style>
:root{--bg:#f6f7f9;--fg:#1b2430;--mut:#5d6877;--card:#fff;--line:#b9c2cf;--f0:#1f6fb2;--f1:#7a5cb8;--f2:#c0561e;--f3:#2a8a5a;--f4:#b08400;--f5:#c0397a}
@media (prefers-color-scheme:dark){:root{--bg:#12161c;--fg:#e6eaf0;--mut:#9aa5b4;--card:#1b222b;--line:#415064;--f0:#5aa6e8;--f1:#a68ae0;--f2:#ee8a52;--f3:#4fc08a;--f4:#e0b73a;--f5:#e66fa8}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.4 system-ui,sans-serif;padding:16px}
h1{font-size:20px;margin:0 0 4px}p.s{color:var(--mut);margin:0 0 12px}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}.bar button{font:inherit;padding:4px 10px;border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:6px;cursor:pointer}.bar button[aria-pressed=true]{background:var(--fg);color:var(--bg)}
.wrap{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:16px;align-items:start}@media(max-width:900px){.wrap{grid-template-columns:1fr}}
.fams{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.fam{background:var(--card);border:1px solid var(--line);border-top:4px solid var(--c);border-radius:8px;padding:10px 12px}
.fam h2{font-size:14px;margin:0 0 8px;color:var(--c)}
ul{list-style:none;margin:0;padding-left:16px;border-left:1px solid var(--line)}ul.r{padding-left:0;border:0}li{margin:4px 0}
.p{display:block;width:100%;text-align:left;font:inherit;padding:4px 8px;border:2px solid var(--c);border-radius:5px;background:var(--bg);color:var(--fg);cursor:pointer}
.p small{display:block;color:var(--mut);font-size:11px}.p.clos{opacity:.65;border-width:1px}.p.en-pause{border-style:dashed}.p.sel{outline:3px solid var(--fg)}.p.cache{display:none}
aside{position:sticky;top:12px;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}aside h2{font-size:16px;margin:0 0 4px}
aside a{color:inherit}.k{color:var(--mut);font-size:12px;margin-top:8px}.ch{display:inline-block;margin:2px 4px 2px 0;padding:1px 8px;border:1px solid var(--line);border-radius:10px;cursor:pointer;background:none;color:inherit;font:inherit;font-size:12px}
.b{height:6px;background:var(--line);border-radius:3px;margin:6px 0}.b i{display:block;height:100%;background:var(--fg);border-radius:3px}
</style></head><body><h1>Organigramme des plans</h1>
<p class="s" id="s"></p><div class="bar" id="bar"></div>
<div class="wrap"><div class="fams" id="fams"></div><aside id="d">Cliquez sur un plan pour voir son détail, son plan et son spec.</aside></div>
<script>const D=__DONNEES__;const P=Object.fromEntries(D.plans.map(p=>[p.nom,p]));
const K=Object.keys(D.familles);const fr=s=>s.slice(8)+'/'+s.slice(5,7);let filtre='tous';
document.getElementById('s').textContent=D.plans.length+' plans, '+D.plans.filter(p=>p.statut=='actif').length+' actifs. Parent = plan dont celui-ci découle ; liens = plans voisins.';
const bar=document.getElementById('bar');['tous','actif','clos','en-pause'].forEach(f=>{const b=document.createElement('button');b.textContent=f;b.setAttribute('aria-pressed',f==filtre);b.onclick=()=>{filtre=f;[...bar.children].forEach(x=>x.setAttribute('aria-pressed',x==b));document.querySelectorAll('.p').forEach(e=>e.classList.toggle('cache',f!='tous'&&P[e.dataset.n].statut!=f))};bar.appendChild(b)});
function noeud(p,fam){const li=document.createElement('li');const b=document.createElement('button');b.className='p '+p.statut;b.dataset.n=p.nom;b.innerHTML=p.nom+'<small>'+fr(p.cree)+' → '+fr(p.maj)+' · '+p.pct+' %</small>';b.onclick=()=>montre(p.nom);li.appendChild(b);
const fils=D.plans.filter(q=>q.parent==p.nom&&q.famille==fam);if(fils.length){const u=document.createElement('ul');fils.forEach(q=>u.appendChild(noeud(q,fam)));li.appendChild(u)}return li}
K.forEach((k,i)=>{const f=document.createElement('section');f.className='fam';f.style.setProperty('--c','var(--f'+i+')');f.innerHTML='<h2>'+D.familles[k]+'</h2>';const u=document.createElement('ul');u.className='r';
D.plans.filter(p=>p.famille==k&&!(p.parent&&P[p.parent]&&P[p.parent].famille==k)).forEach(p=>u.appendChild(noeud(p,k)));f.appendChild(u);document.getElementById('fams').appendChild(f)});
function montre(n){const p=P[n];document.querySelectorAll('.p').forEach(e=>e.classList.toggle('sel',e.dataset.n==n));
const ch=a=>a.map(q=>'<button class="ch" data-q="'+q+'">'+q+'</button>').join('')||'aucun';const voisins=D.plans.filter(q=>q.liens.includes(n)&&!p.liens.includes(q.nom)).map(q=>q.nom);
document.getElementById('d').innerHTML='<h2>'+p.titre+'</h2><div>'+p.statut+' · '+D.familles[p.famille]+'</div><div class="b"><i style="width:'+p.pct+'%"></i></div><div>'+p.pct+' % ('+p.etapes+' étapes)</div><div class="k">Créé / dernière modification</div>'+fr(p.cree)+' → '+fr(p.maj)+'<div class="k">Objectif</div>'+p.objectif+'<div class="k">Parent</div>'+(p.parent?ch([p.parent]):'aucun')+'<div class="k">Liens</div>'+ch(p.liens.concat(voisins))+'<div class="k">Détail</div><a href="'+p.url+'" target="_blank" rel="noopener">Ouvrir le plan</a>'+p.urls_spec.map(u=>'<br><a href="'+u+'" target="_blank" rel="noopener">Spec : '+u.split('/').pop()+'</a>').join('');
document.querySelectorAll('#d .ch[data-q]').forEach(b=>b.onclick=()=>montre(b.dataset.q))}
</script></body></html>"""


def page_html(d):
    return PAGE.replace("__DONNEES__", json.dumps(d, ensure_ascii=False).replace("</", "<\\/"))


def ecris(d):
    os.makedirs(SORTIE, exist_ok=True)
    texte = json.dumps(d, ensure_ascii=False, indent=1)
    page = page_html(d)
    sorties = {"plans.json": texte + "\n", "index.html": page}
    retard = []
    for nom, contenu in sorties.items():
        chemin = os.path.join(SORTIE, nom)
        ancien = open(chemin, encoding="utf-8").read() if os.path.exists(chemin) else None
        if ancien != contenu:
            retard.append(nom)
            if "--verifier" not in sys.argv:
                open(chemin, "w", encoding="utf-8", newline="\n").write(contenu)
    return retard


def publie_pages():
    """Page publique sur la branche `etiquettes` ; sha du commit, ou None si elle est deja a jour."""
    sys.path.insert(0, os.path.join(RACINE, "outils_docs", "scripts_python", "outils_pc"))
    import etiquettes_qr_publication as pub
    masque = lambda s: re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "[IP]", s)      # adresses du reseau local : pas en ligne
    page = masque(page_html(donnees())).replace("<title>", '<meta name="robots" content="noindex, nofollow"><title>', 1)
    pointe = pub._pointe(RACINE)
    arbre = pub._publies(RACINE, pointe)
    if arbre.get("organigramme.html") == page:
        return None
    arbre["organigramme.html"] = page
    arbre.setdefault(".nojekyll", "")
    entrees = "".join(f"100644 blob {pub._git(RACINE, 'hash-object', '-w', '--stdin', entree=c)}\t{n}\n"
                      for n, c in sorted(arbre.items()))
    commit = pub._git(RACINE, "commit-tree", pub._git(RACINE, "mktree", entree=entrees), *(["-p", pointe] if pointe else []),
                      "-m", "organigramme : page des plans")
    pub._git(RACINE, "push", "--quiet", "origin", f"{commit}:refs/heads/{pub.BRANCHE}")
    return commit


def pptx():
    script = os.path.join(os.path.dirname(__file__), "organigramme_pptx.mjs")
    r = subprocess.run(["node", script, os.path.join(SORTIE, "plans.json"),
                        os.path.join(SORTIE, "organigramme-plans.pptx")], capture_output=True, text=True)
    if r.returncode:
        print("AVERTISSEMENT PowerPoint non regenere :", (r.stderr or r.stdout).strip()[:300], file=sys.stderr)


if __name__ == "__main__":
    if "--publier" in sys.argv:
        sha = publie_pages()
        print("deja a jour" if not sha else f"publie : {sha[:9]} -> {URL_PAGES}")
        sys.exit(0)
    retard = ecris(donnees())
    if "--verifier" in sys.argv:
        print("organigramme en retard : " + ", ".join(retard) if retard else "organigramme a jour")
        sys.exit(1 if retard else 0)
    if retard:
        pptx()
    print("ecrit : " + (", ".join(retard) or "rien (a jour)"))
