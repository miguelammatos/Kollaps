#! /usr/bin/python
from NetGraph import NetGraph
from XMLGraphParser import XMLGraphParser
from utils import fail

from socket import gethostname
import netifaces
import os

def main():
    topology_file = "/topology.xml"
    graph = NetGraph()

    XMLGraphParser(topology_file, graph).fill_graph()

    graph.resolve_hostnames()

    #Get our own ip address and set the root of the "tree"
    interface = os.environ.get['NETWORK_INTERFACE']
    if interface is None:
        fail("NETWORK_INTERFACE environment variable is not set!")
    if interface not in netifaces.interfaces():
        fail("$NETWORK_INTERFACE: " + interface + " does not exist!")
    ownIP = netifaces.ifaddresses(interface)[netifaces.AF_INET]['addr']
    currentServiceName = gethostname()
    for host in graph.services[currentServiceName]:
        if(host.ip == ownIP):
            graph.root = host
    if graph.root is None:
        fail("Failed to identify current service instance in topology!")

    # TODO Calculate shortest paths
    # TODO Call TC init and init all destinations
    # TODO Go beyoind static emulation


if __name__ == '__main__':
    main()
