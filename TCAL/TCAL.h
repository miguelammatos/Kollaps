#ifndef TCAL_H
#define TCAL_H

#include <string>

void init(short controllPort);

void initDestination(std::string ip, int bandwidth, int latency, float jitter, float packetLoss);
void changeBandwidth(std::string ip, int bandwidth);
void updateUsage();
unsigned long queryUsage(std::string ip);

void tearDown();

#endif