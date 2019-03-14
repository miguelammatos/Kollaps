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
        self.link_changes = []

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

    #LL
################################################
    def schedule_link_leave(self, time, graph, origin, destination):
#        graphmsg = "Scheduling link leave. Original graph's paths have BWs of:\n"
#        for path in graph.paths.values():
#            if len(path.links) > 0 and isinstance(path.links[-1].destination, NetGraph.Service):
#                graphmsg += "\tto " + path.links[-1].destination.name + ": " + str(path.max_bandwidth) + "\n"
#        message(graphmsg)
################################################
        new_graph = copy(graph)
#        new_graph.paths = copy(graph.paths) #we have to do this separately if we don't want to work within the original graph!
#        new_graph.paths.clear()
#        new_graph.paths_by_id = copy(graph.paths_by_id)
#        new_graph.paths_by_id.clear()
        new_graph.paths = {}
        new_graph.paths_by_id = {}
        new_graph.path_counter = 0
        new_graph.links = copy(graph.links) #Do we need a copy of this?
        new_graph.removed_links = copy(graph.removed_links) #Do we need a copy of this?
        new_graph.removed_bridges = copy(graph.removed_bridges) #Do we need a copy of this?
        for l in new_graph.links:
            if (l.source.name == origin and l.destination.name == destination) or (l.source.name == destination and l.destination.name == origin):
                new_graph.removed_links.append(l)
        for l in new_graph.removed_links:
            new_graph.links.remove(l)
            for node in new_graph.services:
                for nodeinstance in new_graph.services[node]:
                    if l in nodeinstance.links:
                        nodeinstance.links.remove(l)
            for bridge in new_graph.bridges:
                if l in new_graph.bridges[bridge][0].links:
                    new_graph.bridges[bridge][0].links.remove(l)
#            l.flows.clear()

        new_graph.calculate_shortest_paths()

#        message("Original graph's paths:\n------------------------------------------\n" + hex(id(graph.paths)))
#        message(graph.print_paths())
#        message("New graph's paths:\n------------------------------------------\n" + hex(id(new_graph.paths)))
#        message(new_graph.print_paths())

        for service, path in new_graph.paths.items():
            if not service == graph.root and isinstance(service, NetGraph.Service):
                path.calculate_end_to_end_properties()

        message("Link " + origin + "--" + destination + " scheduled to leave at " + str(time))
        self.events.append(Timer(time, change_paths, [graph, new_graph]))
################################################
#        graphmsg_end = "Done scheduling link leave. Original graph's paths have BWs of:\n"
#        for path in graph.paths.values():
#            if len(path.links) > 0 and isinstance(path.links[-1].destination, NetGraph.Service):
#                graphmsg_end += "\tto " + path.links[-1].destination.name + ": " + str(path.max_bandwidth) + "\n"
#        graphmsg_end += "NEW graph's paths have BWs of:\n"
#        for path in new_graph.paths.values():
#            if len(path.links) > 0 and isinstance(path.links[-1].destination, NetGraph.Service):
#                graphmsg_end += "\tto " + path.links[-1].destination.name + ": " + str(path.max_bandwidth) + "\n"
#        message(graphmsg_end)
################################################

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

def change_paths(graph, new_graph):
    msg = ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Changing graph at runtime <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n"
#    msg += "old paths_by_id:\n" + str(graph.paths_by_id) + "\n"
#    for key, path in graph.paths_by_id.items():
#        msg += str(key) + ": " + path.prettyprint()
    graph.paths_by_id = copy(new_graph.paths_by_id)
#    msg += "new paths_by_id:\n" + str(graph.paths_by_id) + "\n"
#    for key, path in graph.paths_by_id.items():
#        msg += str(key) + ": " + path.prettyprint()
    graph.path_counter = new_graph.path_counter
    for service in new_graph.paths:
        current_bw = graph.paths[service].current_bandwidth
        if not service == graph.root and isinstance(service, NetGraph.Service):
#            if not service in graph.paths:
            with graph.paths[service].lock:
                graph.paths[service] = new_graph.paths[service]
                graph.paths[service].current_bandwidth = current_bw ######## this is currently necessary, but why?
#                continue
#            else:
#                original_path = graph.paths[service]
#                new_path = new_graph.paths[service]
#                with original_path.lock:
#                    original_path.jitter = new_path.jitter
#                    original_path.latency = new_path.latency
#                    original_path.drop = new_path.drop
#                    original_path.RTT = new_path.RTT
#                    original_path.max_bandwidth = new_path.max_bandwidth
                change_loss(service, new_graph.paths[service].drop)
                change_latency(service, new_graph.paths[service].latency, new_graph.paths[service].jitter)

    msg += "Updated shortest paths after a link left"#, and these are the new paths:" + "\n"
#    msg += graph.print_paths()
    message(msg)
