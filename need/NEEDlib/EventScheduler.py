from need.NEEDlib.utils import start_experiment, stop_experiment, crash_experiment, message
from need.NEEDlib.PathEmulation import disconnect, reconnect, change_latency, change_loss
from need.NEEDlib.NetGraph import NetGraph

from threading import Timer

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
        for l in graph.links:
            if l.source.name == origin and l.destination.name == destination:
                links.append(l)

        for key in graph.paths:
            if not isinstance(key, NetGraph.Service): # If we get a path to a bridge, ignore
                continue
            path = graph.paths[key]
            for link in links:
                for l in path.links:
                    if l == link:
                        paths.append(path)  # There wont be duplicated paths since there cant be multiple changed links
                        break               # in the same path (replicated links must be on different paths)

        for link in links:
            message("Link " + link.source.name + ":" + link.destination.name + " scheduled to change at " + str(time) + " bw" + str(bandwidth))
        for path in paths:
            message("Path to" + path.links[-1].destination.name + " scheduled to change at " + str(time))

        self.events.append(Timer(time, link_change,
                                 [links, paths, bandwidth, latency, jitter, drop]))


def link_change(links, paths, bandwidth_bps, latency, jitter, drop):
    for l in links:
        with l.lock:
            l.bandwidth_bps = bandwidth_bps if bandwidth_bps >= 0 else l.bandwidth_bps
            l.latency = int(latency) if latency >= 0 else l.latency
            l.jitter = float(jitter) if jitter >= 0 else l.jitter
            l.drop = float(drop) if drop >= 0 else l.drop

    for path in paths:
        with path.lock:
            path.calculate_end_to_end_properties()

            service = path.links[-1].destination
            change_loss(service, path.drop)
            change_latency(service, path.latency, path.jitter)
            # We dont explicitely change bandwidth, the emulation manager will handle that for us


