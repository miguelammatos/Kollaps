#! /usr/bin/python
import sys

from NEED.NetGraph import NetGraph
from NEED.XMLGraphParser import XMLGraphParser
from NEED.ComposeFileGenerator import ComposeFileGenerator
from NEED.utils import fail, SHORT_LIMIT


def main():
    if(len(sys.argv) != 2):
        print("Usage: deploymentGenerator.py <input topology> > <output compose file>")
        exit(-1)

    topology_file = sys.argv[1]
    graph = NetGraph()

    XMLGraphParser(topology_file, graph).fill_graph()
    print("Graph has " + str(len(graph.links)) + " links.", file=sys.stderr)
    service_count = 0
    for hosts in graph.services:
        for host in graph.services[hosts]:
            service_count += 1
    print("      has " + str(service_count) + " services.", file=sys.stderr)

    if len(graph.links) > SHORT_LIMIT:
        fail("Topology has too many links: " + str(len(graph.links)))
    for path in graph.paths:
        if len(path.links) > 249:
            fail("Path from " + path.links[0].source.name + " to " + path.links[-1].destination.name
                 + " is too long (over 249 hops)")

    ComposeFileGenerator(topology_file, graph).generate()


if __name__ == '__main__':
    main()