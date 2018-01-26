
class NetGraph:
    def __init__(self):
        self.services = {} #  TODO: Need to support replication
        self.bridges = {}
        self.links = []

    def get_node(self, name):
        if name in self.services:
            return self.services[name]
        elif name in self.bridges:
            return self.bridges[name]
        else:
            return None

    def new_service(self, name, image):
        service = NetGraph.Service(name, image)
        self.services[name] = service

    def new_bridge(self, name):
        bridge = NetGraph.Bridge(name)
        self.bridges[name] = bridge

    def new_link(self, source, destination, latency, drop, bandwidth, network):
        link = NetGraph.Link(source, destination, latency, drop, bandwidth, network)
        self.links.append(link);
        sourceNode = self.get_node(source)
        sourceNode.attach_link(link)


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