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
        paths = []
        new_paths = []
        for l in graph.links:
            if l.source.name == origin and l.destination.name == destination:
                links.append(l)

        for key in graph.paths:
            if not isinstance(key, NetGraph.Service): # If we get a path to a bridge, ignore
                continue
            path = graph.paths[key]
            for link in links:
                for i, l in enumerate(path.links):
                    if l.index == link.index:
                        paths.append(path)  # There wont be duplicated paths since there cant be multiple changed links
                        new_path = copy(path) # in the same path (replicated links must be on different paths)

                        # Pre-compute the path properties
                        new_path.links = copy(path.links)
                        new_path.links[i] = copy(l)

                        new_l = new_path.links[i]
                        new_l.bandwidth_bps = bandwidth if bandwidth >= 0 else new_l.bandwidth_bps
                        new_l.latency = int(latency) if latency >= 0 else new_l.latency
                        new_l.jitter = float(jitter) if jitter >= 0 else new_l.jitter
                        new_l.drop = float(drop) if drop >= 0 else new_l.drop
                        new_path.calculate_end_to_end_properties()
                        new_paths.append(new_path)
                        break


        for link in links:
            message("Link " + link.source.name + ":" + link.destination.name + " scheduled to change at " + str(time) + " bw" + str(bandwidth))
        for path in paths:
            message("Path to" + path.links[-1].destination.name + " scheduled to change at " + str(time))

        self.events.append(Timer(time, link_change,
                                 [links, paths, new_paths, bandwidth, latency, jitter, drop]))


def link_change(links, paths, new_paths, bandwidth_bps, latency, jitter, drop):
    for l in links:
        with l.lock:
            l.bandwidth_bps = bandwidth_bps if bandwidth_bps >= 0 else l.bandwidth_bps
            l.latency = int(latency) if latency >= 0 else l.latency
            l.jitter = float(jitter) if jitter >= 0 else l.jitter
            l.drop = float(drop) if drop >= 0 else l.drop

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
            # We dont explicitely change bandwidth, the emulation manager will handle that for us

            '''
            message("Path " + path.links[0].source.name + " to " + path.links[-1].destination.name +
                    " changed to bw:" + str(path.max_bandwidth) + " rtt:"+str(path.RTT)
                    + " j:" + str(path.jitter) + " l:" + str(path.drop))
            '''


