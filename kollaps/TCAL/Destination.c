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
#include <stdlib.h>
#include <stdio.h>
#include "Destination.h"

Destination* destination_create(unsigned int ipv4, int bandwidth, float latency,
                         float jitter, float packetLossRate) {

    Destination* self = malloc(sizeof(Destination));
    self->ipv4 = ipv4;
    self->bandwidth = bandwidth;
    self->latency = latency;
    self->jitter = jitter;
    self->packetLossRate = packetLossRate;
    self->usage = 0;
    self->queuelen = 0;
    return self;

}

void destination_getOctetHex(Destination* self, short octet, char* hexOctet){
#define SIZEOF_OCTET 3
    char shift = ((octet-1)*8);
    int mask = (0xff000000 >> shift);
    int maskedIp = (self->ipv4) & mask;
    unsigned char octet_decimal = maskedIp >> (24-shift);
    snprintf(hexOctet, SIZEOF_OCTET, "%02x", octet_decimal);
}


void destination_getIpHex(Destination* self, char* hexIp){
#define SIZEOF_IP 11
    snprintf(hexIp, SIZEOF_IP, "0x%08x", self->ipv4);
}