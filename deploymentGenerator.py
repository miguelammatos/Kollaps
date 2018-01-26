#! /usr/bin/python
import sys

from NetGraph import NetGraph
from XMLGraphParser import XMLGraphParser
from ComposeFileGenerator import ComposeFileGenerator


def main():
    if(len(sys.argv) != 2):
        print("Usage: deploymentGenerator.py <input topology> > <output compose file>")
        exit(-1)

    topology_file = sys.argv[1]
    graph = NetGraph()

    XMLGraphParser(topology_file, graph).fill_graph()
    ComposeFileGenerator(topology_file, graph).generate()


if __name__ == '__main__':
    main()