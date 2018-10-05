#ifndef TCAL_H
#define TCAL_H

extern "C" void init(short controllPort);

extern "C" void initDestination(unsigned int ip, int bandwidth, int latency, float jitter, float packetLoss);
extern "C" void changeBandwidth(unsigned int ip, int bandwidth);
extern "C" void updateUsage();
extern "C" unsigned long queryUsage(unsigned int ip);

extern "C" void tearDown();

#endif