
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
        for link in current_graph.links: #used to be: new_graph.links = copy(current_graph.links)
            new_graph.links.append(copy(link)) #shallow copy keeps reference to origin, dest objects, but that's ok
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
        blah = "Recomputed and stored. Current graph = " + str(new_graph) + ", time = " + str(time) + "\nPath changes:\n"
        for graph in self.path_changes:
            blah += str(graph[1]) + ", time = " + str(graph[0]) + "\nPath changes:\n"
        print_message(blah)

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
                print_message("scheduling an update at " + str(self.graph_changes[i][TIME]))
            else:
                print_message("NOT scheduling an update at " + str(self.graph_changes[i][TIME]))
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

        print_message(msg)

        print_message("Bridge " + name + " scheduled to join back at " + str(time))
        self.graph_changes.append((time, [graph, new_graph]))

    #Change the properties of a link that is part of the graph
    def schedule_link_change(self, time, graph, origin, destination, bandwidth, latency, jitter, drop):
        current_graph = self.get_current_graph(graph)
        new_graph = self.initialize_new_graph(current_graph)

#        msg = "-------------------\nbefore link_change:\n-------------------\n"
#        for path in current_graph.paths_by_id.values():
#            p = path.prettyprint()
#            if not p is None:
#                msg += p

        for link in new_graph.links:
            if link.source.name == origin and link.destination.name == destination:
                link.bandwidth_bps = bandwidth if bandwidth >= 0 else link.bandwidth_bps
                link.latency = float(latency) if latency >= 0 else link.latency
                link.jitter = float(jitter) if jitter >= 0 else link.jitter
                link.drop = float(drop) if drop >= 0 else link.drop

        self.recompute_and_store(new_graph, time)

#        msg += "------------------\nafter link_change:\n------------------\n"
#        for path in new_graph.paths_by_id.values():
#            p = path.prettyprint()
#            if not p is None:
#                msg += p

#        print_message(msg)

        print_message("Link " + origin + "--" + destination + " scheduled to change at " + str(time))
        self.graph_changes.append((time, [graph, new_graph]))

#we need these to re-install the original link objects into changed topologies
def get_original_links(original_links, new_links):
        indices = []
        old_links = []
        for link in new_links:
            inorig = False
            for lnk in original_links:
                if lnk.index == link.index:
                    indices.append(link.index)
                    inorig = True
            if not inorig: #a new link has joined in this event
                old_links.append(link)
        for index in indices:
            for lnk in original_links:
                if lnk.index == index:
                    for link in new_links:
                        if link.index == index:
                            lnk.bandwidth_bps = link.bandwidth_bps
                            lnk.latency = link.latency
                            lnk.jitter = link.jitter
                            lnk.drop = link.drop
                            lnk.flows = link.flows
                            lnk.last_flows_count = link.last_flows_count
                    old_links.append(lnk)

        return old_links

#As it is currently, it does not work if we just set graph = new_graph.
#Therefore, we copy all the relevant attributes over.
#services and hosts_by_ip never change, so we don't copy these at the moment.
def path_change(graphs):
    graph = graphs[0]
    new_graph = graphs[1]
    start = time()
    try:
        #paths_by_id
        for path in new_graph.paths_by_id.values():
            original_path_links = get_original_links(graph.links + graph.removed_links, path.links)
            path.links = original_path_links
        graph.paths_by_id = new_graph.paths_by_id
        #bridges
        for bridge in new_graph.bridges.values():
            original_bridge_links = get_original_links({**graph.bridges, **graph.removed_bridges}, bridge[0].links)
            bridge[0].links = original_bridge_links
        graph.bridges = new_graph.bridges
        #links
        original_links = get_original_links(graph.links + graph.removed_links, new_graph.links)
        new_graph.links = original_links
        graph.links = new_graph.links

        graph.link_counter = new_graph.link_counter
        graph.path_counter = new_graph.path_counter
        graph.removed_links = new_graph.removed_links
        graph.removed_bridges = new_graph.removed_bridges
        graph.networks = new_graph.networks

        #paths
        for service in new_graph.paths:
            if service in graph.paths:
                current_bw = graph.paths[service].current_bandwidth
                if not service == graph.root and isinstance(service, NetGraph.Service):
                    with graph.paths[service].lock:
                        original_path_links = get_original_links(graph.links + graph.removed_links, new_graph.paths[service].links)
                        new_graph.paths[service].links = original_path_links
                        graph.paths[service] = new_graph.paths[service]
                        graph.paths[service].current_bandwidth = current_bw #the new paths have the clean maximum computed. Here we need the bookkeeping of the old path.
                        change_loss(service, new_graph.paths[service].drop)
                        change_latency(service, new_graph.paths[service].latency, new_graph.paths[service].jitter)
            else: # service is now reachable after not having been reachable
                if isinstance(service, NetGraph.Service):
                    original_path_links = get_original_links(graph.links + graph.removed_links, new_graph.paths[service].links)
                    new_graph.paths[service].links = original_path_links
                    graph.paths[service] = new_graph.paths[service]
                    graph.paths[service].current_bandwidth = 0
                    change_loss(service, new_graph.paths[service].drop)
                    change_latency(service, new_graph.paths[service].latency, new_graph.paths[service].jitter)

        to_remove = []
        #is a service not reachable after this change? Then set packet loss to 100%
        for service in graph.paths:
            if isinstance(service, NetGraph.Service) and not service in new_graph.paths:
                to_remove.append(service)
                change_loss(service, 1.0)
        for service in to_remove:
            del graph.paths[service]

    except Exception as e:
        print_message(e)
    end = time()
    print_message("recalculated in " + str(end - start))
