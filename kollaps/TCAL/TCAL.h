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
#ifndef TCAL_H
#define TCAL_H

typedef struct netif{
    unsigned int if_index;
    struct netif* next;
}netif;


void init(unsigned short controllPort, int txqueuelen);

void initDestination(unsigned int ip, int bandwidth, float latency, float jitter, float packetLoss);
void changeBandwidth(unsigned int ip, int bandwidth);
void changeLoss(unsigned int ip, float packetLoss);
void changeLatency(unsigned int ip, float latency, float jitter);
void updateUsage();
unsigned long queryUsage(unsigned int ip);
void registerUsageCallback(void(*callback)(unsigned int, unsigned long, unsigned int));

void disconnect();
void reconnect();

void tearDown(int disableNetwork);

#endif