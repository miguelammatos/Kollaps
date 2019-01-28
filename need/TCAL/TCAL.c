#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "Destination.h"
#include "uthash/uthash.h"
#include "uthash/utlist.h"

#include "TC.h"
#include "TCAL.h"

//TODO now that we controll the environment in NEED we no longer need libutc, so we can go back to calling tc directly


Destination* hosts = NULL;
Destination* hostsByHandle = NULL;
netif* interfaces = NULL;
unsigned short needControllPort = 0;

unsigned int handleCounter = 5;
void (*usageCallback)(unsigned int, unsigned long, unsigned int) = NULL;


void init(unsigned short controllPort, int txqueuelen){
    needControllPort = controllPort;
    TC_init(controllPort, txqueuelen);
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

void changeLoss(unsigned int ip, float packetLoss){
    Destination* dest;
    HASH_FIND(hh_ip, hosts, &ip, sizeof(int), dest);
    dest->packetLossRate = packetLoss;
    TC_changeNetem(dest);
}

void changeLatency(unsigned int ip, int latency, float jitter){
    Destination* dest;
    HASH_FIND(hh_ip, hosts, &ip, sizeof(int), dest);
    dest->latency = latency;
    dest->jitter = jitter;
    TC_changeNetem(dest);
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

void registerUsageCallback(void(*callback)(unsigned int, unsigned long, unsigned int)){
    usageCallback = callback;
}

void disconnect(){
    char rule_max[] = "iptables -w -I OUTPUT -p tcp --dport 65535 -j ACCEPT";
    size_t max_size = strlen(rule_max);
    char* accept_rule = calloc(max_size, sizeof(char));


    system("iptables -w -F");
    system("iptables -w -I INPUT -j DROP");
    snprintf(accept_rule, max_size, "iptables -w -I INPUT -p tcp --dport %hu -j ACCEPT", needControllPort);
    system(accept_rule);
    //TODO For now we also allow metadata to flow out so that the dashboard doesnt report losses
    //TODO @PAULO when/if emucores no longer use network to share metadata this can/should be removed
    snprintf(accept_rule, max_size, "iptables -w -I INPUT -p udp --dport %hu -j ACCEPT", needControllPort);
    system(accept_rule);

    system("iptables -w -I OUTPUT -j DROP");
    snprintf(accept_rule, max_size, "iptables -w -I OUTPUT -p tcp --sport %hu -j ACCEPT", needControllPort);
    system(accept_rule);

    //TODO For now we need to also allow metadata to flow out
    //TODO @PAULO when/if emucores no longer use network to share metadata this can/should be removed
    snprintf(accept_rule, max_size, "iptables -w -I OUTPUT -p udp --dport %hu -j ACCEPT", needControllPort);
    system(accept_rule);

    free(accept_rule);
}

void reconnect(){
    system("iptables -w -F");
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
