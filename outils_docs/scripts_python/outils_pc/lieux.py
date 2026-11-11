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
"""
