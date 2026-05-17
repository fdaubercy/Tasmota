#!/usr/bin/python
#
# espupload par Theo Arends - 20170103
#
# Téléverse un fichier binaire vers le serveur OTA
#
# Exécution : espupload -i <Adresse_IP_hôte> -p <Port_hôte> -f <sketch.bin>
# Exemple : pio-tools\espupload_legacy -i 192.168.4.1:80 -p 80 -u /u2?fsz -f build_output\firmware\tasmota32p4-wifi6.bin
#
# Nécessite pycurl
#   - pip install pycurl

import sys
import os
import optparse
import logging
import pycurl

HOST_ADDR = "192.168.0.43"
HOST_PORT = 80
# HOST_URL = "/api/upload-arduino.php"
HOST_URL = "/u2?fsz"

def upload(hostAddr, hostPort, hostUrl, filename):
  print("-------------------> Utilise espupload_legacy.py pour upload OTA")
  url = 'http://%s:%d%s' % (hostAddr, hostPort, hostUrl)
  c = pycurl.Curl()
  c.setopt(c.URL, url)
  # L'"Expect:" est là pour supprimer le comportement "Expect: 100-continue" qui est
  # le comportement par défaut de libcurl lors de l'envoi de corps volumineux (et qui échoue sur lighttpd).
  c.setopt(c.HTTPHEADER, ["Expect:"])
  c.setopt(c.HTTPPOST, [('file', (c.FORM_FILE, filename, )), ])
  c.perform()
  c.close()

def parser():
  parser = optparse.OptionParser(
    usage = "%prog [options]",
    description = "Téléverse une image vers le serveur hôte Over The Air pour le module esp8266 avec support OTA."
  )

  # ip, port et url de destination
  group = optparse.OptionGroup(parser, "Destination")
  group.add_option("-i", "--host_ip",
    dest = "host_ip",
    action = "store",
    help = "Adresse IP de l'hôte. Défaut : " + HOST_ADDR,
    default = HOST_ADDR
  )
  group.add_option("-p", "--host_port",
    dest = "host_port",
    type = "int",
    help = "Port OTA du serveur hôte. Défaut : " + str(HOST_PORT),
    default = HOST_PORT
  )
  group.add_option("-u", "--host_url",
    dest = "host_url",
    action = "store",
    help = "URL de l'hôte commençant par /. Défaut : '" + HOST_URL + "'",
    default = HOST_URL
  )
  parser.add_option_group(group)

  # image
  group = optparse.OptionGroup(parser, "Image")
  group.add_option("-f", "--file",
    dest = "image",
    help = "Fichier image.",
    metavar="FILE",
    default = None
  )
  parser.add_option_group(group)

  # groupe de sortie
  group = optparse.OptionGroup(parser, "Output")
  group.add_option("-d", "--debug",
    dest = "debug",
    help = "Afficher la sortie de débogage. Et remplacer le niveau de log par debug.",
    action = "store_true",
    default = False
  )
  parser.add_option_group(group)

  (options, args) = parser.parse_args()

  return options
# end parser

def main(args):
  # récupération des options
  options = parser()

  # adaptation du niveau de log
  loglevel = logging.WARNING
  if (options.debug):
    loglevel = logging.DEBUG
  # end if

  # journalisation
  logging.basicConfig(level = loglevel, format = '%(asctime)-8s [%(levelname)s]: %(message)s', datefmt = '%H:%M:%S')

  logging.debug("Options: %s", str(options))

  if (not options.host_ip or not options.image):
    logging.critical("Arguments insuffisants.")

    return 1
  # end if

  if not os.path.exists(options.image):
    logging.critical("Désolé : le fichier %s n'existe pas", options.image)

    return 1
  # end if

  upload(options.host_ip, options.host_port, options.host_url, options.image)
# end main

if __name__ == '__main__':
  sys.exit(main(sys.argv))
# end if
