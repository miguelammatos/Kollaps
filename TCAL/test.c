//
// Created by joao on 10/5/18.
//
#include "TCAL.h"
#include <arpa/inet.h>
#include <stdio.h>

int main(int argc, char** argv){
    struct in_addr addr;
    unsigned int ip;
// store this IP address in sa:
    inet_aton(argv[1], &addr);
    ip = htonl(addr.s_addr);
    printf("%d\n", ip);
    init(55);
    initDestination(ip, 100000, 10, 0.0f, 0.0f);
    return 0;
}