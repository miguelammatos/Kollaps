#! /usr/bin/python
import sys

from NetGraph import NetGraph
from XMLGraphParser import XMLGraphParser
from ComposeFileGenerator import ComposeFileGenerator
from utils import fail, INT_LIMIT


def main():
    if(len(sys.argv) != 2):
        print("Usage: deploymentGenerator.py <input topology> > <output compose file>")
        exit(-1)

    topology_file = sys.argv[1]
    graph = NetGraph()

    XMLGraphParser(topology_file, graph).fill_graph()
    if len(graph.links) > INT_LIMIT:
        fail("Topology has too many links: " + str(len(graph.links)))

    ComposeFileGenerator(topology_file, graph).generate()


if __name__ == '__main__':
    main()