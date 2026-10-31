// Sniffeur I2C passif sur ESP32-S3 : ecoute SDA/SCL et envoie une ligne texte par transaction sur l'USB natif.
// Protocole v=1 : docs/superpowers/specs/2026-10-31-sniffeur-i2c-design.md §5.
//
// Coeur 1 : boucle d'ecoute SANS interruption (un tick FreeRTOS de quelques us suffit a manquer un front de
// SCL a 400 kHz). Sans interruption, le tick du coeur 1 ne tourne plus : le chien de garde des interruptions
// (CONFIG_ESP_INT_WDT_CHECK_CPU1, MWDT1) redemarrerait la carte en 300 ms -> il est coupe au demarrage.
// Coeur 0 : USB, ordres du PC, mode maitre (Wire). Les deux coeurs ne partagent qu'un tampon circulaire
// (un ecrivain par index) et quelques compteurs.
#include <Arduino.h>
#include <Wire.h>
#include "esp_cpu.h"
#include "hal/wdt_hal.h"
#include "soc/gpio_reg.h"
#include "soc/timer_group_struct.h"
#include "machine_i2c.h"

#ifndef BROCHE_SDA
#define BROCHE_SDA 4
#endif
#ifndef BROCHE_SCL
#define BROCHE_SCL 5
#endif
static_assert(BROCHE_SDA < 32 && BROCHE_SCL < 32, "broches lues dans GPIO_IN_REG (GPIO 0 a 31)");

static const int VERSION = 1;
static const uint32_t TAILLE = 256;                 // transactions en attente d'emission (puissance de 2)
static const uint32_t BUS_BLOQUE_MS = 50;           // SDA basse plus longtemps, bus au repos : bus bloque
static const uint32_t SILENCE_AVANT_MAITRE_MS = 2000;
static const uint32_t FREQ_MAITRE = 100000;
static const uint32_t MASQUE_SDA = 1u << BROCHE_SDA, MASQUE_SCL = 1u << BROCHE_SCL;

static TransactionI2C tampon[TAILLE];
static volatile uint32_t tete = 0;                  // ecrit par le coeur 1 seul
static volatile uint32_t queue_ = 0;                // ecrit par le coeur 0 seul
static volatile uint32_t perdues = 0;               // tampon plein (coeur 1 ajoute, coeur 0 remet a 0)
static volatile uint32_t activite = 0;              // +1 a chaque changement des broches
static volatile uint32_t bloque_ms = 0;             // > 0 : bus bloque a signaler
static volatile uint32_t mhz_echantillons = 0;      // vitesse mesuree de la boucle d'ecoute
static volatile bool pause_demandee = false, en_pause = false;
static uint32_t mhz_cpu = 240;

static void coupe_chien_de_garde_interruptions() {
  wdt_hal_context_t ctx;
  ctx.inst = WDT_MWDT1;
  ctx.mwdt_dev = &TIMERG1;
  wdt_hal_write_protect_disable(&ctx);
  wdt_hal_disable(&ctx);
  wdt_hal_write_protect_enable(&ctx);
}

static void broches_en_ecoute() {                   // haute impedance : le sniffeur ne touche pas au bus
  pinMode(BROCHE_SDA, INPUT);
  pinMode(BROCHE_SCL, INPUT);
}

static inline void pousse(const TransactionI2C& tr) {
  uint32_t t = tete, suivant = (t + 1) & (TAILLE - 1);
  if (suivant == queue_) {
    __atomic_fetch_add(&perdues, 1, __ATOMIC_RELAXED);
    return;
  }
  tampon[t] = tr;
  __atomic_store_n(&tete, suivant, __ATOMIC_RELEASE);
}

static void ecoute(void*) {
  coupe_chien_de_garde_interruptions();
  portDISABLE_INTERRUPTS();
  MachineI2C m;
  uint32_t prec = esp_cpu_get_cycle_count(), c_controle = prec, compteur = 0;
  uint64_t haut = 0, t_change = 0;
  uint32_t etat_prec = 0xFFFFFFFF;
  bool bloque_signale = false;
  for (;;) {
    uint32_t etat = REG_READ(GPIO_IN_REG) & (MASQUE_SDA | MASQUE_SCL);
    uint32_t c = esp_cpu_get_cycle_count();
    if (c < prec) haut += (1ULL << 32);
    prec = c;
    uint64_t t = haut | c;
    if (etat != etat_prec) {
      etat_prec = etat;
      t_change = t;
      bloque_signale = false;
      activite = activite + 1;
      avance(m, etat & MASQUE_SDA, etat & MASQUE_SCL, t);
      if (m.prete) pousse(m.sortie);
      continue;
    }
    if (++compteur & 0xFFFF) continue;
    // toutes les 65536 boucles : vitesse, bus bloque, pause demandee par le coeur 0
    mhz_echantillons = (uint32_t)(65536ULL * mhz_cpu / (uint32_t)(c - c_controle));
    c_controle = c;
    uint64_t calme_ms = (t - t_change) / (mhz_cpu * 1000ULL);
    if (!(etat & MASQUE_SDA) && !m.en_cours && calme_ms > BUS_BLOQUE_MS && !bloque_signale) {
      bloque_ms = (uint32_t)calme_ms;
      bloque_signale = true;
    }
    if (pause_demandee) {
      en_pause = true;
      while (pause_demandee) {}
      en_pause = false;
      m = MachineI2C();                             // le mode maitre a remue le bus : repartir au repos
      etat_prec = 0xFFFFFFFF;
    }
  }
}

// ---------- coeur 0 : emission, ordres ----------

static char ligne[64 * 2 + 160];

static void hexa(char* dst, const uint8_t* d, int n) {
  static const char H[] = "0123456789ABCDEF";
  if (n == 0) { *dst++ = '-'; }
  for (int i = 0; i < n; i++) { *dst++ = H[d[i] >> 4]; *dst++ = H[d[i] & 15]; }
  *dst = 0;
}

static void emet_transaction(const TransactionI2C& x) {
  static const char* FIN[] = {"STOP", "RESTART", "TRONQUE"};
  char d[I2C_MAX_OCTETS * 2 + 2], nack[6] = "-";
  hexa(d, x.d, x.n);
  if (x.nack >= 0) snprintf(nack, sizeof nack, "%d", x.nack);
  double khz = 0;
  if (x.fronts >= 2 && x.t_dernier > x.t_premier)
    khz = (x.fronts - 1) * 1000.0 * mhz_cpu / (double)(x.t_dernier - x.t_premier);
  int k = snprintf(ligne, sizeof ligne, "X t=%llu a=%02X rw=%c d=%s nack=%s fin=%s f=%.1f",
                   (unsigned long long)(x.t_debut / mhz_cpu), x.adresse, x.lecture ? 'R' : 'W', d, nack,
                   FIN[x.fin], khz);
  if (x.trop) snprintf(ligne + k, sizeof ligne - k, " trop=%u", x.trop);
  Serial.println(ligne);
}

static void emet_identite() {
  Serial.printf("I v=%d puce=esp32s3 sda=%d scl=%d mode=ecoute ech=%u\n", VERSION, BROCHE_SDA, BROCHE_SCL,
                (unsigned)mhz_echantillons);
}

static bool champ(const char* l, const char* cle, char* val, size_t taille) {
  const char* p = strstr(l, cle);
  if (!p) return false;
  p += strlen(cle);
  size_t i = 0;
  while (*p && *p != ' ' && i + 1 < taille) val[i++] = *p++;
  val[i] = 0;
  return i > 0;
}

static int lit_hexa(const char* s, uint8_t* d, int max) {     // -1 si invalide
  int n = (int)strlen(s);
  if (n % 2 || n / 2 > max) return -1;
  for (int i = 0; i < n / 2; i++) {
    char o[3] = {s[2 * i], s[2 * i + 1], 0};
    char* fin;
    d[i] = (uint8_t)strtoul(o, &fin, 16);
    if (*fin) return -1;
  }
  return n / 2;
}

static void ordre_maitre(const char* l, uint32_t derniere_activite_ms) {
  bool ecrit = l[1] == 'W', lit = (l[1] == 'R') || (l[1] == 'W' && l[2] == 'R');
  char v[80];
  uint8_t d[32];
  int nd = 0, n = 0;
  long a = champ(l, "a=", v, sizeof v) ? strtol(v, nullptr, 16) : -1;
  if (ecrit && (!champ(l, "d=", v, sizeof v) || (nd = lit_hexa(v, d, 32)) <= 0)) a = -1;
  if (lit && (!champ(l, "n=", v, sizeof v) || (n = atoi(v)) < 1 || n > 32)) a = -1;
  if (a < 0x03 || a > 0x77) { Serial.println("M ok=0 err=parametre"); return; }
  if (millis() - derniere_activite_ms < SILENCE_AVANT_MAITRE_MS) { Serial.println("M ok=0 err=bus_actif"); return; }

  pause_demandee = true;
  uint32_t debut = millis();
  while (!en_pause && millis() - debut < 200) delay(1);
  if (!en_pause) { pause_demandee = false; Serial.println("M ok=0 err=ecoute_figee"); return; }
  Wire.begin(BROCHE_SDA, BROCHE_SCL, FREQ_MAITRE);
  const char* err = nullptr;
  uint8_t lus[32];
  int nl = 0;
  if (ecrit) {
    Wire.beginTransmission((uint8_t)a);
    Wire.write(d, nd);
    uint8_t r = Wire.endTransmission(!lit);           // MWR : RESTART avant la lecture
    if (r == 2) err = "nack_adresse"; else if (r == 3) err = "nack_donnee"; else if (r) err = "bus";
  }
  if (!err && lit) {
    nl = Wire.requestFrom((uint8_t)a, (uint8_t)n);
    for (int i = 0; i < nl && Wire.available(); i++) lus[i] = Wire.read();
    if (nl != n) err = nl == 0 ? "nack_adresse" : "lecture_courte";
  }
  Wire.end();
  broches_en_ecoute();
  pause_demandee = false;
  if (err) { Serial.printf("M ok=0 err=%s\n", err); return; }
  char h[66];
  hexa(h, lus, nl);
  Serial.printf("M ok=1 d=%s\n", h);
}

static void emission(void*) {
  Serial.begin(115200);                               // USB natif : l'ISR est installee sur CE coeur (0)
  uint32_t vu = activite, derniere_activite_ms = 0;
  char cmd[120];
  size_t ncmd = 0;
  emet_identite();
  for (;;) {
    bool rien = true;
    while (queue_ != __atomic_load_n(&tete, __ATOMIC_ACQUIRE)) {
      emet_transaction(tampon[queue_]);
      queue_ = (queue_ + 1) & (TAILLE - 1);
      rien = false;
    }
    uint32_t p = __atomic_exchange_n(&perdues, 0, __ATOMIC_RELAXED);
    if (p) Serial.printf("P n=%u\n", (unsigned)p);
    if (bloque_ms) { Serial.printf("B sda=bas ms=%u\n", (unsigned)bloque_ms); bloque_ms = 0; }
    if (activite != vu) { vu = activite; derniere_activite_ms = millis(); }
    while (Serial.available()) {
      char ch = (char)Serial.read();
      if (ch == '\r') continue;
      if (ch != '\n') { if (ncmd + 1 < sizeof cmd) cmd[ncmd++] = ch; continue; }
      cmd[ncmd] = 0;
      ncmd = 0;
      if (strcmp(cmd, "?") == 0) emet_identite();
      else if (cmd[0] == 'M' && (cmd[1] == 'W' || cmd[1] == 'R')) ordre_maitre(cmd, derniere_activite_ms);
      else if (cmd[0]) Serial.println("M ok=0 err=ordre_inconnu");
    }
    if (rien) vTaskDelay(1);
  }
}

void setup() {
  mhz_cpu = getCpuFrequencyMhz();
  broches_en_ecoute();
  xTaskCreatePinnedToCore(emission, "emission", 6144, nullptr, 5, nullptr, 0);
  delay(300);                                          // laisse l'USB s'installer sur le coeur 0
  // derniere instruction : la tache d'ecoute prend le coeur 1 pour toujours (setup/loop n'y reviennent pas)
  xTaskCreatePinnedToCore(ecoute, "ecoute", 4096, nullptr, configMAX_PRIORITIES - 1, nullptr, 1);
}

void loop() {}
