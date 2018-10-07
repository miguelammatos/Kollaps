#include <stdlib.h>
#include <stdio.h>
#include "Destination.h"
#include "uthash/uthash.h"

#include "TC.h"



Destination* hosts = NULL;
Destination* hostsByHandle = NULL;
unsigned int handleCounter = 5;

//To be fully correct we should check on what interface a given IP is reachable
//However the mechanisms to do so on Linux are poorly documented
//So instead we just use an environment variable to decide what interface to use...
char* interface;


void init(short controllPort){
    char* env = getenv("NETWORK_INTERFACE");
    if(NULL == env){
        printf("NETWORK_INTERFACE environment variable not set! Aborting.\n");
        exit(-1);
    }
    interface = env;
    printf("Using interface: %s\n", interface);
    TC_init(interface, controllPort);
}

void initDestination(unsigned int ip, int bandwidth, int latency, float jitter, float packetLoss){
    Destination* dest = destination_create(ip, bandwidth, latency, jitter, packetLoss);
    dest->handle = ++handleCounter;
    HASH_ADD(hh_ip, hosts, ipv4, sizeof(int), dest);
    HASH_ADD(hh_h, hostsByHandle, handle, sizeof(int), dest);

    //Initialize the tc data structures
    TC_initDestination(dest, interface);

}
void changeBandwidth(unsigned int ip, int bandwidth){
    Destination* dest;
    HASH_FIND(hh_ip, hosts, &ip, sizeof(int), dest);
    dest->bandwidth = bandwidth;
    TC_changeBandwidth(dest, interface);
}

void updateUsage(){
    TC_updateUsage(interface);
}

unsigned long queryUsage(unsigned int ip){
    Destination* dest;
    HASH_FIND(hh_ip, hosts, &ip, sizeof(int), dest);
    return dest->usage;
}

void tearDown(){
    Destination *d, *tmp;
    HASH_ITER(hh_ip, hosts, d, tmp){
        HASH_DELETE(hh_ip, hosts, d);
        HASH_DELETE(hh_h, hostsByHandle, d);
        free(d);
    }

    TC_destroy(interface);
}
