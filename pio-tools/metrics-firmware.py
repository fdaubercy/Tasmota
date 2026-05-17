Import("env")

import os
from os.path import join

def firm_metrics(source, target, env):
    print()
    if env["PIOPLATFORM"] == "espressif8266":
        map_file = join(env.subst("$BUILD_DIR")) + os.sep + "firmware.map"
        with open(map_file,'r', encoding='utf-8') as f:
            phrase = "_text_end = ABSOLUTE (.)"
            for line in f:
                if  phrase in line:
                    address = line.strip().split(" ")[0]
                    if int(address, 16) < 0x40108000:
                        used_bytes = int(address, 16) - 0x40100000
                        remaining_bytes = 0x8000 - used_bytes
                        percentage = round(used_bytes / 0x8000 * 100,1)
                        print("IRAM statique utilisée :",used_bytes,"octets (",remaining_bytes,"restants,",percentage,"% utilisé)")

silent_action = env.Action(firm_metrics)
silent_action.strfunction = lambda target, source, env: '' # astuce pour taire la sortie de commande scons
env.AddPostAction("$BUILD_DIR/${PROGNAME}.bin", silent_action)
