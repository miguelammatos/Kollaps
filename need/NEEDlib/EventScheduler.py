from need.NEEDlib.utils import start_experiment, stop_experiment, crash_experiment, message
from need.NEEDlib.PathEmulation import disconnect, reconnect, change_latency, change_loss, initialize_path
from need.NEEDlib.NetGraph import NetGraph

from threading import Timer
from copy import copy

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List


class EventScheduler:
    def __init__(self):
        self.events = []  # type: List[Timer]
        self.link_changes = [] # type: List[(float, NetGraph.Link)]
        self.path_changes = [] ############ TODO LL

    def start(self):
        for e in self.events:
            e.start()

    def schedule_join(self, time):
        self.events.append(Timer(time, start_experiment))

    def schedule_leave(self, time):
        self.events.append(Timer(time, stop_experiment))

    def schedule_crash(self, time):
        self.events.append(Timer(time, crash_experiment))

    def schedule_disconnect(self, time):
        self.events.append(Timer(time, disconnect))

    def schedule_reconnect(self, time):
        self.events.append(Timer(time, reconnect))

    #Remove a link that is currently part of the graph
    def schedule_link_leave(self, time, graph, origin, destination):
        if len(self.path_changes) == 0:
            current_graph = graph
        else:
            current_graph = self.path_changes[0][1] #work from the last change onwards

        new_graph = copy(current_graph)
        new_graph.paths = {}
        new_graph.paths_by_id = {}
        new_graph.path_counter = 0
        new_graph.links = copy(current_graph.links)
        new_graph.removed_links = copy(current_graph.removed_links)
        new_graph.removed_bridges = copy(current_graph.removed_bridges)
        for l in new_graph.links:
            if (l.source.name == origin and l.destination.name == destination) or (l.source.name == destination and l.destination.name == origin):
                new_graph.removed_links.append(l)
        for l in new_graph.removed_links:
            if l in new_graph.links: # and has not been removed before
                new_graph.links.remove(l)
                for node in new_graph.services:
                    for nodeinstance in new_graph.services[node]:
                        if l in nodeinstance.links:
                            nodeinstance.links.remove(l)
                for bridge in new_graph.bridges:
                    if l in new_graph.bridges[bridge][0].links:
                        new_graph.bridges[bridge][0].links.remove(l)

        new_graph.calculate_shortest_paths()

        for service, path in new_graph.paths.items():
            if not service == graph.root and isinstance(service, NetGraph.Service):
                path.calculate_end_to_end_properties()

        self.path_changes.append((time, new_graph))
        self.path_changes.sort(reverse=True, key=lambda change: change[0])

        message("Link " + origin + "--" + destination + " scheduled to leave at " + str(time))
        self.events.append(Timer(time, path_change, [graph, new_graph]))

    #Add back a link that has been removed before
    def schedule_link_join(self, time, graph, origin, destination):
        if len(self.path_changes) == 0:
            current_graph = graph
        else:
            current_graph = self.path_changes[0][1] #work from the last change onwards

        new_graph = copy(current_graph)
        new_graph.paths = {}
        new_graph.paths_by_id = {}
        new_graph.path_counter = 0
        new_graph.links = copy(current_graph.links)
        new_graph.removed_links = copy(current_graph.removed_links)
        new_graph.removed_bridges = copy(current_graph.removed_bridges)
        joining_links = []
        for link in new_graph.removed_links:
            if link.source.name == origin and link.destination.name == destination or link.source.name == destination and link.destination.name == origin:
                joining_links.append(link)
        for link in joining_links:
            new_graph.removed_links.remove(link)
            new_graph.links.append(link)

        for l in joining_links:
            for node in new_graph.services:
                if l.source == node:
                    for nodeinstance in new_graph.services[node]:
                        nodeinstance.links.append(l)
            for bridge in new_graph.bridges:
                if l.source == new_graph.bridges[bridge][0]:
                    new_graph.bridges[bridge][0].links.append(l)

        new_graph.calculate_shortest_paths()

        for service, path in new_graph.paths.items():
            if not service == graph.root and isinstance(service, NetGraph.Service):
                path.calculate_end_to_end_properties()

        self.path_changes.append((time, new_graph))
        self.path_changes.sort(reverse=True, key=lambda change: change[0])

        message("Link " + origin + "--" + destination + " scheduled to join at " + str(time))
        self.events.append(Timer(time, path_change, [graph, new_graph]))


    #Add a completely new link
    def schedule_new_link(self, time, graph, source, destination, latency, jitter, drop, bandwidth, network):
        if len(self.path_changes) == 0:
            current_graph = graph
        else:
            current_graph = self.path_changes[0][1] #work from the last change onwards

        new_graph = copy(current_graph)
        new_graph.paths = {}
        new_graph.paths_by_id = {}
        new_graph.path_counter = 0
        new_graph.links = copy(current_graph.links)
        new_graph.removed_links = copy(current_graph.removed_links)
        new_graph.removed_bridges = copy(current_graph.removed_bridges)
        new_graph.new_link(source, destination, latency, jitter, drop, bandwidth, network)
        new_graph.calculate_shortest_paths()

        for service, path in new_graph.paths.items():
            if not service == graph.root and isinstance(service, NetGraph.Service):
                path.calculate_end_to_end_properties()

        self.path_changes.append((time, new_graph))
        self.path_changes.sort(reverse=True, key=lambda change: change[0])

        message("Link " + source + "--" + destination + " scheduled to newly join at " + str(time))
        self.events.append(Timer(time, path_change, [graph, new_graph]))

    #Remove a bridge that is currently part of the graph
    def schedule_bridge_leave(self, time, graph, name):
        if len(self.path_changes) == 0:
            current_graph = graph
        else:
            current_graph = self.path_changes[0][1] #work from the last change onwards

        new_graph = copy(current_graph)
        new_graph.paths = {}
        new_graph.paths_by_id = {}
        new_graph.path_counter = 0
        new_graph.bridges = copy(current_graph.bridges)
        new_graph.removed_links = copy(current_graph.removed_links)
        new_graph.removed_bridges = copy(current_graph.removed_bridges)
        new_graph.removed_bridges[name] = new_graph.bridges[name]
        del new_graph.bridges[name]

        new_graph.calculate_shortest_paths()

        for service, path in new_graph.paths.items():
            if not service == graph.root and isinstance(service, NetGraph.Service):
                path.calculate_end_to_end_properties()

        self.path_changes.append((time, new_graph))
        self.path_changes.sort(reverse=True, key=lambda change: change[0])

        message("Bridge " + name + " scheduled to leave at " + str(time))
        self.events.append(Timer(time, path_change, [graph, new_graph]))

    #Add back a bridge that has been removed before
    def schedule_bridge_join(self, time, graph, name):
        if len(self.path_changes) == 0:
            current_graph = graph
        else:
            current_graph = self.path_changes[0][1] #work from the last change onwards

        new_graph = copy(current_graph)
        new_graph.paths = {}
        new_graph.paths_by_id = {}
        new_graph.path_counter = 0
        new_graph.bridges = copy(current_graph.bridges)
        new_graph.removed_links = copy(current_graph.removed_links)
        new_graph.removed_bridges = copy(current_graph.removed_bridges)
        bridge = new_graph.removed_bridges[name]
        del new_graph.removed_bridges[name]
        new_graph.bridges[name] = bridge

        new_graph.calculate_shortest_paths()

        for service, path in new_graph.paths.items():
            if not service == graph.root and isinstance(service, NetGraph.Service):
                path.calculate_end_to_end_properties()

        self.path_changes.append((time, new_graph))
        self.path_changes.sort(reverse=True, key=lambda change: change[0])

        message("Bridge " + name + " scheduled to join back at " + str(time))
        self.events.append(Timer(time, path_change, [graph, new_graph]))

    #Change the properties of a link that is part of the graph
    def schedule_link_change(self, time, graph, origin, destination, bandwidth, latency, jitter, drop):
        links = []
        new_links = []
        paths = []
        new_paths = []

        # Update link info
        for l in graph.links:
            if l.source.name == origin and l.destination.name == destination:
                links.append(l)
                copy_l = None

                # Check for previous changes
                for changed_event in self.link_changes:
                    changed_link = changed_event[1]  # type: NetGraph.Link
                    if changed_link.index == l.index:
                        copy_l = copy(changed_link)
                        break

                # if no previous changes
                if copy_l is None:
                    copy_l = copy(l)

                # at this point, copy_l has all attributes that l has at the time we schedule the link change. LL

                # Update only what has changed
                copy_l.bandwidth_bps = bandwidth if bandwidth >= 0 else copy_l.bandwidth_bps
                copy_l.latency = int(latency) if latency >= 0 else copy_l.latency
                copy_l.jitter = float(jitter) if jitter >= 0 else copy_l.jitter
                copy_l.drop = float(drop) if drop >= 0 else copy_l.drop

                new_links.append(copy_l)
                self.link_changes.append((time, copy_l))
                self.link_changes.sort(reverse=True, key=lambda change: change[0])  # make sure they are sorted in time

        # Update path info
        for key in graph.paths:
            if not isinstance(key, NetGraph.Service): # If we get a path to a bridge, ignore
                continue
            path = graph.paths[key]
            for new_link in new_links:
                for i, l in enumerate(path.links):
                    if l.index == new_link.index:
                        paths.append(path)  # There wont be duplicated paths since there cant be multiple changed links
                        new_path = copy(path) # in the same path (replicated links must be on different paths)

                        # Pre-compute the path properties
                        new_path.links = copy(path.links)
                        new_path.links[i] = new_link
                        new_path.calculate_end_to_end_properties()
                        new_paths.append(new_path)
                        break

        for link in links:
            message("Link " + link.source.name + ":" + link.destination.name + " scheduled to change at " + str(time))
        for path in paths:
            message("Path to" + path.links[-1].destination.name + " scheduled to change at " + str(time))

        self.events.append(Timer(time, link_change,
                                 [links, new_links, paths, new_paths]))



def link_change(links, new_links, paths, new_paths):
    for i, l in enumerate(links):
        with l.lock:
            l.bandwidth_bps = new_links[i].bandwidth_bps
            l.latency = new_links[i].latency
            l.jitter = new_links[i].jitter
            l.drop = new_links[i].drop

    for i, path in enumerate(paths):
        with path.lock:
            # Apply the precomputed path properties
            path.jitter = new_paths[i].jitter
            path.latency = new_paths[i].latency
            path.drop = new_paths[i].drop
            path.RTT = new_paths[i].RTT
            path.max_bandwidth = new_paths[i].max_bandwidth

            service = path.links[-1].destination
            change_loss(service, path.drop)
            change_latency(service, path.latency, path.jitter)
            # We dont explicitly change bandwidth, the emulation manager will handle that for us

            '''
            message("Path " + path.links[0].source.name + " to " + path.links[-1].destination.name +
                    " changed to bw:" + str(path.max_bandwidth) + " rtt:"+str(path.RTT)
                    + " j:" + str(path.jitter) + " l:" + str(path.drop))
            '''

def path_change(graph, new_graph):
    graph.paths_by_id = copy(new_graph.paths_by_id)
    graph.removed_links = copy(new_graph.removed_links)
    graph.removed_bridges = copy(new_graph.removed_bridges)

    for service in new_graph.paths:
        current_bw = graph.paths[service].current_bandwidth
        if not service == graph.root and isinstance(service, NetGraph.Service):
            with graph.paths[service].lock:
                graph.paths[service] = new_graph.paths[service]
                graph.paths[service].current_bandwidth = current_bw ######## this is currently necessary, but why?
                change_loss(service, new_graph.paths[service].drop)
                change_latency(service, new_graph.paths[service].latency, new_graph.paths[service].jitter)
