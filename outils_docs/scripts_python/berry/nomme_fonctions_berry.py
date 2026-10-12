"""Convertit les fonctions anonymes d'un module Berry en fonctions nommees.

    AVANT :  modbusFonctions.log = def(msg, level)
                 ...corps...
             end

    APRES :  def modbusFonctions_log(msg, level)
                 ...corps...
             end
             modbusFonctions.log = modbusFonctions_log

Pourquoi : le solidifieur nomme TOUTE fonction anonyme `_anonymous_`. Avec N
fonctions, on obtient N symboles C `_anonymous__closure` identiques dans le meme
fichier -> `error: redefinition`. Une fonction nommee donne un symbole unique.

Le prefixe (nom du module) est indispensable : ces noms deviennent des globaux
Berry, et `log` seul ecraserait la fonction log() de Tasmota.

Repere de fin de fonction : ces declarations sont en colonne 0, donc leur `end`
est le premier `end` en colonne 0 rencontre ensuite. Le script VERIFIE cette
hypothese pour chaque fonction et s'arrete si elle est fausse.

Usage : python convertit_module.py <fichier.be> [--ecrire]
        sans --ecrire : montre seulement ce qui serait fait.
"""
import re
import sys
from pathlib import Path

cible = Path(sys.argv[1])
ecrire = "--ecrire" in sys.argv

lignes = cible.read_text(encoding="utf-8").splitlines(keepends=True)
nom_module = cible.stem

# Declaration anonyme, en colonne 0 : <module>.<fn> = def(...)
DECL = re.compile(rf"^{re.escape(nom_module)}\.(\w+)\s*=\s*def\s*\((.*)\)\s*$")

sortie = []
conversions = []
i = 0
echecs = []

while i < len(lignes):
    ligne = lignes[i]
    m = DECL.match(ligne.rstrip("\n"))
    if not m:
        sortie.append(ligne)
        i += 1
        continue

    fn, args = m.group(1), m.group(2)
    nouveau = f"{nom_module}_{fn}"

    # Cherche le `end` en colonne 0 qui ferme cette fonction.
    j = i + 1
    fin = None
    while j < len(lignes):
        if lignes[j].rstrip("\n") == "end":
            fin = j
            break
        # Un autre `def` en colonne 0 avant le `end` = hypothese fausse.
        if DECL.match(lignes[j].rstrip("\n")):
            break
        j += 1

    if fin is None:
        echecs.append((i + 1, fn, "aucun `end` en colonne 0 trouve"))
        sortie.append(ligne)
        i += 1
        continue

    sortie.append(f"def {nouveau}({args})\n")
    sortie.extend(lignes[i + 1:fin + 1])
    sortie.append(f"{nom_module}.{fn} = {nouveau}\n")
    conversions.append((i + 1, fn, nouveau, fin + 1 - i))
    i = fin + 1

print(f"fichier : {cible.name}  ({len(lignes)} lignes)")
print(f"fonctions converties : {len(conversions)}\n")
for lig, fn, nouveau, taille in conversions:
    print(f"  L{lig:<5} {nom_module}.{fn:<26} -> def {nouveau:<34} ({taille} lignes)")

if echecs:
    print("\nECHECS (non convertis, a traiter a la main) :")
    for lig, fn, raison in echecs:
        print(f"  L{lig} {fn} : {raison}")

# Controles
texte = "".join(sortie)
restants = len(re.findall(rf"^{re.escape(nom_module)}\.\w+\s*=\s*def\s*\(", texte, re.M))
print(f"\ndeclarations anonymes restantes : {restants}")
print(f"nouvelles fonctions nommees     : {len(re.findall(r'^def ' + nom_module + r'_', texte, re.M))}")
print(f"nouvelles affectations          : {len(re.findall(rf'^{re.escape(nom_module)}\.\w+ = {re.escape(nom_module)}_\w+$', texte, re.M))}")

if ecrire and not echecs:
    sauv = cible.with_suffix(".be.avant-conversion")
    sauv.write_text("".join(lignes), encoding="utf-8")
    cible.write_text(texte, encoding="utf-8")
    print(f"\nECRIT. Sauvegarde : {sauv.name}")
elif ecrire:
    print("\nRIEN ECRIT : des echecs subsistent.")
else:
    print("\n(simulation - relancer avec --ecrire pour appliquer)")
