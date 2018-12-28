from need.NEEDlib.utils import start_experiment, stop_experiment, crash_experiment
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
            if l.source == origin and l.destination == destination:
                links.append(l)

        for path in graph.paths:
            for link in links:
                for l in path.links:
                    if l == link:
                        paths.append(path)  # There wont be duplicated paths since there cant be multiple changed links
                        break               # in the same path (replicated links must be on different paths)

        self.events.append(Timer(time, link_change,
                                 [links, paths, graph.bandwidth_in_bps(bandwidth), latency, jitter, drop]))


def link_change(links, paths, bandwidth_bps, latency, jitter, drop):
    for l in links:
        with l.lock:
            l.bandwidth_bps = bandwidth_bps
            l.latency = int(latency)
            l.jitter = float(jitter)
            l.drop = float(drop)

    for path in paths:
        with path.lock:
            path.calculate_end_to_end_properties()

            service = path.links[-1].destination
            change_loss(service, path.drop)
            change_latency(service, path.latency, path.jitter)
            # We dont explicitely change bandwidth, the emulation manager will handle that for us


