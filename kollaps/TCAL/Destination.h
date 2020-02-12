//
// Created by joao on 1/21/18.
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
#ifndef UNTITLED_DESTINATION_H
#define UNTITLED_DESTINATION_H

#include "uthash/uthash.h"


typedef struct {
    unsigned int ipv4;
    float latency;
    float jitter;
    int bandwidth; //in Kbps
    float packetLossRate;
    unsigned int handle;
    unsigned long usage;
    unsigned int if_index; //Index of the interface this destination is reachable on
    unsigned int queuelen;
    UT_hash_handle hh_ip;
    UT_hash_handle hh_h;
}Destination;

Destination* destination_create(unsigned int ipv4, int bandwidth, float latency, float jitter, float packetLossRate);
void destination_getOctetHex(Destination* self, short octet, char* hexOctet);
void destination_getIpHex(Destination* self, char* hexIp);


#endif //UNTITLED_DESTINATION_H
