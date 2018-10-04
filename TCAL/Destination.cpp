//
// Created by joao on 1/21/18.
//

#include <sstream>
#include <iomanip>
#include <iostream>
#include "Destination.h"

Destination::Destination(const std::string &ipv4, int bandwidth, int latency,
                         float jitter, float packetLossRate) {
    _ipv4 = ipv4;
    _latency = latency;
    _jitter = jitter;
    _bandwidth = bandwidth;
    _packetLossRate = packetLossRate;
}

void Destination::setBandwidth(int bandwidth) {
    _bandwidth = bandwidth;
}

void Destination::setHandle(unsigned int handle) {
    _handle = handle;
}

const int Destination::getBandwidth() {
    return _bandwidth;
}

const unsigned int Destination::getHandle() {
    return _handle;
}

const std::string& Destination::getIP() {
    return _ipv4;
}

const int Destination::getLatency() {
    return _latency;
}

const float Destination::getJitter() {
    return _jitter;
}

const float Destination::getPacketLossRate() {
    return _packetLossRate;
}

unsigned int Destination::ipToInt(short octet) {
    const unsigned bits_per_term = 8;
    const unsigned num_terms = 4;

    std::istringstream ip(_ipv4);
    for(unsigned int i=1; i<=num_terms; i++){
        unsigned int term;
        ip >> term;
        ip.ignore();
        if(i == octet)
            return term;
    }
    return 255;//Error
}

std::string Destination::getOctetHex(short octet) {
    std::stringstream ss;
    ss << std::hex << std::setfill('0') << std::setw(2)<< ipToInt(octet);
    return ss.str();
}
