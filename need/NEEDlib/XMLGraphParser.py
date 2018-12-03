import xml.etree.ElementTree as ET
from random import choice, randint
from string import ascii_letters

from need.NEEDlib.utils import fail, message
from need.NEEDlib.NetGraph import NetGraph
from need.NEEDlib.EventScheduler import EventScheduler

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List, Tuple

class XMLGraphParser:
    def __init__(self, file, graph):
        self.file = file
        self.graph = graph  # type: NetGraph
        self.supervisors = []  # type: List[NetGraph.Service]

    def parse_services(self, experiment, services):
        for service in services:
            if service.tag != 'service':
                fail('Invalid tag inside <services>: ' + service.tag)
            if 'name' not in service.attrib or 'image' not in service.attrib:
                fail('A service needs a name and an image attribute.')
            if not service.attrib['name'] or not service.attrib['image']:
                fail('A service needs a name and an image attribute.')


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
                    fail('replicas attribute must be a valid integer.')
            replicas = self.calulate_required_replicas(service.attrib['name'], replicas, experiment, reuse)

            for i in range(replicas):
                    srv = self.graph.new_service(
                        service.attrib['name'], service.attrib['image'], command, shared, reuse)
                    if supervisor:
                        self.supervisors.append(srv)
                        srv.supervisor_port = supervisor_port
                        srv.supervisor = True

    def parse_bridges(self, root):
        for bridge in root:
            if bridge.tag != 'bridge':
                fail('Invalid tag inside <bridges>: ' + bridge.tag)
            if 'name' not in bridge.attrib:
                fail('A bridge needs to have a name.')
            if not bridge.attrib['name']:
                fail('A bridge needs to have a name.')
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
                fail('Invalid tag inside <links>: ' + link.tag)
            if 'origin' not in link.attrib or 'dest' not in link.attrib or 'latency' not in link.attrib or \
                    'upload' not in link.attrib or 'network' not in link.attrib:
                fail("Incomplete link description.")

            source_nodes = self.graph.get_nodes(link.attrib['origin'])
            destination_nodes = self.graph.get_nodes(link.attrib['dest'])

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
                                    jitter, drop, link.attrib['upload'], link.attrib['network'])
                if bidirectional:
                    self.graph.new_link(dst_meta_bridge, src_meta_bridge, link.attrib['latency'],
                                    jitter, drop, link.attrib['download'], link.attrib['network'])
                # connect source to src meta bridge
                self.graph.new_link(link.attrib['origin'], src_meta_bridge, 0,
                                    0, 0.0, link.attrib['upload'], link.attrib['network'])
                if bidirectional:
                    self.graph.new_link(src_meta_bridge, link.attrib['origin'], 0,
                                    0, 0.0, link.attrib['download'], link.attrib['network'])
                # connect destination to dst meta bridge
                self.graph.new_link(dst_meta_bridge, link.attrib['dest'], 0,
                                    0, 0.0, link.attrib['upload'], link.attrib['network'])
                if bidirectional:
                    self.graph.new_link(link.attrib['dest'], dst_meta_bridge, 0,
                                    0, 0.0, link.attrib['download'], link.attrib['network'])
            elif source_nodes[0].shared_link:
                meta_bridge = self.create_meta_bridge()
                # create a link between meta bridge and destination
                self.graph.new_link(meta_bridge, link.attrib['dest'], link.attrib['latency'],
                                    jitter, drop, link.attrib['upload'], link.attrib['network'])
                if bidirectional:
                    self.graph.new_link(link.attrib['dest'], meta_bridge, link.attrib['latency'],
                                    jitter, drop, link.attrib['download'], link.attrib['network'])
                # connect origin to meta bridge
                self.graph.new_link(link.attrib['origin'], meta_bridge, 0,
                                    0, 0.0, link.attrib['upload'], link.attrib['network'])
                if bidirectional:
                    self.graph.new_link(meta_bridge, link.attrib['origin'], 0,
                                    0, 0.0, link.attrib['download'], link.attrib['network'])
            elif destination_nodes[0].shared_link:
                meta_bridge = self.create_meta_bridge()
                # create a link between origin and meta_bridge
                self.graph.new_link(link.attrib['origin'], meta_bridge, link.attrib['latency'],
                                    jitter, drop, link.attrib['upload'], link.attrib['network'])
                if bidirectional:
                    self.graph.new_link(meta_bridge, link.attrib['origin'], link.attrib['latency'],
                                    jitter, drop, link.attrib['download'], link.attrib['network'])
                # connect meta bridge to destination
                self.graph.new_link(meta_bridge, link.attrib['dest'], 0,
                                    0, 0.0, link.attrib['upload'], link.attrib['network'])
                if bidirectional:
                    self.graph.new_link(link.attrib['dest'], meta_bridge, 0,
                                    0, 0.0, link.attrib['download'], link.attrib['network'])
            else:
                # Regular case create a link between origin and destination
                self.graph.new_link(link.attrib['origin'], link.attrib['dest'], link.attrib['latency'],
                                jitter, drop, link.attrib['upload'], link.attrib['network'])
                if bidirectional:
                    self.graph.new_link(link.attrib['dest'], link.attrib['origin'], link.attrib['latency'],
                                jitter, drop, link.attrib['download'], link.attrib['network'])

    def calulate_required_replicas(self, service, hardcoded_count, root, reuse):
        dynamic = None
        for child in root:
            if child.tag == 'dynamic':
                if dynamic is not None:
                    fail("Only one <dynamic> block is allowed.")
                dynamic = child

        if dynamic is None:
            return hardcoded_count

        # first we collect the join/leave/crash events so we can later sort them and calculate the required replicas
        join_leave_events = []  # type: List[Tuple[float, int]]

        has_joins = False

        for event in dynamic:
            if event.tag != 'schedule':
                fail("Only <schedule> is allowed inside <dynamic>")
            if 'name' in event.attrib and 'time' in event.attrib and 'action' in event.attrib:
                # parse name of service
                if event.attrib['name'] != service:
                    continue

                # parse time of event
                time = 0.0
                try:
                    time = float(event.attrib['time'])
                    if time < 0.0:
                        fail("time attribute must be a positive number")
                except ValueError as e:
                    fail("time attribute must be a valid real number")

                # parse amount
                amount = 1
                if 'amount' in event.attrib:
                   try:
                       amount = int(event.attrib['amount'])
                       if amount < 1:
                           fail("amount attribute must be an integer >= 1")
                   except ValueError as e:
                       fail("amount attribute must be an integer >= 1")

                # parse action
                if event.attrib['action'] == 'join':
                   has_joins = True
                   join_leave_events.append((time, amount))
                elif event.attrib['action'] == 'leave':
                    join_leave_events.append((time, -amount))
                elif event.attrib['action'] == 'crash':
                    join_leave_events.append((time, -amount))

        if not has_joins:
            return hardcoded_count

        join_leave_events.sort(key=lambda event: event[0])
        max_replicas = 0

        if reuse:
            # If we reuse ips, then calculate the maximum number of concurrently active replicas
            current_replicas = 0
            for event in join_leave_events:
                current_replicas += event[1]
                if current_replicas < 0:
                    fail("Dynamic section for " + service + " causes a negative number of replicas at second " + str(event[0]))
                if current_replicas > max_replicas:
                    max_replicas = current_replicas

            return max_replicas
        else:
            # If we do not reuse ips then calculate how many replicas join
            for event in join_leave_events:
                if event[1] > 0:  # if event is a join
                    max_replicas += event[1]
            return max_replicas

    def fill_graph(self):
        XMLtree = ET.parse(self.file)
        root = XMLtree.getroot()
        if root.tag != 'experiment':
            fail('Not a valid NEED topology file, root is not <experiment>')

        if 'boot' not in root.attrib:
            fail('<experiment boot="?"> The experiment needs a valid boostrapper image name')

        self.graph.bootstrapper = root.attrib['boot']
        services = None
        bridges = None
        links = None
        for child in root:
            if child.tag == 'services':
                if services is not None:
                    fail("Only one <services> block is allowed.")
                services = child
            elif child.tag == 'bridges':
                if bridges is not None:
                    fail("Only one <bridges> block is allowed.")
                bridges = child
            elif child.tag == 'links':
                if links is not None:
                    fail("Only one <links> block is allowed.")
                links = child
            elif child.tag == 'dynamic':
                pass
            else:
                fail('Unknown tag: ' + child.tag)

        # Links must be parsed last
        if services is None:
            fail("No services declared in topology description")
        self.parse_services(root, services)
        if bridges is not None:
            self.parse_bridges(bridges)
        if links is None:
            fail("No links declared in topology descritpion")
        self.parse_links(links)

        for service in self.supervisors:
            self.graph.set_supervisor(service)

    def parse_schedule(self, service):
        """
        :param service: NetGraph.Service
        :return:
        """
        XMLtree = ET.parse(self.file)
        root = XMLtree.getroot()
        if root.tag != 'experiment':
            fail('Not a valid NEED topology file, root is not <experiment>')

        dynamic = None

        for child in root:
            if child.tag == 'services':
                pass
            elif child.tag == 'bridges':
                pass
            elif child.tag == 'links':
                pass
            elif child.tag == 'dynamic':
                if dynamic is not None:
                    fail("Only one <dynamic> block is allowed.")
                dynamic = child
            else:
                fail('Unknown tag: ' + child.tag)

        scheduler = EventScheduler()
        first_join = -1.0
        first_leave = float('inf')

        # if there is no dynamic block than this instance joins straight away
        if dynamic is None:
            scheduler.schedule_join(0.0)
            return scheduler

        active_replica_count = 0  # counts active replicas for reuse ip case
        used_replica_count = 0  # counts replicas that have joined (left replicas will not be subtracted)
        left_replica_count = 0  # counts number of replicas that have left
        disconnected_replica_count = 0  # counts the number of replicas that are currently disconnected

        lowest_active_replica = 0  # keeps track of the lowest active replica (should always be 0 if reuse == True)

        # there is a dynamic block, so check if there is anything scheduled for us
        for event in dynamic:
            if event.tag != 'schedule':
                fail("Only <schedule> is allowed inside <dynamic>")
            if 'name' in event.attrib and 'time' in event.attrib and 'action' in event.attrib:
                # parse name of service
                if event.attrib['name'] != service.name:
                    continue

                # parse time of event
                time = 0.0
                try:
                    time = float(event.attrib['time'])
                    if time < 0.0:
                        fail("time attribute must be a positive number")
                except ValueError as e:
                    fail("time attribute must be a valid real number")

                # parse amount of replicas affected
                amount = 1
                if 'amount' in event.attrib:
                    amount = int(event.attrib['amount'])

                # parse action
                # join always adds to the end of active replicas
                if event.attrib['action'] == 'join':
                    if service.reuse_ip:
                        lower_threshold = active_replica_count
                        active_replica_count += amount
                        upper_threshold = active_replica_count
                        highest_active_replica = active_replica_count
                    else:
                        lower_threshold = used_replica_count
                        used_replica_count += amount
                        upper_threshold = used_replica_count
                        highest_active_replica = used_replica_count

                    if lower_threshold <= service.replica_id < upper_threshold:
                        scheduler.schedule_join(time)
                        message(service.name + " replica " + str(service.replica_id) + " scheduled to join at " + str(time))
                    if first_join < 0.0:
                        first_join = time

                # leave leaves from the end if reusing and from beginning if not reusing
                elif event.attrib['action'] == 'leave' or event.attrib['action'] == 'crash':
                    if service.reuse_ip:
                        upper_threshold = active_replica_count
                        active_replica_count -= amount
                        left_replica_count += amount
                        lower_threshold = active_replica_count
                        highest_active_replica = active_replica_count
                    else:
                        lower_threshold = left_replica_count
                        left_replica_count += amount
                        upper_threshold = left_replica_count
                        lowest_active_replica = left_replica_count

                    if upper_threshold > service.replica_id >= lower_threshold:
                        if event.attrib['action'] == 'leave':
                            scheduler.schedule_leave(time)
                            message(service.name + " replica " + str(service.replica_id) +
                                    " scheduled to leave at " + str(time))
                        elif event.attrib['action'] == 'crash':
                            scheduler.schedule_crash(time)
                            message(service.name + " replica " + str(service.replica_id) +
                                    " scheduled to crash at " + str(time))
                    if first_leave > time:
                        first_leave = time

                # Disconnect/Reconnect always does so from the beginning of active replicas
                elif event.attrib['action'] == 'reconnect':
                    prev_disconnected_count = disconnected_replica_count
                    disconnected_replica_count -= amount
                    if prev_disconnected_count + lowest_active_replica > \
                            service.replica_id \
                            >= disconnected_replica_count + lowest_active_replica:
                        message(service.name + " replica " + str(service.replica_id) +
                                " scheduled to reconnect at " + str(time))
                        scheduler.schedule_reconnect(time)

                elif event.attrib['action'] == 'disconnect':
                    disconnected_replica_count += amount
                    if lowest_active_replica <= service.replica_id < disconnected_replica_count + lowest_active_replica:
                        message(service.name + " replica " + str(service.replica_id) +
                                " scheduled to disconnect at " + str(time))
                        scheduler.schedule_disconnect(time)
                else:
                    fail("Unrecognized action: " + event.attrib['action'] +
                         " , allowed actions are join, leave, crash, disconnect, reconnect")

            else:
                fail('<schedule> must have name, time and action attributes')

        # deal with auto join
        if first_join < 0.0:
            message(service.name + " scheduled to join at " + str(0.0))
            scheduler.schedule_join(0.0)
        if(first_leave < first_join):
            fail("Dynamic: service " + service.name + " leaves before having joined")

        return scheduler
