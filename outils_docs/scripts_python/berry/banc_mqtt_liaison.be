# Banc Berry de data/fs/mqttLiaisonFonctions.be : garde-fous de la voie MQTT (plan tasks/plans/voie-mqtt.md, A3).
# Charge le VRAI module sous des bouchons (bouchons_berry/liaison_mqtt/ : logFonctions, persist). Le temps est
# simule (millisecondes passees au module) : aucun reseau, aucune carte. Rejoue les cas de boucle : ordre puis accuse,
# ordre inutile, evenement de bouton, rafale d'un element, rafale sur tous, ordres sans accuse, et un MAITRE FAUTIF
# qui recommande l'inverse a chaque retour (la preuve que la boucle est bornee).
#
# Lancer via son enveloppe Python (racine, berry.exe, code de sortie, mutants) :
#     python outils_docs/scripts_python/berry/banc_mqtt_liaison.py
# Ou DEPUIS LA RACINE : lib/libesp32/berry/berry.exe outils_docs/scripts_python/berry/banc_mqtt_liaison.be [dossier_sources]
# Derniere ligne : BANC_MQTT_LIAISON: OK|ECHEC. Ne teste pas le vrai MQTT (module pur, A4 branche mqtt).
import global
import sys
import string
var SOURCES = size(global._argv) > 1 ? global._argv[1] : "data/fs"
sys.path().push(SOURCES)
sys.path().push("outils_docs/scripts_python/berry/bouchons_berry/liaison_mqtt")   # le dernier pousse l'emporte

var LOG_LEVEL_ERREUR = 1
var LOG_LEVEL_INFO = 2
var LOG_LEVEL_DEBUG = 3
var LOG_LEVEL_DEBUG_PLUS = 4
var JOURNAL = []

var echecs = 0
def verifie(ok, libelle)
    print((ok ? "OK   " : "KO   ") + libelle)
    if !ok    echecs += 1    end
end

import mqttLiaisonFonctions
var G = mqttLiaisonFonctions.GardeMqtt          # classe : valeurs par defaut (sans persist)

# --- 0. lecture du persist (drivers.liaisonMqtt.garde) : cles valides reprises, invalides ignorees
var gp = global.mqttLiaisonGarde
verifie(gp != nil && gp.max_element == 4 && gp.delai_accuse == 1500, "persist : maxParElement et delaiAccuseMs repris")
verifie(gp.essais_max == G.ESSAIS_MAX && gp.max_total == G.MAX_TOTAL, "persist : valeur invalide ou absente = defaut")

# --- 1. ordre, accuse, ecart : un ordre produit UN envoi, son retour n'est pas un evenement
var g = G()
verifie(g.demande("p/r1", "ON", 1000) == "envoyer", "ordre : envoye")
verifie(g.demande("p/r1", "ON", 1100) == "attente", "meme ordre pendant l'attente : pas de doublon")
verifie(g.recoit("p/r1", "ON", 1200) == "accuse", "retour attendu : accuse (pas un evenement)")
verifie(g.recoit("p/r1", "ON", 1300) == "inchange", "meme retour une seconde fois (tele periodique) : inchange")
verifie(g.demande("p/r1", "ON", 1400) == "identique", "ordre deja applique : rien n'est envoye (G3)")
verifie(size(g.attente) == 0, "plus d'ordre en attente apres accuse")

# --- 2. evenements venant de l'esclave
var h = G()
verifie(h.recoit("p/b1", "OFF", 1000) == "initial", "premier etat connu : initial (pas d'action au demarrage)")
verifie(h.recoit("p/b1", "ON", 2000) == "evenement", "bouton appuye sans ordre : evenement")
verifie(h.recoit("p/b1", "ON", 3000) == "inchange", "meme etat repete : inchange")
# ordre en cours, puis l'ancien etat repete par une tele : l'ordre reste en attente
var c = G()
c.recoit("p/r2", "OFF", 1000)
c.demande("p/r2", "ON", 2000)
verifie(c.recoit("p/r2", "OFF", 2500) == "inchange" && c.attente.contains("p/r2"), "ancien etat repete pendant un ordre : l'ordre reste attendu")
verifie(c.recoit("p/r2", "AUTRE", 2600) == "evenement" && !c.attente.contains("p/r2"), "etat inattendu pendant un ordre : evenement, ordre abandonne")

# --- 3. rafale sur UN element : quarantaine, les autres continuent
var q = G()
var n_envoyes = 0
var bloque_a = nil
for i: 0 .. 14
    var r = q.demande("p/r1", i % 2 == 0 ? "ON" : "OFF", 1000 + i * 100)
    if r == "envoyer"    n_envoyes += 1    q.recoit("p/r1", i % 2 == 0 ? "ON" : "OFF", 1000 + i * 100 + 50)
    elif bloque_a == nil    bloque_a = r    end
end
verifie(n_envoyes == G.MAX_ELEMENT && bloque_a == "quarantaine", "rafale d'un element : " + str(n_envoyes) + " ordres puis quarantaine")
verifie(q.demande("p/r2", "ON", 3000) == "envoyer", "un AUTRE element reste libre pendant la quarantaine")
verifie(q.demande("p/r1", "ON", 20000) == "quarantaine", "element en quarantaine : refuse")
verifie(q.etats["p/r1"] == "OFF" && q.demande("p/r1", "ON", 1000 + 1400 + G.QUARANTAINE_MS + 10) == "envoyer", "apres la quarantaine : l'element repart")
q.recoit("p/r1", "ON", 1000 + 1400 + G.QUARANTAINE_MS + 60)
verifie(q.demande("p/r1", "OFF", 1000 + 1400 + G.QUARANTAINE_MS + 200) == "envoyer", "apres la quarantaine : l'ordre SUIVANT passe aussi")

# --- 4. ordres espaces : jamais de quarantaine
var e = G()
var tous = true
for i: 0 .. 29
    var t = 1000 + i * 2000                       # 5 ordres par fenetre de 10 s au plus
    var v = i % 2 == 0 ? "ON" : "OFF"
    if e.demande("p/r1", v, t) != "envoyer"    tous = false    end
    e.recoit("p/r1", v, t + 100)
end
verifie(tous, "30 ordres espaces de 2 s : tous envoyes (la fenetre glisse)")

# --- 5. coupe-circuit global : beaucoup d'elements en peu de temps
var k = G()
var envoyes = 0
var coupe = false
for i: 0 .. 99
    var r = k.demande("p/e" + str(i), "ON", 1000 + i * 10)
    if r == "envoyer"    envoyes += 1    elif r == "coupe"    coupe = true    end
end
verifie(coupe && envoyes == G.MAX_TOTAL, "100 elements en 1 s : " + str(envoyes) + " ordres puis coupe-circuit")
verifie(k.demande("p/neuf", "ON", 5000) == "coupe", "coupe-circuit : tout est refuse")
verifie(k.demande("p/neuf", "ON", 1000 + 100 * 10 + G.COUPURE_MS) == "envoyer", "apres la coupure : la voie repart seule")
k.demande("p/z", "ON", 1)
k.rearme()
verifie(!k.coupe_actif && size(k.quarantaine) == 0, "rearme : quarantaines et coupe-circuit leves")

# --- 5 bis. ordre refuse pendant la coupure : aucune attente creee, rien a renvoyer
var kk = G()
for i: 0 .. 69    kk.demande("p/e" + str(i), "ON", 1000 + i)    end
verifie(kk.coupe_actif && kk.demande("p/nouveau", "ON", 2000) == "coupe" && !kk.attente.contains("p/nouveau"), "ordre refuse (coupe-circuit) : aucune attente creee")
# t = 0 est un instant valable (plus de sentinelle)
var z = G()
verifie(z.demande("p/r1", "ON", 0) == "envoyer" && z.recoit("p/r1", "ON", 10) == "accuse", "t = 0 : ordre envoye puis accuse")

# --- 6. ordre sans accuse : renvois bornes, puis echec
var r2 = G()
r2.demande("p/r1", "ON", 1000)
var s = r2.a_renvoyer(1000 + G.DELAI_ACCUSE_MS - 1)
verifie(size(s["renvoyer"]) == 0 && size(s["echec"]) == 0, "avant le delai d'accuse : rien")
s = r2.a_renvoyer(1000 + G.DELAI_ACCUSE_MS)
verifie(size(s["renvoyer"]) == 1 && s["renvoyer"][0][0] == "p/r1" && s["renvoyer"][0][1] == "ON", "apres le delai : renvoi du meme ordre")
s = r2.a_renvoyer(1000 + 2 * G.DELAI_ACCUSE_MS)
verifie(size(s["renvoyer"]) == 1, "deuxieme renvoi (3e emission)")
s = r2.a_renvoyer(1000 + 3 * G.DELAI_ACCUSE_MS)
verifie(size(s["renvoyer"]) == 0 && size(s["echec"]) == 1 && s["echec"][0] == "p/r1" && size(r2.attente) == 0, "ESSAIS_MAX atteint : echec, plus de renvoi")
r2.demande("p/r2", "ON", 90000)
r2.recoit("p/r2", "ON", 90500)
verifie(size(r2.a_renvoyer(99999)["renvoyer"]) == 0, "ordre accuse : jamais renvoye")

# --- 6 bis. renvoi refuse par la quarantaine : ordre abandonne ET loggue
var rq = mqttLiaisonFonctions.GardeMqtt({"maxParElement": 2})
rq.demande("p/r1", "ON", 1000)
rq.demande("p/r1", "OFF", 1100)                    # remplace l'ordre en attente : essais repart a 1
verifie(rq.attente["p/r1"]["valeur"] == "OFF" && rq.attente["p/r1"]["essais"] == 1, "nouvel ordre de valeur differente : remplace l'ancien, essais a 1")
var nj = size(JOURNAL)
s = rq.a_renvoyer(1100 + G.DELAI_ACCUSE_MS)
verifie(size(s["renvoyer"]) == 0 && size(s["echec"]) == 1 && size(rq.attente) == 0, "renvoi bloque par la quarantaine : echec, plus d'attente")
verifie(size(JOURNAL) > nj + 1 && string.find(JOURNAL[-1][0], "voie bloquée") >= 0 && JOURNAL[-1][1] == LOG_LEVEL_ERREUR, "renvoi bloque : echec loggue en erreur")

# --- 6 ter. arguments invalides et valeurs de types differents
var v = G()
verifie(v.demande(nil, "ON", 1000) == "invalide" && v.demande("", "ON", 1000) == "invalide" && v.demande(5, "ON", 1000) == "invalide", "cle nil, vide ou non texte : invalide, sans exception")
verifie(v.demande("p/r1", nil, 1000) == "invalide" && v.recoit(nil, "ON", 1000) == "invalide" && v.recoit("p/r1", nil, 1000) == "invalide", "valeur nil : invalide")
verifie(size(v.attente) == 0 && size(v.etats) == 0 && size(v.totaux) == 0, "appels invalides : aucun effet sur l'etat")
v.demande("p/r1", 1, 1000)
verifie(v.recoit("p/r1", "1", 1100) == "accuse", "ordre 1 (entier), retour \"1\" (texte) : accuse")
# premier retour, sans etat connu, different de l'ordre : probablement l'ancien etat, l'ordre reste attendu
var w = G()
w.demande("p/r2", "OFF", 1000)
verifie(w.recoit("p/r2", "ON", 1100) == "initial" && w.attente.contains("p/r2"), "1er retour different de l'ordre, etat inconnu : initial, ordre toujours attendu")
verifie(w.recoit("p/r2", "OFF", 1200) == "accuse", "puis le vrai retour : accuse")

# --- 7. LA PREUVE ANTI-BOUCLE : un maitre fautif recommande l'inverse a chaque retour de l'esclave
var f = G()
var ordres = 0
var refus = 0
var valeur = "ON"
for i: 0 .. 199                                    # 200 retours en 20 s
    var t = 1000 + i * 100
    var r = f.demande("p/r1", valeur, t)
    if r == "envoyer"
        ordres += 1
        f.recoit("p/r1", valeur, t + 50)           # l'esclave obeit et publie son etat
        valeur = valeur == "ON" ? "OFF" : "ON"     # le maitre fautif reagit a ce retour par l'ordre inverse
    else
        refus += 1
        valeur = valeur == "ON" ? "OFF" : "ON"
    end
end
verifie(ordres == G.MAX_ELEMENT, "maitre fautif : " + str(ordres) + " ordres sur 200 tentatives (borne : " + str(G.MAX_ELEMENT) + ")")

# --- 8. journal : erreurs aux seuils franchis
var erreurs = 0
for j: JOURNAL    if j[1] == LOG_LEVEL_ERREUR && j[2] == "liaisonMqtt" && string.find(j[0], "LIAISON_MQTT_ERREUR: ") == 0    erreurs += 1    end    end
verifie(erreurs >= 3, "journal : quarantaine, coupe-circuit et echec loggues en erreur, cible liaisonMqtt (" + str(erreurs) + ")")

print(echecs == 0 ? "BANC_MQTT_LIAISON: OK" : "BANC_MQTT_LIAISON: ECHEC (" + str(echecs) + ")")
