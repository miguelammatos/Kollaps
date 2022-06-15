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
#ifndef TC_H
#define TC_H


#include "Destination.h"
#include "uthash/uthash.h"

//To avoid warnings, declare these here:
struct sockaddr_nl;
struct nlmsghdr;
struct rtattr;
struct qdisc_util;


#define FIRST_HASH_MASK "0x0000ff00"
#define SECOND_HASH_MASK "0x000000ff"


#define TC_H_MIN_MASK (0x0000FFFFU)
#define TC_H_MIN(h) ((h)&TC_H_MIN_MASK)
#define TC_H_MAJ_MASK (0xFFFF0000U)
#define TC_H_MAJ(h) ((h)&TC_H_MAJ_MASK)



void TC_init(unsigned short controllPort, int txqlen,unsigned int myip);
void TC_initDestination(Destination *dest);
void TC_changeBandwidth(Destination *dest);
void TC_changeNetem(Destination *dest);
void TC_updateUsage(unsigned int if_index);

void TC_destroy(unsigned int if_index, int disableNetwork);

#endif //TC_H
