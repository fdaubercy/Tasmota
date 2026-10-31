// Machine a etats I2C PASSIVE : decode les transactions a partir des echantillons (SDA, SCL, instant).
// Pure (ni Arduino ni ESP-IDF) pour etre testee sur PC : banc/test_machine.cpp.
//
// Regles I2C appliquees :
//   - START / RESTART : SDA descend pendant que SCL reste haut ; STOP : SDA monte pendant que SCL reste haut ;
//   - un bit de donnee = SDA lue au front montant de SCL (un changement simultane de SDA et du front montant
//     est lu comme une donnee : SDA a change pendant la phase basse precedente). Le bit n'est COMPTE qu'au
//     front descendant suivant : le front montant qui precede un STOP ou un RESTART n'est pas une donnee,
//     on ne le sait qu'en voyant SDA bouger pendant que SCL reste haut ;
//   - 8 bits puis un 9e = ACK (SDA basse) ou NACK ; le 1er octet est l'adresse 7 bits + R/W.
// En lecture, le NACK du maitre sur le dernier octet est la fin normale : il n'est pas signale.
#pragma once
#include <stdint.h>

#ifndef I2C_MAX_OCTETS
#define I2C_MAX_OCTETS 64
#endif

enum FinI2C : uint8_t { FIN_STOP = 0, FIN_RESTART = 1, FIN_TRONQUE = 2 };

struct TransactionI2C {
  uint64_t t_debut;        // instant du START (unite de l'appelant : cycles CPU sur l'ESP32)
  uint64_t t_premier;      // 1er front montant de SCL
  uint64_t t_dernier;      // dernier front montant de SCL
  uint32_t fronts;         // fronts montants de SCL, ACK compris (frequence = (fronts - 1) / duree)
  uint16_t trop;           // octets au-dela de I2C_MAX_OCTETS : comptes, non memorises
  int8_t nack;             // -1 : tout acquitte ; 0 : adresse non acquittee ; k : k-ieme octet ECRIT non acquitte
  uint8_t adresse;         // 7 bits
  bool lecture;
  uint8_t n;               // octets de donnees memorises (adresse exclue)
  FinI2C fin;
  uint8_t d[I2C_MAX_OCTETS];
};

struct MachineI2C {
  bool sda = true, scl = true;   // dernier etat vu (bus au repos : les deux hauts)
  bool en_cours = false;
  bool bit_attente = false;      // bit lu au dernier front montant, pas encore compte
  bool bit_valeur = false;
  uint64_t bit_t = 0;
  uint8_t bits = 0;              // bits recus de l'octet courant (0..8) ; a 8, le suivant est l'ACK
  uint8_t octet = 0;
  uint16_t index = 0;            // octet courant : 0 = adresse
  bool prete = false;            // `sortie` vient d'etre terminee : a lire avant le prochain avance()
  TransactionI2C tr{};
  TransactionI2C sortie{};
};

inline void i2c_debut(MachineI2C& m, uint64_t t) {
  m.tr = TransactionI2C{};
  m.tr.t_debut = t;
  m.tr.nack = -1;
  m.en_cours = true;
  m.bits = 0;
  m.octet = 0;
  m.index = 0;
}

inline void i2c_termine(MachineI2C& m, FinI2C fin) {
  m.en_cours = false;
  if (m.index == 0 && m.bits == 0) return;     // START sans aucun bit : parasite, rien a signaler
  m.tr.fin = (m.bits != 0) ? FIN_TRONQUE : fin; // arret au milieu d'un octet (ou avant son ACK)
  m.sortie = m.tr;
  m.prete = true;
}

inline void i2c_bit(MachineI2C& m, bool b, uint64_t t) {
  TransactionI2C& tr = m.tr;
  if (tr.fronts == 0) tr.t_premier = t;
  tr.t_dernier = t;
  tr.fronts++;
  if (m.bits < 8) {
    m.octet = (uint8_t)((m.octet << 1) | (b ? 1 : 0));
    if (++m.bits == 8) {
      if (m.index == 0) {
        tr.adresse = m.octet >> 1;
        tr.lecture = (m.octet & 1) != 0;
      } else if (tr.n < I2C_MAX_OCTETS) {
        tr.d[tr.n++] = m.octet;
      } else {
        tr.trop++;
      }
    }
    return;
  }
  // 9e bit : ACK si SDA basse
  if (b && tr.nack < 0 && (m.index == 0 || !tr.lecture)) tr.nack = (int8_t)(m.index > 127 ? 127 : m.index);
  m.index++;
  m.bits = 0;
  m.octet = 0;
}

inline void avance(MachineI2C& m, bool sda, bool scl, uint64_t t) {
  m.prete = false;
  if (scl && !m.scl) {                 // front montant de SCL : SDA porte la donnee (en attente)
    m.scl = true;
    m.sda = sda;
    m.bit_attente = m.en_cours;
    m.bit_valeur = sda;
    m.bit_t = t;
    return;
  }
  if (!scl) {                          // SCL bas : le bit en attente est confirme, SDA change librement
    if (m.scl && m.bit_attente) {
      m.bit_attente = false;
      i2c_bit(m, m.bit_valeur, m.bit_t);
    }
    m.scl = false;
    m.sda = sda;
    return;
  }
  if (sda == m.sda) return;            // SCL haut, rien ne bouge
  m.sda = sda;
  m.bit_attente = false;               // START/STOP : le front montant n'etait pas une donnee
  if (!sda) {                          // START ou RESTART (i2c_debut ne touche ni sortie ni prete)
    if (m.en_cours) i2c_termine(m, FIN_RESTART);
    i2c_debut(m, t);
  } else if (m.en_cours) {             // STOP
    i2c_termine(m, FIN_STOP);
  }
}
