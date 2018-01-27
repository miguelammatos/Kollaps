from utils import fail
from socket import gethostbyname_ex
from time import sleep
import re

class NetGraph:
    def __init__(self):
        self.services = {}
        self.bridges = {}
        self.links = []

        self.root = None  # type: NetGraph.Service
        self.paths = {}  # Shortest path to each possible destination

        self.reference_bandwidth = 0  # Maximum bandwidth on the topology, used for calculating link cost
        self.bandwidth_re = re.compile("([0-9]+)([KMG])bps")

    def get_nodes(self, name):
        if name in self.services:
            return self.services[name]
        elif name in self.bridges:
            return self.bridges[name]
        else:
            return None

    def new_service(self, name, image):
        service = NetGraph.Service(name, image)
        if self.get_nodes(name) is None:
            self.services[name] = [service]
        else:
            self.get_nodes(name).append(service)

    def new_bridge(self, name):
        bridge = NetGraph.Bridge(name)
        if self.get_nodes(name) is None:
            self.bridges[name] = [bridge]
        else:
            fail("Cant add bridge with name: " + name + ". Another node with the same name already exists")

    def new_link(self, source, destination, latency, drop, bandwidth, network):
        source_nodes = self.get_nodes(source)
        for node in source_nodes:
            bandwidth_kbps = self.bandwidth_in_kbps(bandwidth)
            if self.reference_bandwidth < bandwidth_kbps:
                self.reference_bandwidth = bandwidth_kbps
            link = NetGraph.Link(source, destination, latency, drop, bandwidth, bandwidth_kbps, network)
            self.links.append(link)
            node.attach_link(link)

    def bandwidth_in_kbps(self, bandwidth_string):
        if re.match(self.bandwidth_re, bandwidth_string) is None:
            fail("Bandwidth is not properly specified, accepted values must be: [0-9]+[KMG]bps")
        results = re.findall(self.bandwidth_re, bandwidth_string)
        base = results[0][0]
        multiplier = results[0][1]
        if multiplier == 'K':
            return base
        if multiplier == 'M':
            return base * 1000
        if multiplier == 'G':
            return base * 1000 * 1000

    def resolve_hostnames(self):
        for service in self.services:
            hosts = self.services[service]
            info = gethostbyname_ex(service)
            while len(info[2]) != len(hosts):
                sleep(3)
                info = gethostbyname_ex(service)
            for i in range(len(hosts)):
                hosts[i].ip = info[2][i]



    class Node:
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
        #Links are unidirectional
        def __init__(self, source, destination, latency, drop, bandwidth, Kbps, network):
            self.source = source
            self.destination = destination
            self.latency = latency
            self.drop = drop
            self.bandwidth = bandwidth
            self.bandwidth_Kbps = Kbps
            self.network = network