//
// Created by joao on 1/21/18.
//

#include <stdlib.h>
#include <stdio.h>
#include "Destination.h"

Destination* destination_create(unsigned int ipv4, int bandwidth, int latency,
                         float jitter, float packetLossRate) {

    Destination* self = malloc(sizeof(Destination));
    self->ipv4 = ipv4;
    self->bandwidth = bandwidth;
    self->latency = latency;
    self->jitter = jitter;
    self->packetLossRate = packetLossRate;
    return self;

}

void destination_getOctetHex(Destination* self, short octet, char* hexOctet){
#define SIZEOF_OCTET 3
    char shift = ((octet-1)*8);
    int mask = (0xff000000 >> shift);
    int maskedIp = (self->ipv4) & mask;
    unsigned char octet_decimal = maskedIp >> (24-shift);
    snprintf(hexOctet, SIZEOF_OCTET, "%02x", octet_decimal);
}


void destination_getIpHex(Destination* self, char* hexIp){
#define SIZEOF_IP 9
    snprintf(hexIp, SIZEOF_IP, "%08x", self->ipv4);
}