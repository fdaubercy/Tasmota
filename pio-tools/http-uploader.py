# Idée originale de Pascal Gollor le 2022-12-13

Import("env")

import os
import tasmotapiolib

# Il faut spécifier 'upload_port' dans platform_override.ini à la section '[env]'

# clear upload flags
env.Replace(UPLOADERFLAGS="")

# Utilise espupload.py qui supporte les binaires compressés et non compressés
env.Replace(UPLOADER=os.path.join("pio-tools", "espupload.py"))

# emplacement du binaire non compressé : build_output\firmware\tasmota-theo.bin
bin_file = tasmotapiolib.get_final_bin_path(env)
# emplacement du binaire compressé : build_output\firmware\tasmota-theo.bin.gz
bin_gz_file = bin_file.with_suffix(".bin.gz")

if os.path.exists(bin_gz_file):
  # Fichier binaire compressé - build_output\firmware\tasmota-theo.bin.gz
  env.Replace(UPLOADCMD="$PYTHONEXE $UPLOADER -u $UPLOAD_PORT -f {}".format(bin_gz_file))
elif os.path.exists(bin_file):
  # Fichier binaire non compressé - build_output\firmware\tasmota-theo.bin
  env.Replace(UPLOADCMD="$PYTHONEXE $UPLOADER -u $UPLOAD_PORT -f {}".format(bin_file))
else:
  # Fichier binaire non compressé - C:\tmp\.pioenvs\tasmota-theo\firmware.bin
  env.Replace(UPLOADCMD="$PYTHONEXE $UPLOADER -u $UPLOAD_PORT -f $SOURCES")
