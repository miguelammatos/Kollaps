#include <stdlib.h>
#include <stdio.h>
#include "Destination.h"
#include "uthash/uthash.h"
#include "uthash/utlist.h"

#include "TC.h"
#include "TCAL.h"

//TODO now that we controll the environment in NEED we no longer need libutc, so we can go back to calling tc directly


Destination* hosts = NULL;
Destination* hostsByHandle = NULL;
netif* interfaces = NULL;

unsigned int handleCounter = 5;
void (*usageCallback)(unsigned int, unsigned long) = NULL;


void init(short controllPort){
    TC_init(controllPort);
}

void initDestination(unsigned int ip, int bandwidth, int latency, float jitter, float packetLoss){
    Destination* dest = destination_create(ip, bandwidth, latency, jitter, packetLoss);
    dest->handle = ++handleCounter;
    HASH_ADD(hh_ip, hosts, ipv4, sizeof(int), dest);
    HASH_ADD(hh_h, hostsByHandle, handle, sizeof(int), dest);

    //Initialize the tc data structures
    TC_initDestination(dest);
    netif* existing_if = NULL;
    LL_SEARCH_SCALAR(interfaces, existing_if, if_index, dest->if_index);
    if(!existing_if){
        existing_if = (netif*)malloc(sizeof(netif));
        existing_if->if_index = dest->if_index;
        LL_PREPEND(interfaces, existing_if);
    }

}
void changeBandwidth(unsigned int ip, int bandwidth){
    Destination* dest;
    HASH_FIND(hh_ip, hosts, &ip, sizeof(int), dest);
    dest->bandwidth = bandwidth;
    TC_changeBandwidth(dest);
}

void updateUsage(){
    netif* ifelem;
    LL_FOREACH(interfaces, ifelem){
        TC_updateUsage(ifelem->if_index);
    }
}

unsigned long queryUsage(unsigned int ip){
    Destination* dest;
    HASH_FIND(hh_ip, hosts, &ip, sizeof(int), dest);
    return dest->usage;
}

void registerUsageCallback(void(*callback)(unsigned int, unsigned long)){
    usageCallback = callback;
}

void disconnect(){
    system("iptables -F");
    system("iptables -I INPUT -j DROP");
    system("iptables -I OUTPUT -j DROP");
}

void reconnect(){
    system("iptables -F");
}

void tearDown(int disableNetwork){
    Destination *d, *tmp;
    HASH_ITER(hh_ip, hosts, d, tmp){
        HASH_DELETE(hh_ip, hosts, d);
        HASH_DELETE(hh_h, hostsByHandle, d);
        free(d);
    }

    netif *ifelem, *iftmp;
    LL_FOREACH(interfaces, ifelem){
        TC_destroy(ifelem->if_index, disableNetwork);
    }
    LL_FOREACH_SAFE(interfaces,ifelem,iftmp) {
        LL_DELETE(interfaces,ifelem);
        free(ifelem);
    }
}
