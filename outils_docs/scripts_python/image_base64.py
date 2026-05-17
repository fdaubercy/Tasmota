import base64

with open("outils_docs/scripts_python/tasmota_logo_icon_249443.png","rb") as f:
    b64 = base64.b64encode(f.read()).decode()
print("data:image/x-icon;base64," + b64)
