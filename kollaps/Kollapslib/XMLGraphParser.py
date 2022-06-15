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
import xml.etree.ElementTree as ET
from random import choice, randint, seed, randrange
from string import ascii_letters

from kollaps.Kollapslib.utils import print_and_fail, print_identified, print_message
from kollaps.Kollapslib.NetGraph import NetGraph

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List, Tuple

class XMLGraphParser:
    def __init__(self, file, graph,mode):
        self.file = file
        self.graph = graph  # type: NetGraph
        self.supervisors = []  # type: List[NetGraph.Service]
        self.mode = mode

    def parse_services(self, experiment, services):
        for service in services:
            if service.tag != 'service':
                print_and_fail('Invalid tag inside <services>: ' + service.tag)
            if self.mode == "container":
                if 'name' not in service.attrib or 'image' not in service.attrib:
                    print_and_fail('A service needs a name and an image attribute.')
                if not service.attrib['name'] or not service.attrib['image']:
                    print_and_fail('A service needs a name and an image attribute.')
            if self.mode == "baremetal":
                if 'name' not in service.attrib:
                    print_and_fail('A service needs a name.')
                if not service.attrib['name']:
                    print_and_fail('A service needs a name.')


            command = None
            if 'command' in service.attrib:
                command = service.attrib['command']

            shared = False
            if 'share' in service.attrib:
                shared = (service.attrib['share'] == "true")

            supervisor = False
            supervisor_port = 0
            if 'supervisor' in service.attrib:
                supervisor = True
                if 'port' in service.attrib:
                    supervisor_port =  int(service.attrib['port'])

            reuse = True
            if 'reuse' in service.attrib:
                reuse = (service.attrib['reuse'] == "true")

            replicas = 1
            if 'replicas' in service.attrib:
                try:
                    replicas = int(service.attrib['replicas'])
                except:
                    print_and_fail('replicas attribute must be a valid integer.')
            replicas = self.calulate_required_replicas(service.attrib['name'], replicas, experiment, reuse)

            for i in range(replicas):
                    srv = None
                    if self.mode == "container":
                        srv = self.graph.new_service(service.attrib['name'], service.attrib['image'], command, shared, reuse, replicas)
                    if self.mode == "baremetal":
                        srv = self.graph.new_service(service.attrib['name'], "none", command, shared, reuse, replicas)
                        if "ip" in service.attrib:
                            srv.ip = service.attrib['ip']
                        if "machinename" in service.attrib:
                            srv.machinename = service.attrib["machinename"]
                            if 'kollaps_folder' not in service.attrib:
                                print_and_fail('In baremetal must provide the location of the folder containing kollaps binaries in the remote machine')
                            srv.kollaps_folder = service.attrib["kollaps_folder"]
                            if not supervisor:
                                if 'topology_file' not in service.attrib:
                                    print_and_fail('In baremetal must provide the name of the topology file in the remote machine')
                                srv.topology_file = service.attrib["topology_file"]
                    if supervisor:
                        self.supervisors.append(srv)
                        srv.supervisor_port = supervisor_port
                        srv.supervisor = True
                        if "controllername" in service.attrib:
                            srv.controllername = service.attrib['controllername']

    def parse_bridges(self, root):
        for bridge in root:
            if bridge.tag != 'bridge':
                print_and_fail('Invalid tag inside <bridges>: ' + bridge.tag)
            if 'name' not in bridge.attrib:
                print_and_fail('A bridge needs to have a name.')
            if not bridge.attrib['name']:
                print_and_fail('A bridge needs to have a name.')
            self.graph.new_bridge(bridge.attrib['name'])

    def create_meta_bridge(self):
        while True:  # do-while loop
            meta_bridge_name = "".join(choice(ascii_letters) for x in range(randint(128, 128)))
            if len(self.graph.get_nodes(meta_bridge_name)) == 0:
                break
        self.graph.new_bridge(meta_bridge_name)
        return meta_bridge_name

    def parse_links(self, root):
        for link in root:
            if link.tag != 'link':
                print_and_fail('Invalid tag inside <links>: ' + link.tag)
            if self.mode == "container":
                if 'origin' not in link.attrib or 'dest' not in link.attrib or 'latency' not in link.attrib or \
                        'upload' not in link.attrib or 'network' not in link.attrib:
                    print_and_fail("Incomplete link description.")
            if self.mode == "baremetal":
                if 'origin' not in link.attrib or 'dest' not in link.attrib or 'latency' not in link.attrib or \
                    'upload' not in link.attrib:
                    print_and_fail("Incomplete link description.")

            source_nodes = self.graph.get_nodes(link.attrib['origin'])
            destination_nodes = self.graph.get_nodes(link.attrib['dest'])

            if self.mode == "container":
                network = link.attrib['network']
            if self.mode == "baremetal":
                network = "baremetal"
            jitter = 0
            if 'jitter' in link.attrib:
                jitter = link.attrib['jitter']
            drop = 0
            if 'drop' in link.attrib:
                drop = link.attrib['drop']

            bidirectional = ('download' in link.attrib)

            both_shared = (source_nodes[0].shared_link and destination_nodes[0].shared_link)
            if both_shared:
                src_meta_bridge = self.create_meta_bridge()

                dst_meta_bridge = self.create_meta_bridge()
                # create a link between both meta bridges
                self.graph.new_link(src_meta_bridge, dst_meta_bridge, link.attrib['latency'],
                                    jitter, drop, link.attrib['upload'], network)
                if bidirectional:
                    self.graph.new_link(dst_meta_bridge, src_meta_bridge, link.attrib['latency'],
                                    jitter, drop, link.attrib['download'], network)
                # connect source to src meta bridge
                self.graph.new_link(link.attrib['origin'], src_meta_bridge, 0,
                                    0, 0.0, link.attrib['upload'], network)
                if bidirectional:
                    self.graph.new_link(src_meta_bridge, link.attrib['origin'], 0,
                                    0, 0.0, link.attrib['download'], network)
                # connect destination to dst meta bridge
                self.graph.new_link(dst_meta_bridge, link.attrib['dest'], 0,
                                    0, 0.0, link.attrib['upload'], network)
                if bidirectional:
                    self.graph.new_link(link.attrib['dest'], dst_meta_bridge, 0,
                                    0, 0.0, link.attrib['download'], network)
            elif source_nodes[0].shared_link:
                meta_bridge = self.create_meta_bridge()
                # create a link between meta bridge and destination
                self.graph.new_link(meta_bridge, link.attrib['dest'], link.attrib['latency'],
                                    jitter, drop, link.attrib['upload'], network)
                if bidirectional:
                    self.graph.new_link(link.attrib['dest'], meta_bridge, link.attrib['latency'],
                                    jitter, drop, link.attrib['download'], network)
                # connect origin to meta bridge
                self.graph.new_link(link.attrib['origin'], meta_bridge, 0,
                                    0, 0.0, link.attrib['upload'], network)
                if bidirectional:
                    self.graph.new_link(meta_bridge, link.attrib['origin'], 0,
                                    0, 0.0, link.attrib['download'], network)
            elif destination_nodes[0].shared_link:
                meta_bridge = self.create_meta_bridge()
                # create a link between origin and meta_bridge
                self.graph.new_link(link.attrib['origin'], meta_bridge, link.attrib['latency'],
                                    jitter, drop, link.attrib['upload'], network)
                if bidirectional:
                    self.graph.new_link(meta_bridge, link.attrib['origin'], link.attrib['latency'],
                                    jitter, drop, link.attrib['download'], network)
                # connect meta bridge to destination
                self.graph.new_link(meta_bridge, link.attrib['dest'], 0,
                                    0, 0.0, link.attrib['upload'], network)
                if bidirectional:
                    self.graph.new_link(link.attrib['dest'], meta_bridge, 0,
                                    0, 0.0, link.attrib['download'], network)
            else:
                # Regular case create a link between origin and destination
                self.graph.new_link(link.attrib['origin'], link.attrib['dest'], link.attrib['latency'],
                                jitter, drop, link.attrib['upload'], network)
                if bidirectional:
                    self.graph.new_link(link.attrib['dest'], link.attrib['origin'], link.attrib['latency'],
                                jitter, drop, link.attrib['download'], network)

    def calulate_required_replicas(self, service, hardcoded_count, root, reuse):
        dynamic = None
        for child in root:
            if child.tag == 'dynamic':
                if dynamic is not None:
                    print_and_fail("Only one <dynamic> block is allowed.")
                dynamic = child

        if dynamic is None:
            return hardcoded_count

        # first we collect the join/leave/crash/disconnect/reconnect events
        # so we can later sort them and calculate the required replicas
        events = []  # type: List[Tuple[float, int, int]]
        JOIN = 1
        LEAVE = 2
        CRASH = 3
        DISCONNECT = 4
        RECONNECT = 5

        TIME = 0
        AMMOUNT = 1
        TYPE = 2

        has_joins = False

        for event in dynamic:
            if event.tag != 'schedule':
                print_and_fail("Only <schedule> is allowed inside <dynamic>")
            if 'name' in event.attrib and 'time' in event.attrib and 'action' in event.attrib:
                # parse name of service
                if event.attrib['name'] != service:
                    continue

                # parse time of event
                time = 0.0
                try:
                    time = float(event.attrib['time'])
                    if time < 0.0:
                        print_and_fail("time attribute must be a positive number")
                except ValueError as e:
                    print_and_fail("time attribute must be a valid real number")

                # parse amount
                amount = 1
                if 'amount' in event.attrib:
                   try:
                       amount = int(event.attrib['amount'])
                       if amount < 1:
                           print_and_fail("amount attribute must be an integer >= 1")
                   except ValueError as e:
                       print_and_fail("amount attribute must be an integer >= 1")

                # parse action
                if event.attrib['action'] == 'join':
                   has_joins = True
                   events.append((time, amount, JOIN))
                elif event.attrib['action'] == 'leave':
                    events.append((time, amount, LEAVE))
                elif event.attrib['action'] == 'crash':
                    events.append((time, amount, CRASH))
                elif event.attrib['action'] == 'disconnect':
                    events.append((time, amount, DISCONNECT))
                elif event.attrib['action'] == 'reconnect':
                    events.append((time, amount, RECONNECT))

        if not has_joins:
            return hardcoded_count

        events.sort(key=lambda event: event[TIME])
        max_replicas = 0
        cummulative_replicas = 0
        disconnected = 0

        # Calculate required replicas (and perform semantic checking)
        current_replicas = 0
        for event in events:
            if event[TYPE] == JOIN:
                current_replicas += event[AMMOUNT]
                cummulative_replicas += event[AMMOUNT]
            elif event[TYPE] == LEAVE or event[TYPE] == CRASH:
                current_replicas -= event[AMMOUNT]
            elif event[TYPE] == DISCONNECT:
                disconnected += event[AMMOUNT]
                if event[AMMOUNT] > current_replicas:
                    print_and_fail("Dynamic section for " + service + " disconnects more replicas than are joined at second "
                         + str(event[TIME]))
            elif event[TYPE] == RECONNECT:
                disconnected -= event[AMMOUNT]
                if event[AMMOUNT] > disconnected:
                    print_and_fail("Dynamic section for " + service + " reconnects more replicas than are disconnected at second "
                         + str(event[TIME]))
            if current_replicas < 0:
                print_and_fail("Dynamic section for " + service + " causes a negative number of replicas at second " + str(event[TIME]))
            if current_replicas > max_replicas:
                max_replicas = current_replicas

        if reuse:
            return max_replicas
        else:
            return cummulative_replicas


    def fill_graph(self):
        XMLtree = ET.parse(self.file)
        root = XMLtree.getroot()
        if root.tag != 'experiment':
            print_and_fail('Not a valid Kollaps topology file, root is not <experiment>')

        if 'boot' not in root.attrib:
            print_and_fail('<experiment boot="?"> The experiment needs a valid boostrapper image name')

        self.graph.bootstrapper = root.attrib['boot']
        services = None
        bridges = None
        links = None
        for child in root:
            if child.tag == 'services':
                if services is not None:
                    print_and_fail("Only one <services> block is allowed.")
                services = child
            elif child.tag == 'bridges':
                if bridges is not None:
                    print_and_fail("Only one <bridges> block is allowed.")
                bridges = child
            elif child.tag == 'links':
                if links is not None:
                    print_and_fail("Only one <links> block is allowed.")
                links = child
            elif child.tag == 'dynamic':
                pass
            else:
                print_and_fail('Unknown tag: ' + child.tag)

        # Links must be parsed last
        if services is None:
            print_and_fail("No services declared in topology description")
        self.parse_services(root, services)
        if bridges is not None:
            self.parse_bridges(bridges)
        if links is None:
            print_and_fail("No links declared in topology descritpion")
        self.parse_links(links)

        for service in self.supervisors:
            self.graph.set_supervisor(service)

