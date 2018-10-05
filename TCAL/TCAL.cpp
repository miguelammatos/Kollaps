#include <stdlib.h>


#include <iostream>
#include <list>
#include <chrono>
#include <thread>
#include <cstring>

extern "C" {
#include "Destination.h"
#include "uthash/uthash.h"
};
#include "TC.h"



Destination* hosts = NULL;
unsigned int handleCounter = 5;

//To be fully correct we should check on what interface a given IP is reachable
//However the mechanisms to do so on Linux are poorly documented
//So instead we just use an environment variable to decide what interface to use...
std::string interface;


extern "C" void init(short controllPort){
    char* env = std::getenv("NETWORK_INTERFACE");
    if(nullptr == env){
        std::cout << "NETWORK_INTERFACE environment variable not set! Aborting." << std::endl;
        exit(-1);
    }
    interface = std::string(env);
    std::cout << "Using interface: " << interface << std::endl;
    TC::init(interface, controllPort);
}

extern "C" void initDestination(unsigned int ip, int bandwidth, int latency, float jitter, float packetLoss){
    Destination* dest = destination_create(ip, bandwidth, latency, jitter, packetLoss);
    dest->handle = ++handleCounter;
    HASH_ADD_INT(hosts, ipv4, dest);

    //Initialize the tc data structures
    TC::initDestination(dest, interface);

}
extern "C" void changeBandwidth(unsigned int ip, int bandwidth){
    Destination* dest;
    HASH_FIND_INT(hosts, &ip, dest);
    dest->bandwidth = bandwidth;
    TC::changeBandwidth(dest, interface);
}

extern "C" void updateUsage(){
    TC::updateUsage(interface);
}

extern "C" unsigned long queryUsage(unsigned int ip){
    Destination* dest;
    HASH_FIND_INT(hosts, &ip, dest);
    return TC::queryUsage(dest, interface);
}

extern "C" void tearDown(){
    Destination *d, *tmp;
    HASH_ITER(hh, hosts, d, tmp){
        HASH_DEL(hosts, d);
        free(d);
    }

    TC::destroy(interface);
}
