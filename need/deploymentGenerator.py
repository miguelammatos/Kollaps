#! /usr/bin/python
import sys
import os

from need.NEEDlib.NetGraph import NetGraph
from need.NEEDlib.XMLGraphParser import XMLGraphParser
from need.NEEDlib.DockerComposeFileGenerator import DockerComposeFileGenerator
from need.NEEDlib.KubernetesManifestGenerator import KubernetesManifestGenerator
from need.NEEDlib.utils import fail, SHORT_LIMIT
from need.NEEDlib.utils import print_message, print_error, print_and_fail


def main():
    if len(sys.argv) != 3:
        msg = "Usage: deploymentGenerator.py <input topology> <orchestrator> > <output compose file>\n" \
             + "    <orchestrator> can be -s for Docker Swarm or -k for Kubernetes"
        
        print_and_fail(msg)

    topology_file = sys.argv[1]
    orchestrator = "kubernetes" if sys.argv[2] == "-k" else "docker"
    graph = NetGraph()

    XMLGraphParser(topology_file, graph).fill_graph()
    print("Graph has " + str(len(graph.links)) + " links.", file=sys.stderr)
    service_count = 0
    
    for hosts in graph.services:
        for host in graph.services[hosts]:
            service_count += 1
            
    print("      has " + str(service_count) + " hosts.", file=sys.stderr)

    if len(graph.links) > SHORT_LIMIT:
        fail("Topology has too many links: " + str(len(graph.links)))
        
    for path in graph.paths:
        if len(path.links) > 249:
            msg = "Path from " + path.links[0].source.name + " to " \
                  + path.links[-1].destination.name + " is too long (over 249 hops)"
            print_and_fail(msg)

    generator = KubernetesManifestGenerator(os.getcwd()+"/"+topology_file, graph) if orchestrator == "kubernetes" else DockerComposeFileGenerator(topology_file, graph)
    generator.generate()
    
    print("Experiment UUID: " + generator.experiment_UUID, file=sys.stderr)


if __name__ == '__main__':
    main()
    
    