//
// Created by joao on 1/21/18.
//

#ifndef TC_H
#define TC_H


#include <unordered_map>

extern "C" {
#include "Destination.h"
};

#define TXQUEUELEN 1000

#define TC_BIN "tc"
#define FIRST_HASH_MASK "0x0000ff00"
#define SECOND_HASH_MASK "0x000000ff"


#define TC_H_MIN_MASK (0x0000FFFFU)
#define TC_H_MIN(h) ((h)&TC_H_MIN_MASK)
#define TC_H_MAJ_MASK (0xFFFF0000U)
#define TC_H_MAJ(h) ((h)&TC_H_MAJ_MASK)

namespace TC {
    int callTC(std::string args);

    void init(const std::string &interface, short controllPort);

    void initDestination(Destination *dest, std::string interface);

    void changeBandwidth(Destination *dest, std::string interface);

    void updateUsage(std::string interface);
    unsigned long queryUsage(Destination *dest, std::string interface);

    void destroy(std::string interface);
}

#endif //TC_H
