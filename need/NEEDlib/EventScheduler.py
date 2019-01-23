from need.NEEDlib.utils import start_experiment, stop_experiment, crash_experiment, message
from need.NEEDlib.PathEmulation import disconnect, reconnect, change_latency, change_loss
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


