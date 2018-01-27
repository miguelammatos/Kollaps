#! /usr/bin/python
from NetGraph import NetGraph
from XMLGraphParser import XMLGraphParser
from utils import fail

from socket import gethostname
import netifaces
import os
import sys

def main():
    if(len(sys.argv) != 2):
        topology_file = "/topology.xml"
    else:
        topology_file = sys.argv[1]

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

    graph.calculate_shortest_paths()

'''
#TEMP REMOVE ME
graph.root = graph.services["leaf"][0]
#_____________

graph.calculate_shortest_paths()
for node in graph.paths:
    path = graph.paths[node]
    if len(path) < 1:
        continue
    print(graph.root.name + " -> " + node.name)
    for link in path:
        print("   " + link.source + " hop " + link.destination)
'''

    # TODO Call TC init and init all destinations
    # TODO Go beyoind static emulation


if __name__ == '__main__':
    main()
