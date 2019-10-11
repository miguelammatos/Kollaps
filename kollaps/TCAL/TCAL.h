#ifndef TCAL_H
#define TCAL_H

typedef struct netif{
    unsigned int if_index;
    struct netif* next;
}netif;


void init(unsigned short controllPort, int txqueuelen);

void initDestination(unsigned int ip, int bandwidth, float latency, float jitter, float packetLoss);
void changeBandwidth(unsigned int ip, int bandwidth);
void changeLoss(unsigned int ip, float packetLoss);
void changeLatency(unsigned int ip, float latency, float jitter);
void updateUsage();
unsigned long queryUsage(unsigned int ip);
void registerUsageCallback(void(*callback)(unsigned int, unsigned long, unsigned int));

void disconnect();
void reconnect();

void tearDown(int disableNetwork);

#endif