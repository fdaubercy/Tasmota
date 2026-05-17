Import('env')

link_flags = env['LINKFLAGS']
build_flags = " ".join(env['BUILD_FLAGS'])

if "FIRMWARE_SAFEBOOT" in build_flags:
  # Le Crash Recorder n'est pas inclus dans le firmware safeboot -> supprimer le wrap de l'éditeur de liens
  try:
    link_flags.pop(link_flags.index("-Wl,--wrap=panicHandler"))
  except:
    pass
  try:
    link_flags.pop(link_flags.index("-Wl,--wrap=xt_unhandled_exception"))
  except:
    pass
