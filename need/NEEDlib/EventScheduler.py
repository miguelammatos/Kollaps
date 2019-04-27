
from need.NEEDlib.utils import start_experiment, stop_experiment, crash_experiment, print_message
from need.NEEDlib.PathEmulation import disconnect, reconnect, change_latency, change_loss
from need.NEEDlib.NetGraph import NetGraph

from threading import Timer
from copy import copy
from time import time

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List


class EventScheduler:
    def __init__(self):
        self.events = []  # type: List[Timer]
        self.link_changes = [] # type: List[(float, NetGraph.Link)]
        self.path_changes = [] # type: List[(float, NetGraph)]
        self.graph_changes = [] # type: List[(float, List[NetGraph, NetGraph])]

    def start(self):
        for e in self.events:
            e.start()

    def get_current_graph(self, graph):
        if len(self.path_changes) == 0:
            current_graph = graph
        else:
            current_graph = self.path_changes[0][1] #work from the last change onwards
        return current_graph

    #replaces old link objects with new ones
    def replace_link_objects(self, nodes, links):
        for service in nodes:
            for instance in service:
                indices = []
                new_links = []
                for link in instance.links:
                    indices.append(link.index)
                for index in indices:
                    for lnk in links:
                        if lnk.index == index:
                            new_links.append(lnk)
                instance.links = new_links

    def initialize_new_graph(self, current_graph):
        new_graph = copy(current_graph)
        new_graph.paths = {}
        new_graph.paths_by_id = {}
        new_graph.path_counter = 0
        new_graph.removed_links = copy(current_graph.removed_links)
        new_graph.removed_bridges = copy(current_graph.removed_bridges)
        new_graph.links = []
        new_graph.links_by_index = {}
        for link in current_graph.links: #used to be: new_graph.links = copy(current_graph.links)
            linkcopy = copy(link) #shallow copy keeps reference to origin, dest objects, but that's ok
            new_graph.links.append(linkcopy)
            new_graph.links_by_index[link.index] = linkcopy
        for rlink in new_graph.removed_links:
            new_graph.links_by_index[rlink.index] = rlink
        self.replace_link_objects(new_graph.services.values(), new_graph.links)
        self.replace_link_objects(new_graph.bridges.values(), new_graph.links)
        return new_graph

    def recompute_and_store(self, new_graph, time):
        new_graph.calculate_shortest_paths()

        for service, path in new_graph.paths.items():
            if not service == new_graph.root and isinstance(service, NetGraph.Service):
                path.calculate_end_to_end_properties()

        self.path_changes.insert(0, (time, new_graph))
        self.path_changes.sort(reverse=True, key=lambda change: change[0])

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

    #if multiple events happen at the same time, it is enough to only
    #actually execute the last change happening at that time, because
    #it is computed on top of all the others.
    def schedule_graph_changes(self):
        TIME = 0
        GRAPHS = 1
        for i in range(len(self.graph_changes)):
            if i == len(self.graph_changes)-1 or self.graph_changes[i][TIME] < self.graph_changes[i+1][TIME]:
                self.events.append(Timer(self.graph_changes[i][TIME], path_change, [self.graph_changes[i][GRAPHS]]))
            else:
                pass

    #Remove a link that is currently part of the graph
    def schedule_link_leave(self, time, graph, origin, destination):
        current_graph = self.get_current_graph(graph)
        new_graph = self.initialize_new_graph(current_graph)

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

        self.recompute_and_store(new_graph, time)

        print_message("Link " + origin + "--" + destination + " scheduled to leave at " + str(time))
        self.graph_changes.append((time, [graph, new_graph]))

    #Add back a link that has been removed before
    def schedule_link_join(self, time, graph, origin, destination):
        current_graph = self.get_current_graph(graph)
        new_graph = self.initialize_new_graph(current_graph)

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

        self.recompute_and_store(new_graph, time)

        print_message("Link " + origin + "--" + destination + " scheduled to join at " + str(time))
        self.graph_changes.append((time, [graph, new_graph]))


    #Add a completely new link
    def schedule_new_link(self, time, graph, source, destination, latency, jitter, drop, bandwidth, network):
        current_graph = self.get_current_graph(graph)
        new_graph = self.initialize_new_graph(current_graph)

        new_graph.new_link(source, destination, latency, jitter, drop, bandwidth, network)

        self.recompute_and_store(new_graph, time)

        print_message("Link " + source + "--" + destination + " scheduled to newly join at " + str(time))
        self.graph_changes.append((time, [graph, new_graph]))

    #Remove a bridge that is currently part of the graph
    def schedule_bridge_leave(self, time, graph, name):
        current_graph = self.get_current_graph(graph)
        new_graph = self.initialize_new_graph(current_graph)

        #hack to still find the bridge in XMLGraphParser at startup time
        #it doesn't matter to have it there, because it will be overwritten by dynamic changes at runtime
        graph.removed_bridges[name] = new_graph.bridges[name]

        new_graph.removed_bridges[name] = new_graph.bridges[name]
        del new_graph.bridges[name]

        self.recompute_and_store(new_graph, time)

        print_message("Bridge " + name + " scheduled to leave at " + str(time))
        self.graph_changes.append((time, [graph, new_graph]))

    #Add back a bridge that has been removed before
    def schedule_bridge_join(self, time, graph, name):
        current_graph = self.get_current_graph(graph)
        new_graph = self.initialize_new_graph(current_graph)

        bridge = new_graph.removed_bridges[name]
        del new_graph.removed_bridges[name]
        new_graph.bridges[name] = bridge

        self.recompute_and_store(new_graph, time)

        print_message("Bridge " + name + " scheduled to join back at " + str(time))
        self.graph_changes.append((time, [graph, new_graph]))

    #Change the properties of a link that is part of the graph
    def schedule_link_change(self, time, graph, origin, destination, bandwidth, latency, jitter, drop):
        current_graph = self.get_current_graph(graph)
        new_graph = self.initialize_new_graph(current_graph)

        for link in new_graph.links:
            if link.source.name == origin and link.destination.name == destination:
                link.bandwidth_bps = bandwidth if bandwidth >= 0 else link.bandwidth_bps
                link.latency = float(latency) if latency >= 0 else link.latency
                link.jitter = float(jitter) if jitter >= 0 else link.jitter
                link.drop = float(drop) if drop >= 0 else link.drop

        self.recompute_and_store(new_graph, time)

        print_message("Link " + origin + "--" + destination + " scheduled to change at " + str(time))
        self.graph_changes.append((time, [graph, new_graph]))

def new_links_by_index(new, old):
    new_by_index = {}
    for index in new:
        if index in old:
            l = new[index]
            l.flows = old[index].flows
            l.last_flows_count = old[index].last_flows_count
            new_by_index[index] = l
        else:
            new_by_index[index] = new[index]
    return new_by_index

#We cannot simply set graph = new_graph, because we have references to new_graph in other places.
#It is important to note that we DO NOT update all properties of the graph, only those necessary for the emulation at runtime.
#I.e. we do not update bridges, or the links of bridges. We also do not update graph.links, as the emulation rather uses graph.paths_by_id.
#Other properties, such as services and hosts_by_ip, never change, so we don't update these either.
def path_change(graphs):
    start = time()
    graph = graphs[0]
    new_graph = graphs[1]
    try:
        #is a service not reachable after this change? Then set packet loss to 100%
        to_remove = []
        for service in graph.paths:
            if not service in new_graph.paths and isinstance(service, NetGraph.Service):
                to_remove.append(service)
                change_loss(service, 1.0)
        for service in to_remove:
            del graph.paths[service]

        graph.links_by_index = new_links_by_index(new_graph.links_by_index, graph.links_by_index) #update necessary??

        #apply paths that do exist now and *were* already in the last graph...
        new_paths_by_id = {}
        for service in new_graph.paths:
            if service in graph.paths:
                if isinstance(service, NetGraph.Service) and not service == graph.root:
                    current_bw = graph.paths[service].current_bandwidth
                    new_path = new_graph.paths[service]
                    with graph.paths[service].lock:
                        new_path.links = [graph.links_by_index[link.index] for link in new_path.links]
                        graph.paths[service] = new_path
                        graph.paths[service].current_bandwidth = current_bw #the new paths have the clean maximum computed. Here we need the bookkeeping of the old path.
                        change_loss(service, graph.paths[service].drop)
                        change_latency(service, graph.paths[service].latency, graph.paths[service].jitter)
                    new_paths_by_id[new_path.id] = new_path
            #... or not
            else: # service is now reachable after not having been reachable
                if isinstance(service, NetGraph.Service):
                    with graph.paths[service].lock:
                        graph.paths[service] = new_graph.paths[service]
                        graph.paths[service].links = update_links([link.index for link in graph.paths[service].links], graph.links_by_index)
                        graph.paths[service].current_bandwidth = 0
                        change_loss(service, graph.paths[service].drop)
                        change_latency(service, graph.paths[service].latency, graph.paths[service].jitter)
                    new_paths_by_id[new_path.id] = new_path
        graph.paths_by_id = new_paths_by_id
        graph.links_by_index = new_graph.links_by_index #update necessary??
    except Exception as e:
        print_message("Error updating paths: " + str(e))
    end = time()
    print_message("recalculated in " + '{p:.4f}'.format(p=end - start))
