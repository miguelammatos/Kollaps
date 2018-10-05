//
// Created by joao on 1/21/18.
//

#ifndef UNTITLED_DESTINATION_H
#define UNTITLED_DESTINATION_H

typedef struct {
    unsigned int ipv4;
    int latency;
    float jitter;
    int bandwidth; //in Kbps
    float packetLossRate;
    unsigned int handle;
}Destination;

Destination* destination_create(unsigned int ipv4, int bandwidth, int latency, float jitter, float packetLossRate);
void destination_getOctetHex(Destination* self, short octet, char* hexOctet);
void destination_getIpHex(Destination* self, char* hexIp);


#endif //UNTITLED_DESTINATION_H
