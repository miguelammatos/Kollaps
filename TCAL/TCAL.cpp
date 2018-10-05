#include <stdlib.h>


#include <iostream>
#include <list>
#include <chrono>
#include <thread>
#include <cstring>
#include "unordered_map"

extern "C" {
#include "Destination.h"
};
#include "TC.h"



std::unordered_map<unsigned int, Destination*> hosts;
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
    hosts[ip] = dest;

    //Initialize the tc data structures
    TC::initDestination(dest, interface);

}
extern "C" void changeBandwidth(unsigned int ip, int bandwidth){
    Destination* dest = hosts[ip];
    dest->bandwidth = bandwidth;
    TC::changeBandwidth(dest, interface);
}

extern "C" void updateUsage(){
    TC::updateUsage(interface);
}

extern "C" unsigned long queryUsage(unsigned int ip){
    Destination* dest = hosts[ip];
    return TC::queryUsage(dest, interface);
}

extern "C" void tearDown(){
    for(auto it=hosts.begin(); it!=hosts.end(); it++){
        free(it->second);
    }
    hosts.clear();
    TC::destroy(interface);
}
