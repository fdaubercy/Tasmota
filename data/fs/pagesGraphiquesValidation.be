#- *********************************************************************************************
 * pagesGraphiquesValidation.be - Validation de la description des pages de graphiques (atelier des graphiques, 2026-11-03)
 *
 * Module de fonctions SANS driver, importe par pagesGraphiques.be (lisDescription, valeurs) : separe du moteur pour
 * que chaque fichier reste sous 500 lignes. Embarque et solidifie (ou non) TOUJOURS avec pagesGraphiques.
 *
 * valide(d) rend la liste des motifs de refus (vide = valide), avec le MEME verdict que
 * outils_docs/scripts_python/outils_pc/atelier_graphiques_description.py::valide, dont le docstring est la reference
 * du schema, des bornes (textes en OCTETS UTF-8) et de la grammaire des formules. Rejoue par
 * outils_docs/scripts_python/berry/banc_pages_graphiques.py sur bouchons_berry/pages_graphiques/cas_description.json.
 * Les motifs ne reprennent pas mot pour mot ceux de l'atelier ; le verdict, si.
 * Formules : liste blanche verifiee par un automate a pile, jamais compile ni execute.
 *
 * Solidifiable : aucun etat dans la table du module (rien n'y est ecrit apres le chargement), 'import
 * pagesGraphiquesValidation' dans toute fonction qui le cite, appels par pagesGraphiquesValidation.nom.
********************************************************************************************* -#

#@ solidify:pagesGraphiquesValidation
var pagesGraphiquesValidation = module("pagesGraphiquesValidation")

# Schema (atelier_graphiques_description.py : STYLES, BORNES, ROUTES_RESERVEES, CLES)
pagesGraphiquesValidation.STYLES = ["courbe", "aire", "escalier", "barres", "barres-empilees", "barres-periode", "deux-axes", "lies",
                                    "cadran", "anneau", "chaleur", "nuage", "radar", "liquide", "demi-cercle"]
pagesGraphiquesValidation.BORNES = {"pages": 8, "graphiques": 8, "series": 12, "octets": 8192, "encadres": 8, "calculees": 16}
pagesGraphiquesValidation.ROUTES_RESERVEES = ["cs", "cm", "cn", "in", "up", "u1", "u2", "u3", "rs", "rt", "md", "mn", "sv", "cf", "dl",
                                              "upl", "ufsd", "ufsu", "graphiques", "histo", "cuve", "energie", "pages", "coprocesseur",
                                              "discovery", "json", "sd"]
pagesGraphiquesValidation.FONCTIONS = ["min", "max", "abs", "round"]
pagesGraphiquesValidation.CLES = {
    "racine": ["version", "pages", "encadres", "calculees"],
    "page": ["id", "titre", "acces", "graphiques"],
    "graphique": ["type", "titre", "series", "min", "max", "zones", "periode", "cadence", "largeur", "hauteur", "cumul"],
    "encadre": ["id", "type", "serie", "lien"],
    "calculee": ["formule", "nature"]
}

# ---- Validation (meme verdict que atelier_graphiques_description::valide) -------------------------

# Vrai si x est une chaine de la liste (une valeur d'un autre type n'est jamais comparee : liste == chaine leverait)
def pagesGraphiquesValidation_dans(x, liste)
    return type(x) == "string" && liste.find(x) != nil
end
pagesGraphiquesValidation.dans = pagesGraphiquesValidation_dans

def pagesGraphiquesValidation_nombre(x)
    return type(x) == "int" || type(x) == "real"
end
pagesGraphiquesValidation.nombre = pagesGraphiquesValidation_nombre

# Texte de 1 a 60 octets UTF-8 (titres)
def pagesGraphiquesValidation_titreOk(t)
    return type(t) == "string" && size(t) >= 1 && size(t) <= 60
end
pagesGraphiquesValidation.titreOk = pagesGraphiquesValidation_titreOk

# Classe d'un caractere par son octet : 1 chiffre ASCII, 2 lettre ASCII ou '_', 0 autre (octet nul ou non ASCII compris)
def pagesGraphiquesValidation_classe(c)
    import string
    var b = string.byte(c)
    if (b >= 48 && b <= 57)    return 1    end
    if ((b >= 65 && b <= 90) || (b >= 97 && b <= 122) || b == 95)    return 2    end
    return 0
end
pagesGraphiquesValidation.classe = pagesGraphiquesValidation_classe

# Chemin de serie : [A-Za-z_][A-Za-z0-9_]* ('.' [A-Za-z0-9_]+)*, 96 octets au plus, sans "__" ni segment constructor/prototype
def pagesGraphiquesValidation_cheminOk(s)
    import pagesGraphiquesValidation
    import string
    if (type(s) != "string" || size(s) == 0 || size(s) > 96 || string.find(s, "__") >= 0)    return false    end
    var premier = true
    for seg: string.split(s, ".")
        if (size(seg) == 0 || seg == "constructor" || seg == "prototype")    return false    end
        for j: 0 .. size(seg) - 1
            var k = pagesGraphiquesValidation.classe(seg[j])
            if (k == 0 || (premier && j == 0 && k != 2))    return false    end
        end
        premier = false
    end
    return true
end
pagesGraphiquesValidation.cheminOk = pagesGraphiquesValidation_cheminOk

# Identifiant de page ou d'encadre : [a-z0-9-]{1,24}
def pagesGraphiquesValidation_idOk(v)
    import string
    if (type(v) != "string" || size(v) < 1 || size(v) > 24)    return false    end
    for i: 0 .. size(v) - 1
        var b = string.byte(v[i])
        if (!((b >= 97 && b <= 122) || (b >= 48 && b <= 57) || b == 45))    return false    end
    end
    return true
end
pagesGraphiquesValidation.idOk = pagesGraphiquesValidation_idOk

# Couleur #rrggbb
def pagesGraphiquesValidation_couleurOk(v)
    import string
    if (type(v) != "string" || size(v) != 7 || v[0] != "#")    return false    end
    for i: 1 .. 6
        var b = string.byte(v[i])
        if (!((b >= 48 && b <= 57) || (b >= 65 && b <= 70) || (b >= 97 && b <= 102)))    return false    end
    end
    return true
end
pagesGraphiquesValidation.couleurOk = pagesGraphiquesValidation_couleurOk

# Jetons d'une formule : liste de [genre, texte] (genre "n" nombre, "c" chemin, "s" symbole), nil si un caractere est
# hors liste blanche. Seuls separateurs : espace et tabulation. Nombre [0-9]+('.'[0-9]+)? ; chemin comme cheminOk.
def pagesGraphiquesValidation_jetons(f)
    import pagesGraphiquesValidation
    import string
    var V = pagesGraphiquesValidation
    var jetons = []
    var i = 0
    var n = size(f)
    while (true)
        while (i < n && (f[i] == " " || f[i] == "\t"))    i += 1    end
        if (i >= n)    break    end
        var d = i
        var k = V.classe(f[i])
        if (k == 1)
            while (i < n && V.classe(f[i]) == 1)    i += 1    end
            if (i + 1 < n && f[i] == "." && V.classe(f[i + 1]) == 1)
                i += 1
                while (i < n && V.classe(f[i]) == 1)    i += 1    end
            end
            jetons.push(["n", f[d .. i - 1]])
        elif (k == 2)
            while (i < n && V.classe(f[i]) != 0)    i += 1    end
            while (i + 1 < n && f[i] == "." && V.classe(f[i + 1]) != 0)
                i += 1
                while (i < n && V.classe(f[i]) != 0)    i += 1    end
            end
            jetons.push(["c", f[d .. i - 1]])
        elif ([45, 43, 42, 47, 40, 41, 44].find(string.byte(f[i])) != nil)     # - + * / ( ) ,
            i += 1
            jetons.push(["s", f[d]])
        else
            return nil
        end
    end
    return jetons
end
pagesGraphiquesValidation.jetons = pagesGraphiquesValidation_jetons

# Motif de refus d'une formule, nil si acceptee. Meme langage que la grammaire recursive de l'atelier, verifie par
# un automate a pile (pas de recursion : la pile Berry de la carte est bornee) : un operande est attendu au debut,
# apres un operateur, '(' ou ',' ; un seul '-' unaire par operande ; pile = parentheses (nil) et fonctions [nom, nb d'arguments].
def pagesGraphiquesValidation_valideFormule(f)
    import pagesGraphiquesValidation
    var V = pagesGraphiquesValidation
    if (type(f) != "string" || size(f) > 200)    return "formule vide, non textuelle ou trop longue"    end
    var t = V.jetons(f)
    if (t == nil)    return "formule interdite : caractere hors liste blanche"    end
    if (size(t) == 0)    return "formule vide, non textuelle ou trop longue"    end
    var pile = []
    var operande = true
    var moins = false
    var i = 0
    while (i < size(t))
        var g = t[i][0]
        var x = t[i][1]
        i += 1
        if (operande)
            if (g == "s" && x == "-" && !moins)
                moins = true
                continue
            end
            moins = false
            if (g == "n")
                operande = false
            elif (g == "c")
                if (!V.cheminOk(x))    return "formule interdite : chemin refuse " + x    end
                if (V.FONCTIONS.find(x) != nil)
                    if (i >= size(t) || t[i][0] != "s" || t[i][1] != "(")    return "formule interdite : fonction " + x + " sans parenthese"    end
                    i += 1
                    pile.push([x, 1])
                else
                    operande = false
                end
            elif (g == "s" && x == "(")
                pile.push(nil)
            else
                return "formule interdite : operande attendu avant " + x
            end
        elif (g == "s" && (x == "+" || x == "-" || x == "*" || x == "/"))
            operande = true
        elif (g == "s" && x == "," && size(pile) > 0 && pile[size(pile) - 1] != nil)
            pile[size(pile) - 1][1] += 1
            operande = true
        elif (g == "s" && x == ")" && size(pile) > 0)
            var haut = pile.pop()
            if (haut != nil && (((haut[0] == "abs" || haut[0] == "round") && haut[1] != 1) || ((haut[0] == "min" || haut[0] == "max") && haut[1] < 2)))
                return "formule interdite : arite de " + haut[0] + " : " + str(haut[1]) + " argument(s)"
            end
        else
            return "formule interdite : jeton inattendu " + x
        end
    end
    if (operande)    return "formule interdite : operande attendu en fin de formule"    end
    if (size(pile) > 0)    return "formule interdite : parenthese fermante attendue"    end
    return nil
end
pagesGraphiquesValidation.valideFormule = pagesGraphiquesValidation_valideFormule

# Cles hors schema de l'objet -> motifs
def pagesGraphiquesValidation_cles(obj, quoi, m)
    import pagesGraphiquesValidation
    var permises = pagesGraphiquesValidation.CLES[quoi]
    for k: obj.keys()
        if (permises.find(k) == nil)    m.push(quoi + " : cle inconnue " + str(k))    end
    end
end
pagesGraphiquesValidation.cles = pagesGraphiquesValidation_cles

# [motif, nature] d'une serie : nature de la calculee citee (calc:<nom>), nil pour un chemin brut
def pagesGraphiquesValidation_serie(s, calc)
    import pagesGraphiquesValidation
    import string
    var V = pagesGraphiquesValidation
    if (type(s) == "string" && string.find(s, "calc:") == 0)
        var c = calc.find(s[5 .. size(s) - 1])
        if (!isinstance(c, map) || !V.dans(c.find("nature"), ["direct", "historique"]))    return ["serie " + s + " : calculee inconnue", nil]    end
        return [nil, c["nature"]]
    end
    if (!V.cheminOk(s))    return ["serie " + str(s) + " : chemin invalide", nil]    end
    return [nil, nil]
end
pagesGraphiquesValidation.serie = pagesGraphiquesValidation_serie

def pagesGraphiquesValidation_graphique(g, ou, calc, m)
    import pagesGraphiquesValidation
    var V = pagesGraphiquesValidation
    if (!isinstance(g, map))
        m.push(ou + " : objet attendu")
        return
    end
    V.cles(g, "graphique", m)
    if (!V.dans(g.find("type"), V.STYLES))    m.push(ou + " : style inconnu")    end
    if (!V.titreOk(g.find("titre")))    m.push(ou + " : titre de 1 a 60 caracteres")    end
    var periode = g.find("periode", "direct")
    if (!V.dans(periode, ["direct", "jour", "mois"]))    m.push(ou + " : periode invalide")    end
    if (!V.dans(g.find("largeur", "demi"), ["demi", "pleine"]))    m.push(ou + " : largeur invalide")    end
    var entier = def (x, bas, haut) return type(x) == "int" && x >= bas && x <= haut end
    if (g.contains("cadence") && !entier(g["cadence"], 1, 3600))    m.push(ou + " : cadence hors 1..3600")    end
    if (g.contains("hauteur") && !entier(g["hauteur"], 80, 600))    m.push(ou + " : hauteur hors 80..600")    end
    var cumul = g.find("cumul")
    var cumule = V.dans(cumul, ["heure", "jour", "mois"])
    if (g.contains("cumul") && !cumule)    m.push(ou + " : cumul invalide")    end
    for k: ["min", "max"]
        if (g.contains(k) && !V.nombre(g[k]))    m.push(ou + " : " + k + " doit etre un nombre")    end
    end
    if (V.nombre(g.find("min")) && V.nombre(g.find("max")) && g["min"] >= g["max"])    m.push(ou + " : min >= max")    end
    var zones = g.find("zones", [])
    if (!isinstance(zones, list))
        m.push(ou + " : zones doit etre une liste")
    else
        for z: zones
            if (!(isinstance(z, list) && size(z) == 2 && V.nombre(z[0]) && V.couleurOk(z[1])))
                m.push(ou + " : zone mal formee")
            elif (z[0] < 0 || z[0] > 1)
                m.push(ou + " : zone hors [0, 1]")
            end
        end
    end
    var series = g.find("series")
    if (!isinstance(series, list) || size(series) == 0)
        m.push(ou + " : series doit etre une liste non vide")
        return
    end
    if (size(series) > V.BORNES["series"])    m.push(ou + " : series : " + str(size(series)) + " > " + str(V.BORNES["series"]))    end
    for s: series
        var r = V.serie(s, calc)
        if (r[0] != nil)
            m.push(ou + " : " + r[0])
        elif (r[1] == "direct" && V.dans(periode, ["jour", "mois"]))
            m.push(ou + " : nature de la formule incompatible, " + s + " (direct) sur periode " + periode)
        elif (r[1] == "historique" && V.dans(periode, ["direct"]))
            m.push(ou + " : nature de la formule incompatible, " + s + " (historique) sur periode direct")
        end
        if (r[1] == "direct" && cumule)    m.push(ou + " : cumul sur une serie instantanee, " + s)    end
    end
end
pagesGraphiquesValidation.graphique = pagesGraphiquesValidation_graphique

# Identifiant ; vus : ids deja rencontres (map id -> true), complete ici
def pagesGraphiquesValidation_id(v, vus, ou, m)
    import pagesGraphiquesValidation
    if (!pagesGraphiquesValidation.idOk(v))
        m.push(ou + " : id invalide (attendu [a-z0-9-]{1,24})")
        return
    end
    if (pagesGraphiquesValidation.ROUTES_RESERVEES.find(v) != nil)    m.push(ou + " : id reserve " + v + " (route existante)")
    elif (vus.contains(v))    m.push(ou + " : id en double " + v)
    end
    vus[v] = true
end
pagesGraphiquesValidation.id = pagesGraphiquesValidation_id

# Liste des motifs de refus de la description d (vide = valide)
def pagesGraphiquesValidation_valide(d)
    import pagesGraphiquesValidation
    import json
    var V = pagesGraphiquesValidation
    if (!isinstance(d, map))    return ["description : objet attendu"]    end
    var m = []
    V.cles(d, "racine", m)
    if (!V.nombre(d.find("version")) || d["version"] != 1)    m.push("version : doit valoir 1")    end
    var calc = d.find("calculees", {})
    if (!isinstance(calc, map) || size(calc) > V.BORNES["calculees"])
        m.push("calculees : objet de " + str(V.BORNES["calculees"]) + " entrees au plus")
        calc = {}
    end
    for nom: calc.keys()
        if (!V.cheminOk(nom) || size(nom) > 48)    m.push("calculee " + nom + " : nom invalide")    end
        var c = calc[nom]
        if (!isinstance(c, map))
            m.push("calculee " + nom + " : objet attendu")
            continue
        end
        V.cles(c, "calculee", m)
        if (!V.dans(c.find("nature"), ["direct", "historique"]))    m.push("calculee " + nom + " : nature direct ou historique attendue")    end
        var motif = V.valideFormule(c.find("formule"))
        if (motif != nil)    m.push("calculee " + nom + " : " + motif)    end
    end
    var pages = d.find("pages")
    var ids = {}
    if (!isinstance(pages, list) || size(pages) == 0)
        m.push("pages : liste non vide attendue")
        pages = []
    elif (size(pages) > V.BORNES["pages"])
        m.push("pages : " + str(size(pages)) + " > " + str(V.BORNES["pages"]))
    end
    var i = 0
    for p: pages
        i += 1
        var ou = "page " + str(i)
        if (!isinstance(p, map))
            m.push(ou + " : objet attendu")
            continue
        end
        V.cles(p, "page", m)
        V.id(p.find("id"), ids, ou, m)
        if (!V.titreOk(p.find("titre")))    m.push(ou + " : titre de 1 a 60 caracteres")    end
        if (!V.dans(p.find("acces", "bouton"), ["bouton", "lien"]))    m.push(ou + " : acces bouton ou lien attendu")    end
        var gs = p.find("graphiques")
        if (!isinstance(gs, list) || size(gs) == 0)
            m.push(ou + " : graphiques doit etre une liste non vide")
            continue
        end
        if (size(gs) > V.BORNES["graphiques"])    m.push(ou + " : graphiques : " + str(size(gs)) + " > " + str(V.BORNES["graphiques"]))    end
        var j = 0
        for g: gs
            j += 1
            V.graphique(g, ou + " graphique " + str(j), calc, m)
        end
    end
    var encs = d.find("encadres", [])
    if (!isinstance(encs, list) || size(encs) > V.BORNES["encadres"])
        m.push("encadres : liste de " + str(V.BORNES["encadres"]) + " au plus")
        encs = []
    end
    var vus = {}
    i = 0
    for e: encs
        i += 1
        var ou = "encadre " + str(i)
        if (!isinstance(e, map))
            m.push(ou + " : objet attendu")
            continue
        end
        V.cles(e, "encadre", m)
        V.id(e.find("id"), vus, ou, m)
        if (!V.dans(e.find("type"), V.STYLES))    m.push(ou + " : style inconnu")    end
        var r = V.serie(e.find("serie"), calc)
        if (r[0] != nil)    m.push(ou + " : " + r[0])    end
        if (e.contains("lien") && (type(e["lien"]) != "string" || !ids.contains(e["lien"])))    m.push(ou + " : lien vers une page inconnue")    end
    end
    # shortcut: json.dump ecrit 1.0 en "1" (Python : "1.0") : quelques octets d'ecart, seulement tout pres de la borne
    var taille = size(json.dump(d))
    if (taille > V.BORNES["octets"])    m.push("taille : " + str(taille) + " octets > " + str(V.BORNES["octets"]))    end
    return m
end
pagesGraphiquesValidation.valide = pagesGraphiquesValidation_valide

# Retourne le module lors de l'importation
return pagesGraphiquesValidation
