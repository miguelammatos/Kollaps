#! /usr/bin/python
from NEED.NetGraph import NetGraph
from NEED.XMLGraphParser import XMLGraphParser
from NEED.EmulationManager import EmulationManager
from NEED.utils import fail


from socket import gethostname
import netifaces
import os, signal, sys

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
    print("Done parsing topology")

    print("Resolving hostnames...")
    graph.resolve_hostnames()
    print("All hosts found!")

    print("Determining the root of the tree...")
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
    print("We are " + currentServiceName + "@" + ownIP)

    print("Calculating shortest paths...")
    graph.calculate_shortest_paths()

    print("Initializing network emulation...")
    manager = EmulationManager(graph)
    manager.initialize()
    print("Waiting for command to start experiment")
    sys.stdout.flush()
    sys.stderr.flush()

    # Enter the emulation loop
    manager.emulation_loop()

if __name__ == '__main__':
    main()
