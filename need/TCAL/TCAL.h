#ifndef TCAL_H
#define TCAL_H

typedef struct netif{
    unsigned int if_index;
    struct netif* next;
}netif;


void init(short controllPort);

void initDestination(unsigned int ip, int bandwidth, int latency, float jitter, float packetLoss);
void changeBandwidth(unsigned int ip, int bandwidth);
void updateUsage();
unsigned long queryUsage(unsigned int ip);
void registerUsageCallback(void(*callback)(unsigned int, unsigned long));

void tearDown();

#endif