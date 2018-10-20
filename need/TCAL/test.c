//
// Created by joao on 10/5/18.
//
#include "TCAL.h"
#include <arpa/inet.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>
#include <dlfcn.h>

#include <stdarg.h>

void callback(unsigned int ip, unsigned long bytes){
	printf("%d %d\n", ip, bytes);
}


int main(int argc, char** argv){
    struct in_addr addr;
    unsigned int ip;
    inet_aton(argv[1], &addr);
    ip = htonl(addr.s_addr);
    printf("%s\n", argv[1]);
    printf("%ud\n", ip);
  
    
    void (*init)(short);
    void (*initDestination)(unsigned int, int, int, float, float);
    void (*changeBandwidth)(unsigned int, int);
    void (*updateUsage)();
    void (*registerUsageCallback)(void(*callback)(unsigned int, unsigned long));
    void (*tearDown)(int);

    void* handle;
    handle = dlopen("libTCAL.so", RTLD_LAZY);
    if (!handle) {
	fprintf(stderr, "%s\n", dlerror());
        exit(-1);
    }

    dlerror();    /* Clear any existing error */

    *(void **) (&init)  = dlsym(handle, "init");
    *(void **) (&initDestination)  = dlsym(handle, "initDestination");
    *(void **) (&changeBandwidth)  = dlsym(handle, "changeBandwidth");
    *(void **) (&updateUsage)  = dlsym(handle, "updateUsage");
    *(void **) (&registerUsageCallback)  = dlsym(handle, "registerUsageCallback");
    *(void **) (&tearDown)  = dlsym(handle, "tearDown");

    init(55);
    registerUsageCallback(&callback);
    int original_ip = ip;
    for(int i=0; i<5; i++){
	ip++;
    	initDestination(ip, 100000, 10, 0.0f, 0.0f);
    	changeBandwidth(ip, 200000);
    }
    int n = 0;
    while(1){
    	updateUsage();
	sleep(1);
	n++;
    if(n >= 5)
	    break;
    }
    tearDown(0);
    return 0;
}
