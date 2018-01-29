from utils import fail
from socket import gethostbyname_ex
from time import sleep
import re

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List


class NetGraph:
    def __init__(self):
        self.services = {}  # type: Dict[str,List[NetGraph.Service]]
        self.bridges = {}  # type: Dict[str,List[NetGraph.Service]]
        self.links = []  # type: List[NetGraph.Link]

        self.root = None  # type: NetGraph.Service
        self.paths = {}  # type: Dict[NetGraph.Node,List[NetGraph.Link]

        self.reference_bandwidth = 0  # Maximum bandwidth on the topology, used for calculating link cost
        self.bandwidth_re = re.compile("([0-9]+)([KMG])bps")

    class Node(object):
        def __init__(self, name):
            self.name = name
            self.network = ""  # maybe in the future support multiple networks? (TCAL doesnt allow that for now)
            self.links = []

        def attach_link(self, link):
            self.links.append(link)
            self.network = link.network

    class Service(Node):
        def __init__(self, name, image):
            super(NetGraph.Service, self).__init__(name)
            self.image = image
            self.ip = ""  # to be filled in later

    class Bridge(Node):
        def __init__(self, name):
            super(NetGraph.Bridge, self).__init__(name)

    class Link:
        # Links are unidirectional
        def __init__(self, source, destination, latency, drop, bandwidth, Kbps, network):
            self.source = source  # type: NetGraph.Node
            self.destination = destination  # type: NetGraph.Node
            self.latency = latency
            self.drop = drop
            self.bandwidth = bandwidth  # type: str
            self.bandwidth_Kbps = Kbps  # type: int
            self.network = network

    def get_nodes(self, name):
        if name in self.services:
            return self.services[name]
        elif name in self.bridges:
            return self.bridges[name]
        else:
            return []

    def new_service(self, name, image):
        service = NetGraph.Service(name, image)
        if len(self.get_nodes(name)) == 0:
            self.services[name] = [service]
        else:
            self.get_nodes(name).append(service)

    def new_bridge(self, name):
        bridge = NetGraph.Bridge(name)
        if len(self.get_nodes(name)) == 0:
            self.bridges[name] = [bridge]
        else:
            fail("Cant add bridge with name: " + name + ". Another node with the same name already exists")

    def new_link(self, source, destination, latency, drop, bandwidth, network):
        source_nodes = self.get_nodes(source)
        destination_nodes = self.get_nodes(destination)
        for node in source_nodes:
            for dest in destination_nodes:
                bandwidth_kbps = self.bandwidth_in_kbps(bandwidth)
                if self.reference_bandwidth < bandwidth_kbps:
                    self.reference_bandwidth = bandwidth_kbps
                link = NetGraph.Link(node, dest, latency, drop, bandwidth, bandwidth_kbps, network)
                self.links.append(link)
                node.attach_link(link)

    def bandwidth_in_kbps(self, bandwidth_string):
        if re.match(self.bandwidth_re, bandwidth_string) is None:
            fail("Bandwidth is not properly specified, accepted values must be: [0-9]+[KMG]bps")
        results = re.findall(self.bandwidth_re, bandwidth_string)
        base = results[0][0]
        multiplier = results[0][1]
        if multiplier == 'K':
            return int(base)
        if multiplier == 'M':
            return int(base) * 1000
        if multiplier == 'G':
            return int(base) * 1000 * 1000

    def resolve_hostnames(self):
        for service in self.services:
            hosts = self.services[service]
            info = [[], [], []]
            while len(info[2]) != len(hosts):
                try:
                    info = gethostbyname_ex(service)
                    if len(info[2]) != len(hosts):
                        sleep(3)
                except:
                    sleep(3)
            for i in range(len(hosts)):
                hosts[i].ip = info[2][i]

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

        self.paths[self.root] = []
        while len(Q) > 0:
            Q.sort(key=lambda ls: ls[0])
            u = Q.pop(0)[1]  # type: NetGraph.Node
            for link in u.links:
                alt = dist[u] + (self.reference_bandwidth/link.bandwidth_Kbps)
                if alt < dist[link.destination]:
                    node = link.destination
                    dist[node] = alt
                    path = self.paths[u][:]
                    path.append(link)
                    self.paths[node] = path
                    for e in Q:  # find the node in Q and change its priority
                        if e[1] == node:
                            e[0] = alt

    @staticmethod
    def calculate_path_latency(path):
        """
        :param path: List[Link]
        :return: int
        """
        total_latency = 0
        for link in path:
            try:
                total_latency += int(link.latency)
            except:
                fail("Provided latency is not an integer: " + link.latency)
        return total_latency

    @staticmethod
    def calculate_path_drop(path):
        """
        :param path: List[Link]
        :return: float
        """
        # Product of reverse probabilities reversed
        # basically calculate the probability of not dropping across the entire path
        # and then invert it
        # Problem is similar to probability of getting at least one 6 in multiple dice rolls
        total_not_drop_probability = 1.0
        for link in path:
            try:
                total_not_drop_probability *= (1.0-float(link.drop))
            except:
                fail("Provided packet loss probability is not a float: " + link.latency)
        return (1.0-total_not_drop_probability)

    @staticmethod
    def calculate_path_max_initial_bandwidth(path):
        """
        :param path: List[Link]
        :return: int
        """
        max_bandwidth = None
        for link in path:
            if max_bandwidth is None:
                max_bandwidth = link.bandwidth_Kbps
            if link.bandwidth_Kbps < max_bandwidth:
                max_bandwidth = link.bandwidth_Kbps

        return max_bandwidth
