# Preparation de la carte simulee pour banc_boot.be (2026-10-23). Ce fichier N'EST PAS un module :
# banc_boot.be le compile et l'execute au niveau global, apres faux_firmware.be. Il pose la globale
# PREPARATION_BOOT, dont prepare() remplit le LittleFS en memoire comme le ferait un televersement :
#
#   - la liste des modules SOLIDIFIES et la liste noire de l'environnement de la carte sont LUES dans
#     platformio_tasmota_cenv.ini (custom_berry_solidify, ${berry_commun.xxx} resolus, et
#     custom_files_exclude), comme le fait copy_fs_image (pre_utilitaires_platformio.py) : le banc suit
#     donc tout changement de ces listes sans etre modifie ;
#   - LittleFS = data/fs SAUF solidifies et liste noire (poses a la racine), data/json -> /json,
#     data/sd -> /sd (noms seuls, contenu vide : non lus au demarrage), puis le dossier de la carte
#     (autoexec.be, controleGarage.be, ...). Le _persist.json est celui du cas teste ;
#   - pour chaque module solidifie, une ENVELOPPE de deux lignes est ecrite dans le dossier de travail
#     (.pio/banc_boot/solidifies, ignore par git) : 'import nom' la trouve avant le vrai fichier et
#     recoit le module construit comme par la solidification (BANC_BOOT.solidifie). Rien d'autre n'est
#     ecrit sur le disque du PC.
import global
import string
import os

class PREPARATION_BOOT_CLASSE
    var ini                     # texte de platformio_tasmota_cenv.ini

    def sansBlancs(t) return string.replace(string.replace(t, " ", ""), "\t", "") end

    # Valeur d'une cle d'une section, lignes de continuation (indentees) comprises, commentaires retires
    def valeur(section, cle)
        var dedans = false
        var lignes = string.split(self.ini, "\n")
        var valeurs = []
        var i = 0
        while i < size(lignes)
            var l = string.replace(lignes[i], "\r", "")
            var egal = string.find(l, "=")
            if string.startswith(l, "[")    dedans = (string.find(l, "[" + section + "]") == 0)
            elif dedans && egal > 0 && self.sansBlancs(l[0 .. egal - 1]) == cle
                valeurs.push(l[egal + 1 ..])
                i += 1
                while i < size(lignes) && size(lignes[i]) > 0 && (lignes[i][0] == " " || lignes[i][0] == "\t")
                    valeurs.push(lignes[i])
                    i += 1
                end
                break
            end
            i += 1
        end
        var mots = []
        for v: valeurs
            var sansCommentaire = string.split(string.replace(v, "\r", ""), ";")[0]
            for m: string.split(string.replace(sansCommentaire, "\t", " "), " ")
                if size(m) > 0    mots.push(m)    end
            end
        end
        return mots
    end

    # Noms de fichier (sans dossier) d'une liste, ${berry_commun.xxx} resolus
    def fichiers(section, cle)
        var r = []
        for m: self.valeur(section, cle)
            if string.startswith(m, "${berry_commun.")
                var sous = string.split(string.split(m, ".")[1], "}")[0]
                for f: self.fichiers("berry_commun", sous)    r.push(f)    end
            else
                var morceaux = string.split(m, "/")
                r.push(morceaux[size(morceaux) - 1])
            end
        end
        return r
    end

    def prepare(env, sources, carte, persistTexte, travail)
        var lit = global.BANC_BOOT.litDisque
        self.ini = lit("platformio_tasmota_cenv.ini")
        var solidifies = self.fichiers("env:" + env, "custom_berry_solidify")
        var exclus = self.fichiers("env:" + env, "custom_files_exclude")
        if size(solidifies) == 0    raise "banc_error", "aucun module solidifie lu pour env:" + env    end

        var fs = global.LITTLEFS
        for nom: os.listdir(sources)
            if !string.endswith(nom, ".be") || solidifies.find(nom) != nil || exclus.find(nom) != nil    continue    end
            fs.pose("/" + nom, lit(sources + "/" + nom))
        end
        for nom: os.listdir("data/json")    fs.pose("/json/" + nom, lit("data/json/" + nom))    end
        for sous: os.listdir("data/sd")
            for nom: os.listdir("data/sd/" + sous)    fs.pose("/sd/" + sous + "/" + nom, "")    end
        end
        for nom: os.listdir(carte)
            if !os.path.isdir(carte + "/" + nom)    fs.pose("/" + nom, lit(carte + "/" + nom))    end
        end
        fs.pose("/_persist.json", persistTexte)

        # Enveloppes des modules solidifies
        var dossier = travail + "/solidifies"
        for d: [".pio", travail, dossier]    if !os.path.exists(d)    os.mkdir(d)    end    end
        global.BANC_BOOT.solidifies = []
        for f: solidifies
            var nom = string.split(f, ".be")[0]
            global.BANC_BOOT.solidifies.push(nom)
            global.BANC_BOOT.ecrisDisque(dossier + "/" + nom + ".be",
                "# Enveloppe generee par banc_boot.be : module solidifie (voir preparation_boot.be)\n" +
                "import global\nreturn global.BANC_BOOT.solidifie(\"" + nom + "\")\n")
        end
        return dossier
    end
end
PREPARATION_BOOT = PREPARATION_BOOT_CLASSE()
