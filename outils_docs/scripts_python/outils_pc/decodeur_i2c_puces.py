"""Puces I2C du parc et traduction de leurs registres (decodeur_i2c.py).

Inventaire du 2026-10-31 (persists de data/<lieu>/<carte>) : ADS1115 (0x48), MCP23017 et TCA9554 (0x20),
DS3231 (0x68), ES8311 (0x18, P4), MPU6050 (0x68, bloc « inclinaison » des volets). Toutes sont a pointeur
de registre : une ecriture commence par le numero du registre, une lecture repart du dernier pointeur ecrit.

Chaque puce : nom, adresses possibles, taille d'un registre (octets), auto-increment du pointeur, noms des
registres, et deux fonctions facultatives :
    valeur(reg, v, mem) -> texte      valeur d'un registre (v : entier, gros-boutiste si 2 octets) ;
    resume(ptr, d, mem) -> texte|None  lecture groupee (date du DS3231, mesures du MPU6050).
`mem` est la memoire de l'adresse (pointeur, plage de l'ADS1115...), tenue par decodeur_i2c.Decodeur.
"""


def _signe(v, bits=16):
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


def _bits(v, prefixe, actifs="haut"):
    hauts = [f"{prefixe}{i}" for i in range(8) if v >> i & 1]
    return f"0b{v:08b} -> {actifs} : {' '.join(hauts) if hauts else 'aucune'}"


# ---------------------------------------------------------------- ADS1115
PGA = (6.144, 4.096, 2.048, 1.024, 0.512, 0.256, 0.256, 0.256)
MUX = ("AIN0-AIN1", "AIN0-AIN3", "AIN1-AIN3", "AIN2-AIN3", "AIN0-GND", "AIN1-GND", "AIN2-GND", "AIN3-GND")
SPS = (8, 16, 32, 64, 128, 250, 475, 860)


def _ads_valeur(reg, v, mem):
    if reg == 1:
        mem["pga"] = PGA[v >> 9 & 7]
        return (f"OS={v >> 15} {MUX[v >> 12 & 7]} PGA=±{PGA[v >> 9 & 7]} V "
                f"{'unique' if v >> 8 & 1 else 'continu'} {SPS[v >> 5 & 7]} SPS comparateur={'coupe' if (v & 3) == 3 else 'actif'}")
    if reg == 0:
        brut = _signe(v)
        if "pga" in mem:
            return f"{brut} = {brut * mem['pga'] / 32768 * 1000:.1f} mV (PGA ±{mem['pga']} V)"
        return f"{brut} (plage inconnue : configuration non vue)"
    return str(_signe(v))


# ---------------------------------------------------------------- MCP23017 (IOCON.BANK = 0)
MCP_NOMS = ["IODIR", "IPOL", "GPINTEN", "DEFVAL", "INTCON", "IOCON", "GPPU", "INTF", "INTCAP", "GPIO", "OLAT"]
MCP_SENS = {"IODIR": "entree", "GPIO": "haut", "OLAT": "haut", "GPPU": "tirage", "IPOL": "inverse",
            "GPINTEN": "interruption", "INTF": "interruption"}


def _mcp_valeur(reg, v, mem):
    nom = MCP_NOMS[reg // 2] if reg < 22 else ""
    return _bits(v, "AB"[reg % 2], MCP_SENS.get(nom, "a 1")) if nom else f"0x{v:02X}"


# ---------------------------------------------------------------- TCA9554 / TCA9554A
TCA_SENS = {0: "haut", 1: "haut", 2: "inverse", 3: "entree"}


def _tca_valeur(reg, v, mem):
    return _bits(v, "P", TCA_SENS.get(reg, "a 1"))


# ---------------------------------------------------------------- DS3231
def _bcd(v):
    return (v >> 4) * 10 + (v & 15)


def _ds_resume(ptr, d, mem):
    textes = []
    if ptr == 0 and len(d) >= 7:
        h = d[2]
        if h & 0x40:                    # mode 12 h : bit 5 = apres-midi
            heure = _bcd(h & 0x1F) % 12 + (12 if h & 0x20 else 0)
        else:
            heure = _bcd(h & 0x3F)
        textes.append(f"20{_bcd(d[6]):02d}-{_bcd(d[5] & 0x1F):02d}-{_bcd(d[4]):02d} "
                      f"{heure:02d}:{_bcd(d[1]):02d}:{_bcd(d[0] & 0x7F):02d}")
    debut_t = 0x11 - ptr
    if 0 <= debut_t and debut_t + 1 < len(d):
        textes.append(f"temperature {_signe(d[debut_t], 8) + (d[debut_t + 1] >> 6) * 0.25:.2f} °C")
    return " ; ".join(textes) or None


def _ds_valeur(reg, v, mem):
    return f"0x{v:02X} (BCD {_bcd(v)})" if reg <= 6 else f"0x{v:02X}"


# ---------------------------------------------------------------- MPU6050
MPU_NOMS = {0x19: "SMPLRT_DIV", 0x1A: "CONFIG", 0x1B: "GYRO_CONFIG", 0x1C: "ACCEL_CONFIG",
            0x3B: "ACCEL_XOUT_H", 0x3C: "ACCEL_XOUT_L", 0x3D: "ACCEL_YOUT_H", 0x3E: "ACCEL_YOUT_L",
            0x3F: "ACCEL_ZOUT_H", 0x40: "ACCEL_ZOUT_L", 0x41: "TEMP_OUT_H", 0x42: "TEMP_OUT_L",
            0x43: "GYRO_XOUT_H", 0x44: "GYRO_XOUT_L", 0x45: "GYRO_YOUT_H", 0x46: "GYRO_YOUT_L",
            0x47: "GYRO_ZOUT_H", 0x48: "GYRO_ZOUT_L", 0x6B: "PWR_MGMT_1", 0x6C: "PWR_MGMT_2", 0x75: "WHO_AM_I"}


def _mpu_valeur(reg, v, mem):
    if reg == 0x1C:
        mem["afs"] = v >> 3 & 3
        return f"accelerometre ±{2 << (v >> 3 & 3)} g"
    if reg == 0x1B:
        mem["gfs"] = v >> 3 & 3
        return f"gyroscope ±{250 << (v >> 3 & 3)} °/s"
    if reg == 0x6B:
        return f"0x{v:02X} ({'en sommeil' if v & 0x40 else 'eveille'})"
    if reg == 0x75:
        return f"0x{v:02X}" + (" = MPU6050" if v == 0x68 else " (pas un MPU6050 ?)")
    return f"0x{v:02X}"


def _mpu_resume(ptr, d, mem):
    mesures = []
    for base, nom, conv in ((0x3B, "ax", lambda r: f"{r / (16384 >> mem.get('afs', 0)):.3f} g"),
                            (0x3D, "ay", lambda r: f"{r / (16384 >> mem.get('afs', 0)):.3f} g"),
                            (0x3F, "az", lambda r: f"{r / (16384 >> mem.get('afs', 0)):.3f} g"),
                            (0x41, "T", lambda r: f"{r / 340 + 36.53:.1f} °C"),
                            (0x43, "gx", lambda r: f"{r / (131 / (1 << mem.get('gfs', 0))):.1f} °/s"),
                            (0x45, "gy", lambda r: f"{r / (131 / (1 << mem.get('gfs', 0))):.1f} °/s"),
                            (0x47, "gz", lambda r: f"{r / (131 / (1 << mem.get('gfs', 0))):.1f} °/s")):
        i = base - ptr
        if 0 <= i and i + 1 < len(d):
            mesures.append(f"{nom}={conv(_signe(d[i] << 8 | d[i + 1]))}")
    return " ".join(mesures) or None


# ---------------------------------------------------------------- ES8311 (noms seulement)
ES_NOMS = {0x00: "RESET", 0x01: "CLK_MANAGER1", 0x02: "CLK_MANAGER2", 0x03: "CLK_MANAGER3", 0x04: "CLK_MANAGER4",
           0x05: "CLK_MANAGER5", 0x06: "CLK_MANAGER6", 0x07: "CLK_MANAGER7", 0x08: "CLK_MANAGER8",
           0x09: "SDPIN", 0x0A: "SDPOUT", 0x0B: "SYSTEM_0B", 0x0C: "SYSTEM_0C", 0x0D: "SYSTEM_0D", 0x0E: "SYSTEM_0E",
           0x0F: "SYSTEM_0F", 0x10: "SYSTEM_10", 0x11: "SYSTEM_11", 0x12: "SYSTEM_12", 0x13: "SYSTEM_13",
           0x14: "SYSTEM_14", 0x15: "ADC_15", 0x16: "ADC_16", 0x17: "ADC_VOLUME", 0x1C: "ADC_1C",
           0x31: "DAC_MUTE", 0x32: "DAC_VOLUME", 0x37: "DAC_RAMP", 0x44: "GPIO_44", 0x45: "GP_45",
           0xFD: "CHIP_ID1", 0xFE: "CHIP_ID2", 0xFF: "CHIP_VER"}


PUCES = {
    "ADS1115": {"nom": "ADS1115 (CAN 16 bits)", "adresses": range(0x48, 0x4C), "taille": 2, "auto_inc": False,
                "registres": {0: "Conversion", 1: "Config", 2: "Lo_thresh", 3: "Hi_thresh"}, "valeur": _ads_valeur},
    "MCP23017": {"nom": "MCP23017 (16 E/S)", "adresses": range(0x20, 0x28), "taille": 1, "auto_inc": True,
                 "registres": {r: MCP_NOMS[r // 2] + "AB"[r % 2] for r in range(22)}, "valeur": _mcp_valeur},
    "TCA9554": {"nom": "TCA9554 (8 E/S)", "adresses": [*range(0x20, 0x28), *range(0x38, 0x40)], "taille": 1,
                "auto_inc": False, "registres": {0: "Entrees", 1: "Sorties", 2: "Inversion", 3: "Configuration"},
                "valeur": _tca_valeur},
    "DS3231": {"nom": "DS3231 (horloge)", "adresses": [0x68], "taille": 1, "auto_inc": True,
               "registres": {0: "Secondes", 1: "Minutes", 2: "Heures", 3: "Jour", 4: "Date", 5: "Mois", 6: "Annee",
                             0x0E: "Controle", 0x0F: "Etat", 0x10: "Vieillissement", 0x11: "Temp_MSB", 0x12: "Temp_LSB"},
               "valeur": _ds_valeur, "resume": _ds_resume},
    "MPU6050": {"nom": "MPU6050 (inclinaison)", "adresses": [0x68, 0x69], "taille": 1, "auto_inc": True,
                "registres": MPU_NOMS, "valeur": _mpu_valeur, "resume": _mpu_resume},
    "ES8311": {"nom": "ES8311 (codec audio)", "adresses": [0x18, 0x19], "taille": 1, "auto_inc": True,
               "registres": ES_NOMS},
}
