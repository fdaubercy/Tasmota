"""Lieu et puce d'une carte, tires du nom d'env ; table des lieux et JS de remplissage d'une liste par lieu."""

import fichiers_berry_etat as etat

LIEUX = [("etage2", "2e étage"), ("rdc", "Rez-de-chaussée"), ("cave", "Cave"),
         ("garage", "Garage"), ("bureau", "Bureau"), ("exterieur", "Extérieur")]
EXCEPTIONS = {"tasmota-pompe-piscine": "exterieur"}
PUCES = {"tasmota32": "ESP32", "tasmota32s3": "ESP32-S3", "tasmota32p4": "ESP32-P4",
         "tasmota32p4r3": "ESP32-P4", "tasmota": "ESP8266"}


def lieu(env):
    """None pour une base ou un nom sans tiret ; sinon l'exception ou le 2e segment (tel quel si hors table)."""
    if etat.est_base(env) or "-" not in env:
        return None
    return EXCEPTIONS.get(env) or env.split("-")[1]


def puce(env):
    seg = env.split("-")[0]
    return PUCES.get(seg, seg)


def pour_page():
    return {"lieux": [list(x) for x in LIEUX]}


def _serveur(chemin):
    """Bloc `serveur` d'un persist, au format actuel (`serveur`) ou ancien (`parametres.serveur`) ; {} sinon."""
    import json

    try:
        d = json.loads(chemin.read_text(encoding="utf-8"))
        s = d.get("serveur") or (d.get("parametres") or {}).get("serveur") or {}
    except (OSError, ValueError, AttributeError):
        return {}
    return s if isinstance(s, dict) else {}


def _identite(env, lieu_, serveur, ip, **plus):
    mqtt = serveur.get("mqtt")
    return {"env": env, "lieu": lieu_, "hote": str(serveur.get("hostname") or ""),
            "topic": str(mqtt.get("topic") or "") if isinstance(mqtt, dict) else "", "ip": ip, **plus}


def identites(racine):
    """Une identite par carte (famille « cartes ») : env, lieu, nom d'hote et topic du persist du depot, IP propre.
    Puis, marquees `sauvegarde: True`, celles des dossiers data/<lieu>/<nom>-sauvegarde/ (carte qui tourne encore
    l'ancien code, donc l'ancien topic) : ne sont PAS des cartes en plus, a ne pas compter."""
    import build_envs                                 # ici : fichiers_berry_etat importe build_envs (cycle)
    from pathlib import Path

    res = []
    noms = set()
    for e in build_envs.liste_envs(racine):
        if e.famille != "cartes":
            continue
        noms.add(e.nom)
        chemin = build_envs.persist_carte(racine, e.nom)
        res.append(_identite(e.nom, lieu(e.nom), _serveur(chemin) if chemin else {}, e.ip if e.ip_source == "h" else ""))
    vus = {(i["hote"], i["topic"]) for i in res}
    actifs = [i["topic"].lower() + "/" for i in res if i["topic"]]
    # -sauvegarde, -sauvegarde-2... (fichiers_berry_suppression::dossier_libre)
    for chemin in sorted((Path(racine) / "data").glob("*/*-sauvegarde*/_persist.json")):
        dossier, lieu_ = chemin.parent.name, chemin.parent.parent.name
        morceaux = dossier.rsplit("-sauvegarde", 1)[0].split("-")
        env = "-".join([morceaux[0], lieu_] + morceaux[1:])
        i = _identite(env if env in noms else dossier, lieu_, _serveur(chemin), "", sauvegarde=True)
        # un topic qui prolonge celui d'une carte active lui volerait ses messages (lieuDeTopic : le plus long gagne)
        if any((i["topic"].lower() + "/").startswith(a) for a in actifs):
            continue
        if (i["hote"], i["topic"]) not in vus:
            vus.add((i["hote"], i["topic"]))
            res.append(i)
    return res


def pour_page_identites(racine):
    """Reponse de GET /lieux : la table et les identites des cartes."""
    return {**pour_page(), "cartes": identites(racine)}


JS = r"""
function remplitParLieu(select, cartes, lieux, choisi, bases) {
  while (select.firstChild) select.removeChild(select.firstChild);
  const groupe = (label, liste) => {
    const g = document.createElement('optgroup');
    g.label = label;
    liste.forEach(c => {
      const o = document.createElement('option');
      o.value = c.nom;
      o.textContent = c.nom;
      g.appendChild(o);
    });
    select.appendChild(g);
  };
  const connus = lieux.map(l => l[0]);
  lieux.forEach(l => {
    const liste = cartes.filter(c => c.lieu === l[0]);
    if (liste.length) groupe(l[1], liste);
  });
  const autres = [];
  cartes.forEach(c => { if (connus.indexOf(c.lieu) < 0 && autres.indexOf(c.lieu) < 0) autres.push(c.lieu); });
  autres.forEach(code => groupe(code, cartes.filter(c => c.lieu === code)));
  if (bases && bases.length) groupe('Mes bases', bases);
  if (choisi) select.value = choisi;
  if (select.selectedIndex < 0) select.selectedIndex = 0;   // valeur disparue (env supprime) : premiere option, jamais une liste vide
}

function lieuDeHote(module, ipSource, cartes) {
  const m = String(module || '').toLowerCase();
  const parNom = cartes.find(c => c.hote && c.hote.toLowerCase() === m);
  if (parNom) return parNom.lieu;
  const parIp = ipSource ? cartes.find(c => c.ip && c.ip === ipSource) : null;
  return parIp ? parIp.lieu : null;
}

function lieuDeTopic(topic, cartes, nu) {
  const reste = nu ? String(topic || '') : String(topic || '').split('/').slice(1).join('/');
  let meilleure = null;
  cartes.forEach(c => {
    if (!c.topic) return;
    if ((reste === c.topic || reste.indexOf(c.topic + '/') === 0) && (!meilleure || c.topic.length > meilleure.topic.length)) meilleure = c;
  });
  return meilleure ? meilleure.lieu : null;
}

function lieuDemande(lieux) {
  const v = new URLSearchParams(location.search).get('lieu');
  return v && lieux.some(l => l[0] === v) ? v : null;
}

function bandeauLieu(parent, libelle, surFermeture) {
  const b = document.createElement('div');
  b.className = 'bandeau-lieu';
  b.appendChild(document.createTextNode('Lieu : ' + libelle + ' (depuis l’annuaire) · '));
  const x = document.createElement('button');
  x.type = 'button';
  x.textContent = 'Tous les lieux ✕';
  x.onclick = () => {
    const u = new URL(location.href);
    u.searchParams.delete('lieu');
    history.replaceState(null, '', u.pathname + u.search + u.hash);
    b.remove();
    surFermeture();
  };
  b.appendChild(x);
  parent.insertBefore(b, parent.firstChild);
  return b;
}
function libelleLieu(lieux, code) {
  const l = lieux.find(x => x[0] === code);
  return l ? l[1] : (code && code !== 'autres' ? code : 'Autres');
}

// Puces Tous / lieux / Autres d'une page de flux (syslog, sniffeur MQTT). opts : erreurs (compte aussi les erreurs),
// surChoix() (redessin de la page). Les comptes sont tenus PAR CLE (module|ip, topic) des la reception, pause comprise,
// et jamais decrementes ; un lieu = la somme de ses cles, recalculee quand /lieux arrive.
function pucesLieu(conteneur, opts) {
  const MAXC = 5000;
  const P = {cartes: [], lieux: [], choisi: '', puces: {}};
  let cles = new Map(), tot = {}, hors = {};
  const ajoute = (t, c, n, e) => { const x = t[c] || (t[c] = {n: 0, e: 0}); x.n += n; x.e += e; };
  const maj = code => {
    const p = P.puces[code], c = tot[code] || {n: 0, e: 0};
    if (!p) return;
    p.n.textContent = c.n;
    if (p.e) p.e.textContent = c.e ? ' ' + c.e + ' err' : '';
  };
  const codeDe = e => {
    const c = e.calcule(P.cartes);
    return P.lieux.some(x => x[0] === c) ? c : 'autres';
  };
  const ent = (cle, calcule) => {
    let e = cles.get(cle);
    if (!e) {
      e = {n: 0, e: 0, code: undefined, calcule, hors: cles.size >= MAXC};
      // shortcut: 5000 cles retenues (les cles viennent du reseau), au-dela le compte va au lieu du moment sans etre retenu
      // (non recalcule a l'arrivee de /lieux) ; a ameliorer si une page voit plus de 5000 modules ou topics distincts.
      if (!e.hors) cles.set(cle, e);
    }
    if (e.code === undefined) e.code = codeDe(e);
    return e;
  };
  P.libelle = code => libelleLieu(P.lieux, code);
  P.code = (cle, calcule) => ent(cle, calcule).code;
  P.compte = (cle, calcule, erreur) => {
    const e = ent(cle, calcule), x = erreur ? 1 : 0;
    e.n++; e.e += x;
    if (e.hors) ajoute(hors, e.code, 1, x);
    ajoute(tot, e.code, 1, x); ajoute(tot, '', 1, x);
    maj(e.code); maj('');
  };
  P.efface = () => { cles = new Map(); tot = {}; hors = {}; Object.keys(P.puces).forEach(maj); };
  P.choisit = code => {
    P.choisi = code;
    for (const k in P.puces) P.puces[k].bouton.classList.toggle('choisi', k === code);
    opts.surChoix();
  };
  const dessine = () => {
    const tete = document.createElement('span');
    tete.className = 'gris'; tete.textContent = 'Lieu';
    conteneur.replaceChildren(tete); P.puces = {};
    for (const [code, libelle] of [['', 'Tous'], ...P.lieux, ['autres', 'Autres']]) {
      const b = document.createElement('button'), n = document.createElement('span');
      const e = opts.erreurs ? document.createElement('span') : null;
      b.type = 'button'; b.className = 'puce'; b.dataset.lieu = code || 'tous'; n.className = 'n';
      b.append(libelle + ' ', n);
      if (e) { e.className = 'e'; b.append(e); }
      b.onclick = () => P.choisit(code === P.choisi ? '' : code);
      conteneur.appendChild(b); P.puces[code] = {bouton: b, n, e};
    }
  };
  // Reponse de GET /lieux : table et cartes, comptes recalcules d'apres les cles (pas d'apres le tampon), puces,
  // puis ?lieu= (premier chargement seulement, jamais memorise) : bandeau dans `parent` et choix.
  P.recoit = (d, parent) => {
    P.cartes = d.cartes; P.lieux = d.lieux;
    const anciennes = cles;
    cles = new Map(); tot = {};
    anciennes.forEach((e, cle) => {
      e.code = codeDe(e); cles.set(cle, e);
      ajoute(tot, e.code, e.n, e.e); ajoute(tot, '', e.n, e.e);
    });
    for (const c in hors) { ajoute(tot, c, hors[c].n, hors[c].e); ajoute(tot, '', hors[c].n, hors[c].e); }
    dessine(); Object.keys(P.puces).forEach(maj);
    const demande = lieuDemande(P.lieux);
    if (demande) { bandeauLieu(parent, P.libelle(demande), () => P.choisit('')); P.choisit(demande); }
    else P.choisit(P.choisi);
  };
  return P;
}
"""
