from NEED.utils import fail, ip2int
from time import sleep
from math import sqrt
from os import environ
import re

import dns.resolver

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List, Tuple


class NetGraph:
    def __init__(self):
        self.services = {}  # type: Dict[str,List[NetGraph.Service]]
        self.bridges = {}  # type: Dict[str,List[NetGraph.Service]]
        self.links = []  # type: List[NetGraph.Link]
        self.link_counter = 0  # increment counter that will give each link an index
        self.path_counter = 0  # increment counter that will give each path an id

        self.networks = []  # type: List[str]
        self.supervisors = []  # type: List[NetGraph.Service]

        self.root = None  # type: NetGraph.Service
        self.paths = {}  # type: Dict[NetGraph.Node,NetGraph.Path]
        self.paths_by_id = {} # type: Dict[int, NetGraph.Path]

        self.reference_bandwidth = 0  # Maximum bandwidth on the topology, used for calculating link cost
        self.bandwidth_re = re.compile("([0-9]+)([KMG])bps")

    class Node(object):
        def __init__(self, name, shared):
            self.name = name
            self.network = ""  # maybe in the future support multiple networks? (TCAL doesnt allow that for now)
            self.links = []
            self.shared_link = shared

        def attach_link(self, link):
            self.links.append(link)
            self.network = link.network

    class Service(Node):
        def __init__(self, name, image, command, shared):
            super(NetGraph.Service, self).__init__(name, shared)
            self.image = image
            self.command = command
            self.ip = ""  # to be filled in later
            self.last_bytes = 0  # number of bytes sent to this service
            self.supervisor = False
            self.supervisor_port = 0

    class Bridge(Node):
        def __init__(self, name):
            super(NetGraph.Bridge, self).__init__(name, False)


    class Link:
        # Links are unidirectional
        def __init__(self, source, destination, latency, jitter, drop, bandwidth, bps, network):
            self.index = 0
            self.source = source  # type: NetGraph.Node
            self.destination = destination  # type: NetGraph.Node
            try:
                self.latency = int(latency)
                self.drop = float(drop)
                self.jitter = float(jitter)
            except:
                fail("Provided link data is not valid: "
                     + latency + "ms "
                     + drop + "drop rate "
                     + bandwidth)
            self.bandwidth = bandwidth  # type: str
            self.bandwidth_bps = bps  # type: int
            self.flows = []  # type: List[Tuple[int, int]]  # (RTT, Bandwidth)
            self.last_flows_count = 0
            self.network = network

    class Path(object):
        def __init__(self, links, id, used_bandwidth=0):
            self.links = links  # type: List[NetGraph.Link]
            self.id = id
            total_latency = 0
            total_not_drop_probability = 1.0
            max_bandwidth = None
            jitter = 0
            for link in self.links:
                try:
                    if max_bandwidth is None:
                        max_bandwidth = link.bandwidth_bps
                    if link.bandwidth_bps < max_bandwidth:
                        max_bandwidth = link.bandwidth_bps
                    # Accumulate jitter by summing the variances
                    jitter = sqrt( (jitter*jitter)+(link.jitter*link.jitter))
                    total_latency += int(link.latency)
                    total_not_drop_probability *= (1.0-float(link.drop))
                except:
                    fail("Provided link data is not valid: "
                         + str(link.latency) + "ms "
                         + str(link.drop) + "drop rate "
                         + link.bandwidth)
            self.max_bandwidth = max_bandwidth  # in bps
            self.current_bandwidth = max_bandwidth
            self.latency = total_latency
            self.jitter = jitter
            self.RTT = self.latency*2
            # Product of reverse probabilities reversed
            # basically calculate the probability of not dropping across the entire path
            # and then invert it
            # Problem is similar to probability of getting at least one 6 in multiple dice rolls
            self.drop = (1.0-total_not_drop_probability)
            self.used_bandwidth = used_bandwidth

    def get_nodes(self, name):
        if name in self.services:
            return self.services[name]
        elif name in self.bridges:
            return self.bridges[name]
        else:
            return []

    def new_service(self, name, image, command, shared):
        service = NetGraph.Service(name, image, command, shared)
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
            fail("Cant add bridge with name: " + name + ". Another node with the same name already exists")
        return bridge

    def new_link(self, source, destination, latency, jitter, drop, bandwidth, network):
        if network not in self.networks:
            self.networks.append(network)
        source_nodes = self.get_nodes(source)
        destination_nodes = self.get_nodes(destination)
        for node in source_nodes:
            for dest in destination_nodes:
                bandwidth_bps = self.bandwidth_in_bps(bandwidth)
                if self.reference_bandwidth < bandwidth_bps:
                    self.reference_bandwidth = bandwidth_bps
                link = NetGraph.Link(node, dest, latency, jitter, drop, bandwidth, bandwidth_bps, network)
                link.index = self.link_counter
                self.link_counter += 1
                self.links.append(link)
                node.attach_link(link)

    def bandwidth_in_bps(self, bandwidth_string):
        if re.match(self.bandwidth_re, bandwidth_string) is None:
            fail("Bandwidth is not properly specified, accepted values must be: [0-9]+[KMG]bps")
        results = re.findall(self.bandwidth_re, bandwidth_string)
        base = results[0][0]
        multiplier = results[0][1]
        if multiplier == 'K':
            return int(base)*1000
        if multiplier == 'M':
            return int(base) * 1000 * 1000
        if multiplier == 'G':
            return int(base) * 1000 * 1000 * 1000

    def resolve_hostnames(self):
        # python's built in address resolver looks in /etc/hosts first
        # this is a problem since services with multiple replicas (same hostname)
        # will only have ONE entry in /etc/hosts, so the other hosts will never be found...
        # Solution: forcefully use dns queries that skip /etc/hosts (this pulls the dnspython dependency...)

        # Moreover, in some scenarios the /etc/resolv.conf is broken inside the containers
        # So to get the names to resolve properly we need to force to use dockers internal nameserver
        # 127.0.0.11

        experimentUUID = environ.get('NEED_UUID', '')
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
                hosts[i].ip = ip2int(ips[i])

    def calculate_shortest_paths(self):
        # Dijkstra's shortest path implementation
        if self.root is None:
            fail("Root of the tree has not been defined.")

        dist = {}
        Q = []
        for service in self.services:
            hosts = self.services[service]
            for host in hosts:
                distance = 0
                if host != self.root:
                    distance = self.reference_bandwidth
                entry = [distance, host]
                Q.append(entry)
                dist[host] = distance
        for bridge in self.bridges:
            b = self.bridges[bridge][0]
            Q.append([self.reference_bandwidth, b])
            dist[b] = self.reference_bandwidth

        self.paths[self.root] = NetGraph.Path([], self.path_counter)
        self.paths_by_id[self.path_counter] = self.paths[self.root]
        self.path_counter += 1
        while len(Q) > 0:
            Q.sort(key=lambda ls: ls[0])
            u = Q.pop(0)[1]  # type: NetGraph.Node
            for link in u.links:
                alt = dist[u] + (self.reference_bandwidth/link.bandwidth_bps)
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

