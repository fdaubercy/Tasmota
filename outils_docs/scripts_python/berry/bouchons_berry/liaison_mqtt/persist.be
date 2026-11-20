# Bouchon du module natif 'persist' pour banc_mqtt_liaison.be : find() sur une map. drivers.liaisonMqtt : seuils de
# garde-fous reduits (lecture du persist) et esclaves declares (un actif a deux segments, un actif a un segment,
# un inactif, un sans topic).
var persist = module("persist")
persist._p = {"drivers": {"liaisonMqtt": {"activation": "ON", "garde": {"maxParElement": 4, "delaiAccuseMs": 1500, "essaisMax": "x"},
    "esclaves": {"projecteur": {"activation": "ON", "topic": "jardin/projecteur_led"},
                 "pompe": {"activation": "ON", "topic": "pompe"},
                 "inactif": {"activation": "OFF", "topic": "x/inactif"},
                 "a/b": {"activation": "ON", "topic": "q/r"},
                 "joker": {"activation": "ON", "topic": "x/+"},
                 "sanstopic": {"activation": "ON"}}}},
    "modules": {"maison": {"environnement": {
        "thermometres": {"t1": {"virtuel": "MQTT_projecteur", "mqtt": {"chemin": "DS18B20.Temperature"}}, "t2": {"virtuel": "OFF"}, "t3": {"virtuel": "MQTT_projecteur"}, "t4": {"virtuel": "MQTT_projecteur", "mqtt": {"chemin": "Button1"}}},
        "analogiques": {"a1": {"activation": "ON", "nom": "Niveau pompe", "value": 512, "virtuel": "MQTT_pompe", "mqtt": {"chemin": "ANALOG.A1"}}, "a2": {"virtuel": "MQTT_pompe", "mqtt": {"chemin": "sensors.niveau.volume", "declencheur": "ANALOG#A2"}},
                        "a3": {"activation": "OFF", "nom": "Inactif pompe", "virtuel": "MQTT_pompe"}},
        "boutons": {"b1": {"virtuel": "MQTT_projecteur", "mqtt": {"chemin": "Button1"}}},
        "interrupteurs": {"s1": {"virtuel": "MQTT_pompe", "mqtt": {"chemin": "Switch1"}}},
        "relais": {"r1": {"activation": "ON", "nom": "Relais pompe", "virtuel": "MQTT_pompe", "mqtt": {"commande": "Power1"}}},
        "compteurs": {"c1": {"virtuel": "MQTT_inactif", "mqtt": {"chemin": "COUNTER.C1"}}}}}}}
persist.find = def (k, d) return persist._p.find(k, d) end
return persist
