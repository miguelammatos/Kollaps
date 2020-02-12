//
// Created by joao on 10/12/18.
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
#ifndef TCAL_TCAL_UTILS_H
#define TCAL_TCAL_UTILS_H



#define MAX_DIST	(16*1024)
#define NORMAL_SIZE  (4*1024)
#define NEXT_IS_NUMBER() (NEXT_ARG_OK() && isdigit(argv[1][0]))
static int get_ticks(__u32 *ticks, const char *str);
int netem_parse_costum_opt(struct qdisc_util *qu, int argc, char **argv, struct nlmsghdr *n, const char *dev);
void fillNormalDist();

int set_txqueuelen(const char* ifname, int num_packets);
int set_if_flags(const char *ifname, short flags);
int set_if_up(const char *ifname, short flags);
int set_if_down(const char *ifname, short flags);

struct qdisc_util *get_qdisc_kind(const char *str);
struct filter_util *get_filter_kind(const char *str);

void open_rtnl(struct rtnl_handle* h);
void close_rtnl(struct rtnl_handle* h);

int get_route_interface(unsigned int ip);
#endif //TCAL_TCAL_UTILS_H
