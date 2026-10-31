// Banc PC de la machine a etats I2C (src/machine_i2c.h), sans carte.
// Lancement : python outils_docs/firmware_sniffeur_i2c/banc/lance_banc.py  (code de sortie 0 = vert)
#include <cstdio>
#include <cstring>
#include <vector>
#include "../src/machine_i2c.h"

static int echecs = 0;
#define VERIFIE(cond) do { if (!(cond)) { std::printf("ECHEC ligne %d : %s\n", __LINE__, #cond); echecs++; } } while (0)

struct Bus {
  MachineI2C m;
  uint64_t t = 0;
  std::vector<TransactionI2C> vues;
  bool sda = true, scl = true;
  void ech(bool s, bool c) {
    t += 10;
    sda = s; scl = c;
    avance(m, s, c, t);
    if (m.prete) vues.push_back(m.sortie);
  }
  void start() { ech(1, 1); ech(0, 1); ech(0, 0); }
  void restart() { ech(1, 0); ech(1, 1); ech(0, 1); ech(0, 0); }
  void stop() { ech(0, 0); ech(0, 1); ech(1, 1); }
  void bit(bool b) { ech(b, 0); ech(b, 1); ech(b, 0); }
  // SDA change dans le meme echantillon que le front montant de SCL (echantillonnage lent)
  void bit_serre(bool b) { ech(b, 1); ech(b, 0); }
  void octet(uint8_t v, bool ack, bool serre = false) {
    for (int i = 7; i >= 0; i--) serre ? bit_serre((v >> i) & 1) : bit((v >> i) & 1);
    serre ? bit_serre(!ack) : bit(!ack);
  }
};

static void ecriture_un_octet(bool serre) {
  Bus b;
  b.start(); b.octet(0x48 << 1, true, serre); b.octet(0x01, true, serre); b.stop();
  VERIFIE(b.vues.size() == 1);
  if (b.vues.size() != 1) return;
  const TransactionI2C& x = b.vues[0];
  VERIFIE(x.adresse == 0x48); VERIFIE(!x.lecture); VERIFIE(x.n == 1); VERIFIE(x.d[0] == 0x01);
  VERIFIE(x.nack == -1); VERIFIE(x.fin == FIN_STOP); VERIFIE(x.fronts == 18); VERIFIE(x.trop == 0);
  VERIFIE(x.t_dernier > x.t_premier);
}

static void lecture_apres_restart() {
  Bus b;
  b.start(); b.octet(0x90, true); b.octet(0x00, true);
  b.restart(); b.octet(0x91, true); b.octet(0x12, true); b.octet(0x34, false); b.stop();
  VERIFIE(b.vues.size() == 2);
  if (b.vues.size() != 2) return;
  VERIFIE(b.vues[0].adresse == 0x48); VERIFIE(!b.vues[0].lecture); VERIFIE(b.vues[0].fin == FIN_RESTART);
  VERIFIE(b.vues[0].n == 1); VERIFIE(b.vues[0].d[0] == 0x00);
  VERIFIE(b.vues[1].lecture); VERIFIE(b.vues[1].n == 2);
  VERIFIE(b.vues[1].d[0] == 0x12); VERIFIE(b.vues[1].d[1] == 0x34);
  VERIFIE(b.vues[1].nack == -1);              // NACK du maitre en fin de lecture : normal
  VERIFIE(b.vues[1].fin == FIN_STOP);
}

static void nack_adresse() {
  Bus b;
  b.start(); b.octet(0x77 << 1, false); b.stop();
  VERIFIE(b.vues.size() == 1);
  if (b.vues.empty()) return;
  VERIFIE(b.vues[0].adresse == 0x77); VERIFIE(b.vues[0].nack == 0); VERIFIE(b.vues[0].n == 0);
  VERIFIE(b.vues[0].fin == FIN_STOP);
}

static void nack_donnee() {
  Bus b;
  b.start(); b.octet(0x40, true); b.octet(0xAA, true); b.octet(0xBB, false); b.stop();
  VERIFIE(b.vues.size() == 1);
  if (b.vues.empty()) return;
  VERIFIE(b.vues[0].nack == 2); VERIFIE(b.vues[0].n == 2);
}

static void stop_au_milieu() {
  Bus b;
  b.start(); b.octet(0x40, true); b.bit(1); b.bit(0); b.bit(1); b.stop();
  VERIFIE(b.vues.size() == 1);
  if (b.vues.empty()) return;
  VERIFIE(b.vues[0].fin == FIN_TRONQUE); VERIFIE(b.vues[0].n == 0);
}

static void debordement() {
  Bus b;
  b.start(); b.octet(0x40, true);
  for (int i = 0; i < I2C_MAX_OCTETS + 6; i++) b.octet((uint8_t)i, true);
  b.stop();
  VERIFIE(b.vues.size() == 1);
  if (b.vues.empty()) return;
  VERIFIE(b.vues[0].n == I2C_MAX_OCTETS); VERIFIE(b.vues[0].trop == 6);
  VERIFIE(b.vues[0].d[I2C_MAX_OCTETS - 1] == I2C_MAX_OCTETS - 1);
}

static void parasite_ignore() {
  Bus b;
  b.start(); b.stop();                  // START puis STOP sans aucun bit
  b.ech(1, 0); b.ech(0, 0); b.ech(1, 0); // SDA bouge pendant que SCL est bas : rien
  VERIFIE(b.vues.empty());
}

int main() {
  ecriture_un_octet(false);
  ecriture_un_octet(true);
  lecture_apres_restart();
  nack_adresse();
  nack_donnee();
  stop_au_milieu();
  debordement();
  parasite_ignore();
  std::printf(echecs ? "ROUGE : %d echec(s)\n" : "VERT : machine I2C\n", echecs);
  return echecs ? 1 : 0;
}
