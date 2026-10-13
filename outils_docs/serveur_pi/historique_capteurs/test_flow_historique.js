#!/usr/bin/env node
// Banc de test du noeud « Aplatir -> line protocol » : le JS est EXTRAIT du flow
// (flow-historique-capteurs.json), pas recopie, puis execute dans un bac a sable vm.
// Usage : node test_flow_historique.js        (code de sortie 0 = vert)
//         node test_flow_historique.js --temoin  (mutations : le banc DOIT echouer)
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const flow = JSON.parse(fs.readFileSync(path.join(__dirname, 'flow-historique-capteurs.json'), 'utf8'));
const code = flow.find((n) => n.id === 'f_aplatit').func;
const TS = 1792000000; // heure de reception figee
const prep = flow.find((n) => n.id === 'f_prep').func;

function lance(source, msg, vars) {
    const sandbox = {
        Buffer,
        env: { get: (k) => (vars || {})[k] },
        Date: class extends Date { static now() { return TS * 1000; } },
    };
    return vm.runInNewContext('(function(msg){' + source + '\n})', sandbox)(msg);
}
const sortie = (source, topic, payload) => {
    const r = lance(source, { topic, payload });
    return r === null ? null : r.payload;
};

const cuve = {
    Time: '2026-10-13T14:05:00',
    DS18B20: { Id: '0316A2794A3C', Temperature: 12.4 },
    ADS1115: { A0: 1234, A1: 5, A2: 0, A3: 0 },
    sensorsCuve: { valeursAnalogiques: { valeurCapteurHauteur: 2.31 }, niveauCuve: { hauteurEau: 83.5, tauxRemplissage: 0.76, volume: 4180 } },
    TempUnit: 'C',
};
const etat = {
    Time: '2026-10-13T14:05:00', Uptime: '1T02:03:04', UptimeSec: 93784, Heap: 150, LoadAvg: 19,
    POWER1: 'ON', POWER2: 'OFF', Wifi: { AP: 1, SSId: 'maison', RSSI: 62, Signal: -69, LinkCount: 1 },
};

const cas = [
    ['SENSOR cuve', 'tele/tasmota_cuve/SENSOR', cuve,
        'capteurs,appareil=tasmota_cuve ADS1115_A0=1234,ADS1115_A1=5,ADS1115_A2=0,ADS1115_A3=0,DS18B20_Temperature=12.4,' +
        'sensorsCuve_niveauCuve_hauteurEau=83.5,sensorsCuve_niveauCuve_tauxRemplissage=0.76,sensorsCuve_niveauCuve_volume=4180,' +
        'sensorsCuve_valeursAnalogiques_valeurCapteurHauteur=2.31 ' + TS],
    ['STATE POWER1 ON + Wifi.RSSI', 'tele/tasmota_garage/STATE', etat,
        'etat,appareil=tasmota_garage Heap=150,LoadAvg=19,POWER1=1,POWER2=0,UptimeSec=93784,Wifi_AP=1,Wifi_LinkCount=1,Wifi_RSSI=62,Wifi_Signal=-69 ' + TS],
    ['aucun champ numerique -> ignore', 'tele/tasmota_x/SENSOR', { Time: '2026-10-13T14:05:00', TempUnit: 'C', DS18B20: { Id: 'ABC' } }, null],
    ['cle avec espace echappee', 'tele/ma carte,a=b/SENSOR', { 'Mon capteur': { 'Temp,1=x': 21.5 }, DHT: 'texte' },
        'capteurs,appareil=ma\\ carte\\,a\\=b Mon\\ capteur_Temp\\,1\\=x=21.5 ' + TS],
    ['DS18B20 multiples + AM2301 + COUNTER + Switch', 'tele/tasmota_b/SENSOR',
        { 'DS18B20-1': { Temperature: 9 }, 'DS18B20-2': { Temperature: -1.5 }, AM2301: { Temperature: 20.1, Humidity: 55 }, COUNTER: { C1: 42 }, Switch1: 'ON' },
        'capteurs,appareil=tasmota_b AM2301_Humidity=55,AM2301_Temperature=20.1,COUNTER_C1=42,DS18B20-1_Temperature=9,DS18B20-2_Temperature=-1.5,Switch1=1 ' + TS],
    ['payload chaine JSON / Buffer', 'tele/t/SENSOR', Buffer.from('{"COUNTER":{"C1":3}}'), 'capteurs,appareil=t COUNTER_C1=3 ' + TS],
    ['topic non tele/.../SENSOR|STATE', 'tele/t/LWT', { a: 1 }, null],
    ['topic multi-niveaux', 'tele/cave/serveur-rly-cave-v2/SENSOR', { DS18B20: { Temperature: 14.2 } }, 'capteurs,appareil=cave/serveur-rly-cave-v2 DS18B20_Temperature=14.2 1792000000'],
    ['JSON invalide', 'tele/t/SENSOR', '{pas du json', null],
];

function banc(source) {
    let echecs = 0;
    for (const [nom, topic, payload, attendu] of cas) {
        let obtenu;
        try { obtenu = sortie(source, topic, payload); } catch (e) { obtenu = 'EXCEPTION ' + e.message; }
        const ok = obtenu === attendu;
        if (!ok) { echecs++; }
        if (!banc.silencieux) {
            console.log((ok ? 'OK    ' : 'ECHEC ') + nom);
            if (!ok) { console.log('   attendu: ' + attendu + '\n   obtenu : ' + obtenu); }
        }
    }
    // le noeud d'authentification : en-tete Basic seulement si INFLUX_USER est defini
    const h1 = lance(prep, {}, { INFLUX_USER: 'u', INFLUX_PASSWORD: 'p' }).headers.Authorization;
    const h0 = lance(prep, {}, {}).headers.Authorization;
    const okAuth = h1 === 'Basic ' + Buffer.from('u:p').toString('base64') && h0 === undefined;
    if (!okAuth) { echecs++; }
    if (!banc.silencieux) { console.log((okAuth ? 'OK    ' : 'ECHEC ') + 'authentification par variables d\'environnement'); }
    return echecs;
}

if (process.argv.includes('--temoin')) {
    banc.silencieux = true;
    const mutations = [
        ['ne plus convertir "ON" en 1', "if (valeur === 'ON') { champs[chemin] = 1; }", "if (valeur === 'ON') { }"],
        ['ne plus echapper les espaces', "([,= ])", "([,=])"],
    ];
    let tous = true;
    for (const [nom, de, vers] of mutations) {
        if (!code.includes(de)) { console.log('TEMOIN INVALIDE (motif introuvable) : ' + nom); process.exit(2); }
        const n = banc(code.replace(de, vers));
        console.log((n > 0 ? 'temoin OK (banc rouge, ' + n + ' echec(s))' : 'TEMOIN RATE (banc reste vert)') + ' : ' + nom);
        if (n === 0) { tous = false; }
    }
    process.exit(tous ? 0 : 1);
}

const echecs = banc(code);
console.log(echecs === 0 ? '\nTOUT VERT' : '\n' + echecs + ' ECHEC(S)');
process.exit(echecs === 0 ? 0 : 1);
