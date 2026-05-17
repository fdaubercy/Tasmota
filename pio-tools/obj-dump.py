# Produit un dump objet (.asm) après la compilation du fichier ELF

Import("env")

# Correspondance explicite pour les cibles Xtensa ; tout le reste utilise RISC-V par défaut
XTENSA_OBJDUMP = {
    "esp8266": "xtensa-lx106-elf-objdump",
    "esp32":   "xtensa-esp32-elf-objdump",
    "esp32s2": "xtensa-esp32s2-elf-objdump",
    "esp32s3": "xtensa-esp32s3-elf-objdump",
}

def resolve_objdump_tool(mcu: str) -> str:
    """
    Retourne l'outil objdump pour le MCU.
    Les MCU Xtensa connus utilisent des outils explicites ; tous les autres utilisent l'objdump RISC-V.
    """
    mcu = (mcu or "").lower().strip()
    return XTENSA_OBJDUMP.get(mcu, "riscv32-esp-elf-objdump")

def obj_dump_after_elf(source, target, env):
    """
    Action post-compilation : exécute objdump sur le fichier ELF et écrit ${PROGNAME}.asm.
    """
    board = env.BoardConfig()
    mcu = board.get("build.mcu", "esp32").lower()

    objdump_tool = resolve_objdump_tool(mcu)
    out_file = "$BUILD_DIR/${PROGNAME}.asm"
    print(f"Création de {out_file} avec {objdump_tool}")

    cmd = f"{objdump_tool} -D -C {target[0]} > {out_file}"
    env.Execute(cmd)

# Action post-compilation silencieuse
silent_action = env.Action([obj_dump_after_elf])
silent_action.strfunction = lambda target, source, env: ""
env.AddPostAction("$BUILD_DIR/${PROGNAME}.elf", silent_action)
