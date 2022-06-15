#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from kubernetes import client, config
from time import sleep, time
from math import sqrt
from os import environ
from threading import Lock
import re
import os
import dns.resolver

from kollaps.Kollapslib.utils import print_and_fail, ip2int,ip2intbig

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List, Tuple


class NetGraph:
    def __init__(self):
        # Note to future developers self.services can probably be completely replaced with self.hosts_by_ip
        self.services = {}  # type: Dict[str,List[NetGraph.Service]]
        self.hosts_by_ip = {} # type: Dict[int, NetGraph.Service]
        self.bridges = {}  # type: Dict[str,List[NetGraph.Service]]
        self.links = []  # type: List[NetGraph.Link]
        self.links_by_index = {} # type: Dict[int, NetGraph.Link]
        self.link_counter = 0  # increment counter that will give each link an index
        self.path_counter = 0  # increment counter that will give each path an id
        self.removed_links = [] #LL; type: List[NetGraph.Link]
        self.removed_bridges = {} #LL; type: Dict[str,List[NetGraph.Service]]; list has length at most 1
        self.hosts_by_bigip = {}

        self.networks = []  # type: List[str]
        self.supervisors = []  # type: List[NetGraph.Service]

        self.root = None  # type: NetGraph.Service
        self.paths = {}  # type: Dict[NetGraph.Node,NetGraph.Path]
        self.paths_by_id = {} # type: Dict[int, NetGraph.Path]

        self.bandwidth_re = re.compile("([0-9]+)([KMG])bps")
        self.bootstrapper = ""  # type: str
        self.age = 0

    class Node(object):
        def __init__(self, name, shared):
            self.name = name
            self.network = ""  # maybe in the future support multiple networks?
            self.links = []
            self.shared_link = shared

        def attach_link(self, link):
            self.links.append(link)
            self.network = link.network

    class Service(Node):
        def __init__(self, name, image, command, shared, reuse, count):
            super(NetGraph.Service, self).__init__(name, shared)
            self.image = image
            self.command = command
            self.ip = 167772161  # to be filled in later (this is just a value that can safely be converted to an IP)
            self.machinename = ""
            self.replica_id = 0 # to be filled in later (after we sort by ip)
            self.replica_count = count
            self.last_bytes = 0  # number of bytes sent to this service
            self.supervisor = False
            self.supervisor_port = 0
            self.reuse_ip = reuse
            self.time_passed = 0
            self.count = 0
            self.controllername = ""
            self.topology_file = ""
            self.kollaps_folder = ""

    class Bridge(Node):
        def __init__(self, name):
            super(NetGraph.Bridge, self).__init__(name, False)


    class Link:
        # Links are unidirectional
        def __init__(self, source, destination, latency, jitter, drop, bandwidth, bps, network):
            self.lock = Lock()
            self.index = 0
            self.source = source  # type: NetGraph.Node
            self.destination = destination  # type: NetGraph.Node
            try:
                self.latency = float(latency)
                self.drop = float(drop)
                self.jitter = float(jitter)
            except:
                print_and_fail("Provided link data is not valid: "
                    + latency + "ms "
                    + drop + "drop rate "
                    + bandwidth)
            self.bandwidth = bandwidth  # type: str
            self.bandwidth_bps = bps  # type: int
            self.flows = []  # type: List[Tuple[int, int]]  # (RTT, Bandwidth)
            self.last_flows_count = 0
            self.network = network

    class Path(object):
        def __init__(self, links, id, used_bandwidth=1):
            self.links = links  # type: List[NetGraph.Link]
            self.id = id
            self.lock = Lock()
            self.latency = 0
            self.RTT = 0
            self.drop = 0.0
            self.max_bandwidth = None
            self.jitter = 0
            self.used_bandwidth = used_bandwidth

            self.calculate_end_to_end_properties()
            self.current_bandwidth = self.max_bandwidth

        def calculate_end_to_end_properties(self):
            total_not_drop_probability = 1.0
            self.max_bandwidth = None
            self.latency = 0
            self.jitter = 0
            for link in self.links:
                try:
                    # Pick the smallest bandwidth
                    if self.max_bandwidth is None:
                        self.max_bandwidth = link.bandwidth_bps
                    if link.bandwidth_bps < self.max_bandwidth:
                        self.max_bandwidth = link.bandwidth_bps
                    # Accumulate jitter by summing the variances
                    self.jitter = sqrt( (self.jitter*self.jitter)+(link.jitter*link.jitter))
                    # Latency is just a sum
                    self.latency += float(link.latency)
                    # Drop is product of reverse probabilities reversed
                    # basically calculate the probability of not dropping across the entire path
                    # and then invert it
                    # Problem is similar to probability of getting at least one 6 in multiple dice rolls
                    total_not_drop_probability *= (1.0-float(link.drop))
                except:
                    print_and_fail("Provided link data is not valid: "
                        + str(link.latency) + "ms "
                        + str(link.drop) + "drop rate "
                        + link.bandwidth)
            self.RTT = self.latency*2
            self.drop = (1.0-total_not_drop_probability)

        def prettyprint(self):
            if len(self.links) > 0 and isinstance(self.links[-1].destination, NetGraph.Service):
                pretty = "I am a path and these are my links:\n"
                for link in self.links:
                    pretty += "  " + link.source.name + "--" + link.destination.name + "\n"
                pretty += "    These are my end-to-end properties: bandwidth=" + '{:,}'.format(self.max_bandwidth).replace(',', '\'') + ", latency = " + str(self.latency) + ", jitter = " + str(self.jitter)  + ", drop = " + str(self.drop) + "\n"
                return pretty
            else:
                return None

    def get_nodes(self, name):
        if name in self.services:
            return self.services[name]
        elif name in self.bridges:
            return self.bridges[name]
        else:
            return []

    def new_service(self, name, image, command, shared, reuse, count):
        service = NetGraph.Service(name, image, command, shared, reuse, count)
        if len(self.get_nodes(name)) == 0:
            self.services[name] = [service]
        else:
            self.get_nodes(name).append(service)
        return service

    def set_supervisor(self, service):
        service.supervisor = True
        service.network = self.networks[0]

    def new_bridge(self, name):
        bridge = NetGraph.Bridge(name)
        if len(self.get_nodes(name)) == 0:
            self.bridges[name] = [bridge]
        else:
            print_and_fail("Cant add bridge with name: " + name + ". Another node with the same name already exists")
        return bridge

    def new_link(self, source, destination, latency, jitter, drop, bandwidth, network):
        if network not in self.networks:
            self.networks.append(network)
        source_nodes = self.get_nodes(source)
        destination_nodes = self.get_nodes(destination)
        for node in source_nodes:
            for dest in destination_nodes:
                bandwidth_bps = self.bandwidth_in_bps(bandwidth)
                link = NetGraph.Link(node, dest, latency, jitter, drop, bandwidth, bandwidth_bps, network)
                link.index = self.link_counter
                self.link_counter += 1
                self.links.append(link)
                node.attach_link(link)
                self.links_by_index[link.index] = link

    def bandwidth_in_bps(self, bandwidth_string):
        if re.match(self.bandwidth_re, bandwidth_string) is None:
            print_and_fail("Bandwidth is not properly specified, accepted values must be: [1-9]+[KMG]bps")
        results = re.findall(self.bandwidth_re, bandwidth_string)
        base = results[0][0]
        if int(base) == 0:
            print_and_fail("Bandwidth is not properly specified, accepted values must be: [1-9]+[KMG]bps")
        multiplier = results[0][1]
        if multiplier == 'K':
            return int(base)*1000
        if multiplier == 'M':
            return int(base) * 1000 * 1000
        if multiplier == 'G':
            return int(base) * 1000 * 1000 * 1000

    def resolve_hostnames(self):

        orchestrator = os.getenv('KOLLAPS_ORCHESTRATOR', 'swarm')
        if orchestrator == 'kubernetes':
            # kubernetes version
            # we are only talking to the kubernetes API

            experimentUUID = environ.get('KOLLAPS_UUID', '')
            config.load_incluster_config()
            kubeAPIInstance = client.CoreV1Api()
            need_pods = kubeAPIInstance.list_namespaced_pod('default')
            for service in self.services:
                hosts = self.services[service]
                answers = []
                ips = []
                while len(ips) != len(hosts):
                    answers = []
                    need_pods = kubeAPIInstance.list_namespaced_pod('default')
                    try:
                        for pod in need_pods.items:  # loop through pods - much less elegant than using a DNS service
                            if pod.metadata.name.startswith(service + "-" + experimentUUID):
                                if pod.status.pod_ip is not None:  # LL
                                    answers.append(pod.status.pod_ip)
                        ips = [str(ip) for ip in answers]
                    except:
                        sleep(3)
                ips.sort()  # needed for deterministic behaviour
                for i in range(len(hosts)):
                    int_ip = ip2int(ips[i])
                    hosts[i].ip = int_ip
                    hosts[i].replica_id = i
                    self.hosts_by_ip[int_ip] = hosts[i]

        else:
            if orchestrator != 'swarm':
                print("Unrecognized orchestrator. Using default docker swarm.")

            # python's built in address resolver looks in /etc/hosts first
            # this is a problem since services with multiple replicas (same hostname)
            # will only have ONE entry in /etc/hosts, so the other hosts will never be found...
            # Solution: forcefully use dns queries that skip /etc/hosts (this pulls the dnspython dependency...)

            # Moreover, in some scenarios the /etc/resolv.conf is broken inside the containers
            # So to get the names to resolve properly we need to force to use dockers internal nameserver
            # 127.0.0.11

            experimentUUID = environ.get('KOLLAPS_UUID', '')
            docker_resolver = dns.resolver.Resolver(configure=False)
            docker_resolver.nameservers = ['127.0.0.11']
            for service in self.services:
                hosts = self.services[service]
                ips = []
                while len(ips) != len(hosts):
                    try:
                        answers = docker_resolver.query(service + "-" + experimentUUID, 'A')
                        ips = [str(ip) for ip in answers]
                        if len(ips) != len(hosts):
                            sleep(3)
                    except:
                        sleep(3)
                        
                ips.sort()  # needed for deterministic behaviour
                for i in range(len(hosts)):
                    int_ip = ip2int(ips[i])
                    big_int_ip = ip2intbig(ips[i])
                    hosts[i].ip = int_ip
                    hosts[i].replica_id = i
                    self.hosts_by_ip[int_ip] = hosts[i]
                    self.hosts_by_bigip[big_int_ip] = hosts[i]

    def put_ips(self):
        ips = []
        for service in self.services:
            hosts = self.services[service]

            for i in range(len(hosts)):
                int_ip = ip2int(hosts[i].ip)
                big_int_ip = ip2intbig(hosts[i].ip)
                hosts[i].ip = int_ip
                hosts[i].replica_id = i
                self.hosts_by_ip[int_ip] = hosts[i]
                self.hosts_by_bigip[big_int_ip] = hosts[i]


    def calculate_shortest_paths(self):
#        start = time()
        # Dijkstra's shortest path implementation
        # Distance is number of hops
        if self.root is None:
            print_and_fail("Root of the tree has not been defined.")

        inf = float("inf")
        dist = {}
        Q = []
        for service in self.services:
            hosts = self.services[service]
            for host in hosts:
                distance = 0
                if host != self.root:
                    distance = inf
                entry = [distance, host]
                Q.append(entry)
                dist[host] = distance
        for bridge in self.bridges:
            b = self.bridges[bridge][0]
            Q.append([inf, b])
            dist[b] = inf

        self.paths[self.root] = NetGraph.Path([], self.path_counter)
        self.paths_by_id[self.path_counter] = self.paths[self.root]
        self.path_counter += 1
        while len(Q) > 0:
            Q.sort(key=lambda ls: ls[0])
            u = Q.pop(0)[1]  # type: NetGraph.Node
            for link in u.links:
                alt = dist[u] + 1
                if link.destination in dist: # if destination is a bridge, it could have been removed
                    if alt < dist[link.destination]:
                        node = link.destination
                        dist[node] = alt
                        # append to the previous path
                        path = self.paths[u].links[:]
                        path.append(link)
                        self.paths[node] = NetGraph.Path(path, self.path_counter)
                        self.paths_by_id[self.path_counter] = self.paths[node]
                        self.path_counter += 1
                        for e in Q:  # find the node in Q and change its priority
                            if e[1] == node:
                                e[0] = alt
#        end = time()
#        print("shortest paths found in " + str(end - start))

    def print_paths(self):
        nice = ""
        for node, path in self.paths.items():
            nice += "To node " + node.name
            if isinstance(node, NetGraph.Service):
                nice += "_" + str(node.replica_id)
            nice += "\n"
            nice += path.prettyprint()
        return "---------------------\nPaths from node " + str(self.root.name) + "_" + str(self.root.replica_id) + ":\n" + "---------------------\n" + nice + "---------------------"

"""
    def print_links(self):
        nice = "I am a graph and these are my links:\n"
        for link in self.links:
            nice += "Link index " + str(link.index) + ": " + link.source.name + "--" + link.destination.name + "\n"
        print(nice, file=sys.stdout)
"""
