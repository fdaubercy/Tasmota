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


def identites(racine):
    """Une identite par carte (famille « cartes ») : env, lieu, nom d'hote et topic du persist du depot, IP propre."""
    import build_envs                                 # ici : fichiers_berry_etat importe build_envs (cycle)
    import json

    res = []
    for e in build_envs.liste_envs(racine):
        if e.famille != "cartes":
            continue
        serveur = {}
        chemin = build_envs.persist_carte(racine, e.nom)
        try:
            serveur = json.loads(chemin.read_text(encoding="utf-8")).get("serveur") or {} if chemin else {}
        except (OSError, ValueError, AttributeError):
            serveur = {}
        mqtt = serveur.get("mqtt") if isinstance(serveur, dict) else None
        res.append({"env": e.nom, "lieu": lieu(e.nom),
                    "hote": str(serveur.get("hostname") or "") if isinstance(serveur, dict) else "",
                    "topic": str(mqtt.get("topic") or "") if isinstance(mqtt, dict) else "",
                    "ip": e.ip if e.ip_source == "h" else ""})
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
"""
