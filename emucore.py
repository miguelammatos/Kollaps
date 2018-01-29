#! /usr/bin/python
from NetGraph import NetGraph
from XMLGraphParser import XMLGraphParser
from utils import fail
import PathEmulation


import subprocess
from socket import gethostname
import netifaces
import os
import sys


def main():
    if len(sys.argv) != 2:
        topology_file = "/topology.xml"
    else:
        topology_file = sys.argv[1]

    # Because of the bootstrapper hack we cant get output from the emucore through standard docker logs...
    sys.stdout = open("/var/log/need.log", "w")
    sys.stderr = open("/var/log/need_error.log", "w")

    graph = NetGraph()

    XMLGraphParser(topology_file, graph).fill_graph()

    #__debug_print_paths(graph)
    #return

    graph.resolve_hostnames()

    # Get our own ip address and set the root of the "tree"
    interface = os.environ.get('NETWORK_INTERFACE', 'eth0')
    if interface is None:
        fail("NETWORK_INTERFACE environment variable is not set!")
    if interface not in netifaces.interfaces():
        fail("$NETWORK_INTERFACE: " + interface + " does not exist!")
    ownIP = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]['addr']

    currentServiceName = gethostname()
    for host in graph.services[currentServiceName]:
        if host.ip == ownIP:
            graph.root = host
    if graph.root is None:
        fail("Failed to identify current service instance in topology!")

    graph.calculate_shortest_paths()

    PathEmulation.init()
    for service in graph.paths:
        path = graph.paths[service]
        PathEmulation.initialize_path(path)

    # Temporary hack to start the experiment
    subprocess.run('echo "done\n" > /tmp/readypipe', shell=True)

    # TODO Go beyond static emulation


def __debug_print_paths(graph):
    graph.root = graph.services["leaf"][0]

    graph.calculate_shortest_paths()
    for node in graph.paths:
        path = graph.paths[node]
        print("##############################")
        print(graph.root.name + " -> " + node.name + ":" + str(node.__hash__()))
        print("latency: " + str(graph.calculate_path_latency(path)))
        print("drop: " + str(graph.calculate_path_drop(path)))
        print("bandwidth: " + str(graph.calculate_path_max_initial_bandwidth(path)))
        print("------------------------------")
        for link in path:
            print("   " + link.source.name + " hop " + link.destination.name)


if __name__ == '__main__':
    main()
