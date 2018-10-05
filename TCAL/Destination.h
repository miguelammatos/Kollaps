//
// Created by joao on 1/21/18.
//

#ifndef UNTITLED_DESTINATION_H
#define UNTITLED_DESTINATION_H

#include "string"

class Destination {
    unsigned int _ipv4;
    int _latency;
    float _jitter;
    int _bandwidth; //in Kbps
    float _packetLossRate;

    unsigned int _handle;
public:
    Destination(unsigned int ipv4,
                int bandwidth, int latency, float jitter, float packetLossRate);
    std::string getOctetHex(short octet);
    const int getIp();
    std::string getIpHex();
    const int getLatency();
    const float getJitter();
    const int getBandwidth();
    const float getPacketLossRate();
    void setBandwidth(int bandwidth);
    const unsigned int getHandle();

    void setHandle(unsigned int handle);
private:
    unsigned int ipToInt(short octet);
};


#endif //UNTITLED_DESTINATION_H
