from utils import fail


class NetGraph:
    def __init__(self):
        self.services = {}
        self.bridges = {}
        self.links = []

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
            link = NetGraph.Link(source, destination, latency, drop, bandwidth, network)
            self.links.append(link)
            node.attach_link(link)


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

    class Bridge(Node):
        def __init__(self, name):
            super(NetGraph.Bridge, self).__init__(name)

    class Link:
        #Links are unidirectional
        def __init__(self, source, destination, latency, drop, bandwidth, network):
            self.source = source
            self.destination = destination
            self.latency = latency
            self.drop = drop
            self.bandwidth = bandwidth
            self.network = network