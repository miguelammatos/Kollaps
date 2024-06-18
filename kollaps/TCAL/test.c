//
// Created by joao on 10/5/18.
//
/*
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to you under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 * https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
 * implied.  See the License for the specific language governing
 * permissions and limitations under the License.
 */
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

    // char map_path[64];
    // sprintf(map_path, "/sys/fs/bpf/tc/globals/usage%s","123");
    // bpf_obj_get(map_path);
  
    
    void (*init)(short);
    void (*initDestination)(unsigned int, int, int, float, float);
    void (*changeBandwidth)(unsigned int, int);
    void (*changeLoss)(unsigned int, float);
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
    *(void **) (&changeLoss)  = dlsym(handle, "changeLoss");
    *(void **) (&updateUsage)  = dlsym(handle, "updateUsage");
    *(void **) (&registerUsageCallback)  = dlsym(handle, "registerUsageCallback");
    *(void **) (&tearDown)  = dlsym(handle, "tearDown");

    init(55);
    registerUsageCallback(&callback);
    int original_ip = ip;
    for(int i=0; i<5; i++){
	ip++;
    	initDestination(ip, 100000, 10, 1.0f, 0.0f);
	changeLoss(ip, 0.5);
    	changeBandwidth(ip, 200000);
    }
    int n = 0;
    while(1){
    	updateUsage();
	sleep(2);
	n++;
    	if(n >= 15)
	    break;
    }
    tearDown(0);
    return 0;
}
