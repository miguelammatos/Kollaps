#! /usr/bin/python
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import sys
import os

from kollaps.Kollapslib.NetGraph import NetGraph
from kollaps.Kollapslib.XMLGraphParser import XMLGraphParser
from kollaps.Kollapslib.deploymentGenerators.DockerComposeFileGenerator import DockerComposeFileGenerator
from kollaps.Kollapslib.deploymentGenerators.KubernetesManifestGenerator import KubernetesManifestGenerator
from kollaps.Kollapslib.utils import SHORT_LIMIT
from kollaps.Kollapslib.utils import print_message, print_error, print_and_fail


def main():
    if not (len(sys.argv) == 3 or len(sys.argv) == 4):
        msg = "Usage: deploymentGenerator.py <input topology> <orchestrator> > <output compose file>\n" \
             + "    <orchestrator> can be -s for Docker Swarm or -k for Kubernetes" \
             + "    optionally use -d to deactivate bandwidth emulation at runtime."

        print_and_fail(msg)
        
    
    shm_size = 8000000000
    aeron_lib_path = "/home/daedalus/Documents/aeron4need/cppbuild/Release/lib/libaeronlib.so"
    aeron_term_buffer_length = 64*1024*1024           # must be multiple of 64*1024
    aeron_ipc_term_buffer_length = 64*1024*1024   	# must be multiple of 64*1024

    threading_mode = 'SHARED'             # aeron uses 1 thread
    # threading_mode = 'SHARED_NETWORK'   # aeron uses 2 threads
    # threading_mode = 'DEDICATED'        # aeron uses 3 threads

    pool_period = 0.05
    max_flow_age = 2
    
    output = ""
    
    # TODO use argparse to check for flags and arguments properly
    
    topology_file = sys.argv[1]
    
    orchestrator = "kubernetes" if sys.argv[2] == "-k" else "swarm"
    
    bw_emulation = False if (len(sys.argv) > 3 and sys.argv[3] == "-d") else True

    graph = NetGraph()

    XMLGraphParser(topology_file, graph).fill_graph()
    output += "Graph has " + str(len(graph.links)) + " links.\n"
    service_count = 0
    
    for hosts in graph.services:
        for host in graph.services[hosts]:
            service_count += 1
            
    output += "      has " + str(service_count) + " hosts.\n"

    if len(graph.links) > SHORT_LIMIT:
        print_and_fail("Topology has too many links: " + str(len(graph.links)))
        
    for path in graph.paths:
        if len(path.links) > 249:
            msg = "Path from " + path.links[0].source.name + " to " \
                  + path.links[-1].destination.name + " is too long (over 249 hops)"
            print_and_fail(msg)
    
    generator = None
    if orchestrator == "kubernetes":
        generator = KubernetesManifestGenerator(os.getcwd() + "/" + topology_file, graph)

    elif orchestrator == 'swarm':
        generator = DockerComposeFileGenerator(topology_file, graph)
        
    # insert here any other generators required by new orchestrators
    else:
        pass
    
    if generator is not None:
        generator.generate(pool_period, max_flow_age, threading_mode, shm_size, aeron_lib_path, aeron_term_buffer_length, aeron_ipc_term_buffer_length, bw_emulation)
        output += "Experiment UUID: " + generator.experiment_UUID
        print(output, file=sys.stderr)
        
    else:
        print("Failed to find a suitable generator.", file=sys.stderr)


if __name__ == '__main__':
    main()
    
    
