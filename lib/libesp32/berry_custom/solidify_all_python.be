#!/usr/bin/env -S PYTHONPATH=../berry python3 -m berry_port -s -g
#
# Berry solidify files

import os
import global
import solidify
import string as string2
import re

import sys
sys.path().push('src/embedded')   # allow to import from src/embedded

import "../../../tasmota/tasmota_defines_for_berry.be" as tasmota_defines

# globals that need to exist to make compilation succeed
# NOTE (fork) : `log` ajoute le 2026-07-15. Sans lui, tout fichier appelant log()
# meurt en `syntax_error: 'log' undeclared` AVANT meme le resolveur `#@ solidify:`.
# berry_tasmota, berry_matter, berry_animation et lv_haspmota le stubbent deja :
# son absence ici est une incoherence amont, et elle frappe justement le creneau
# prevu pour le code utilisateur — celui qui logue.
#
# NOTE (fork) : les trois dernieres lignes de la liste ci-dessous (serial / drivers...
# / LOG_LEVEL...) sont NOS globaux,
# ajoutes le 2026-07-15. Ils sont declares au niveau fichier par autoexec.be
# (l.9-21), alimentes par _persist.json, et references librement par nos modules.
# Le solidifieur tourne sur le PC : il ne les connait pas, et refuse a la
# COMPILATION tout fichier qui les mentionne (`syntax_error: 'drivers' undeclared`).
#
# Les stubber a nil ne fausse rien : le bytecode solidifie resout les globaux PAR NOM
# a l'execution (ils apparaissent en be_kv_str dans le .h). Sur l'ESP32, autoexec.be
# les a deja affectes pour de vrai. Le stub ne sert qu'a satisfaire le compilateur PC.
#
# `serial` est un global Tasmota, pas un des notres : son absence est une lacune amont
# de plus, comme celles de `log` et de `Driver`.
#
# Cette divergence-ci, contrairement a celles de log/Driver, n'a PAS vocation a
# remonter en PR : ces noms n'appartiennent qu'a notre framework.
var globs = "path,ctypes_bytes_dyn,tasmota,ccronexpr,gpio,light,webclient,load,MD5,lv,light_state,udp,tcpclientasync,log,"
            "lv_clock,lv_clock_icon,lv_signal_arcs,lv_signal_bars,lv_wifi_arcs_icon,lv_wifi_arcs,"
            "lv_wifi_bars_icon,lv_wifi_bars,"
            "_lvgl,"
            "int64,"
            "serial,"
            "drivers,serveur,diverses,modules,boolMute,"
            "LOG_LEVEL_ERREUR,LOG_LEVEL_INFO,LOG_LEVEL_DEBUG,LOG_LEVEL_DEBUG_PLUS,logSerial,logWeb"

for g:string2.split(globs, ",")
  global.(g) = nil
end

# NOTE (fork) : ajoute le 2026-07-15, calque sur berry_tasmota.
# Les classes ne peuvent PAS etre stubbees a nil comme les globals ci-dessus :
# `class X : Driver` exige que Driver soit une vraie classe, sinon le compilateur
# refuse avec `syntax_error: 'Driver' undeclared`. On en fabrique donc une vide.
# Sans ca, AUCUN controleXxx.be (tous des `class ... : Driver`) n'est solidifiable.
# berry_tasmota fait exactement pareil pour I2C_Driver ; berry_custom, le creneau
# utilisateur, n'avait aucun glob_classes du tout.
var glob_classes = "Driver"

for g:string2.split(glob_classes, ",")
  compile(f"class {g} end")()
end

var prefix_dir = "src/embedded/"
var prefix_out = "src/solidify/"

def sort(l)
  # insertion sort
  for i:1..size(l)-1
    var k = l[i]
    var j = i
    while (j > 0) && (l[j-1] > k)
      l[j] = l[j-1]
      j -= 1
    end
    l[j] = k
  end
  return l
end

def clean_directory(dir)
  var file_list = os.listdir(dir)
  for f : file_list
    if f[0] == '.'  continue end    # ignore files starting with `.`
    os.remove(dir + f)
  end
end

var pattern = "#@\\s*solidify:([A-Za-z0-9_.,]+)"

def parse_file(fname, prefix_out)
  print("Parsing: ", fname)
  var f = open(prefix_dir + fname)
  var src = f.read()
  f.close()
  # try to compile
  var compiled = compile(src)
  compiled()      # run the compile code to instanciate the classes and modules
  # output solidified
  var fname_h = string2.split(fname, '.be')[0] + '.h'  # take whatever is before the first '.be'
  var fout = open(prefix_out + "solidified_" + fname_h, "w")
  fout.write(f"/* Solidification of {fname_h} */\n")
  fout.write("/********************************************************************\\\n")
  fout.write("* Generated code, don't edit                                         *\n")
  fout.write("\\********************************************************************/\n")
  fout.write('#include "be_constobj.h"\n')

  var directives = re.searchall(pattern, src)
  # print(directives)

  for directive : directives
    var object_list = string2.split(directive[1], ',')
    var object_name = object_list[0]
    var weak = (object_list.find('weak') != nil)          # do we solidify with weak strings?
    var o = global
    var cl_name = nil
    var obj_name = nil
    for subname : string2.split(object_name, '.')
      o = o.(subname)
      cl_name = obj_name
      obj_name = subname
      if   (type(o) == 'class')
        obj_name = 'class_' + obj_name
      elif (type(o) == 'module')
        obj_name = 'module_' + obj_name
      end
    end
    solidify.dump(o, weak, fout, cl_name)
  end

  fout.write("/********************************************************************/\n")
  fout.write("/* End of solidification */\n")
  fout.close()
end

clean_directory(prefix_out)

var src_file_list = os.listdir(prefix_dir)
src_file_list = sort(src_file_list)
for src_file : src_file_list
  if src_file[0] == '.'  continue end
  parse_file(src_file, prefix_out)
end
