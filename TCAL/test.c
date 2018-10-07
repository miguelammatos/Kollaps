//
// Created by joao on 10/5/18.
//
#include "TCAL.h"
#include "Destination.h"

#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>

#include <stdarg.h>

int main(int argc, char** argv){
    struct in_addr addr;
    unsigned int ip;
    inet_aton(argv[1], &addr);
    ip = htonl(addr.s_addr);
    printf("%s\n", argv[1]);
    printf("%ud\n", ip);
    
    Destination* dest = destination_create(ip, 100000, 10, 0.0f, 0.0f);
    char octet1[] = "FF";
    char octet2[] = "FF";
    char octet3[] = "FF";
    char octet4[] = "FF";

    destination_getOctetHex(dest, 1, octet1);
    destination_getOctetHex(dest, 2, octet2);
    destination_getOctetHex(dest, 3, octet3);
    destination_getOctetHex(dest, 4, octet4);

    printf("Octets 0x%s 0x%s 0x%s 0x%s\n", octet1, octet2, octet3, octet4);
    
    char hexIp[] = "ffffffff";
    destination_getIpHex(dest, hexIp);
    printf("0x%s\n", hexIp);
    free(dest);
    
    init(55);
    int original_ip = ip;
    for(int i=0; i<5; i++){
	ip +=i;
    	initDestination(ip, 100000, 10, 0.0f, 0.0f);
    	changeBandwidth(ip, 200000);
    }
    updateUsage();
    ip = original_ip;
    for(int i=0; i<5; i++){
	ip +=i;
	if(queryUsage(ip)){
		printf("FAIL!");
		exit(-1);	
	}
    }
    tearDown();

    char* buffer = NULL;
    int required_size = 0;
    char fmt[] = "Hello %d";
    required_size = snprintf(buffer, 0, fmt, 1);
    required_size += 1; //for null termination
    buffer = (char*)malloc(required_size*sizeof(char));
    required_size = snprintf(buffer, required_size, fmt, 1);

    printf("%s\n", buffer);
    free(buffer);

    return 0;
}
