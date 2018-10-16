#! /usr/bin/python
from need.NEEDlib.NetGraph import NetGraph
from need.NEEDlib.XMLGraphParser import XMLGraphParser
from need.NEEDlib.EmulationManager import EmulationManager
from need.NEEDlib.utils import fail, ENVIRONMENT, int2ip


import socket
import sys
from uuid import uuid4


def get_own_ip(graph):
    # Old way using the netifaces dependency (bad because it has a binary component)
    # interface = os.environ.get(ENVIRONMENT.NETWORK_INTERFACE, 'eth0')
    # if interface is None:
    #     fail("NETWORK_INTERFACE environment variable is not set!")
    # if interface not in netifaces.interfaces():
    #     fail("$NETWORK_INTERFACE: " + interface + " does not exist!")
    # ownIP = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]['addr']

    # New way:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    last_ip = None
    # Connect to at least 2 to avoid using our own ip
    for int_ip in graph.hosts_by_ip:
        s.connect((int2ip(int_ip),1))
        new_ip = s.getsockname()[0]
        if new_ip == last_ip:
            break
        last_ip = new_ip
    return last_ip



def main():
    if len(sys.argv) != 2:
        topology_file = "/topology.xml"
    else:
        topology_file = sys.argv[1]
    # For future reference: This topology file must not exceed 512KB otherwise docker refuses
    # to copy it as a config file, this has happened with the 2k scale-free topology...


    instance_UUID = str(uuid4())
    # Because of the bootstrapper hack we cant get output from the emucore through standard docker logs...
    sys.stdout = open("/var/log/need_" + instance_UUID + ".log", "w")
    sys.stderr = sys.stdout

    graph = NetGraph()

    XMLGraphParser(topology_file, graph).fill_graph()
    print("Done parsing topology")

    print("Resolving hostnames...")
    graph.resolve_hostnames()
    print("All hosts found!")

    print("Determining the root of the tree...")
    # Get our own ip address and set the root of the "tree"
    ownIP = get_own_ip(graph)
    currentServiceName = socket.gethostname()
    for host in graph.services[currentServiceName]:
        if int2ip(host.ip) == ownIP:
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
