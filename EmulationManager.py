from time import time, sleep
from threading import Lock

from NetGraph import NetGraph
import PathEmulation
from FlowDisseminator import FlowDisseminator

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List

class EmulationManager:

    ERROR_MARGIN = 0.01  # in percent
    POOL_PERIOD = 0.05 # in seconds

    def __init__(self, graph):
        self.graph = graph  # type: NetGraph
        self.active_links = {}  # type: Dict[int, NetGraph.Link]
        self.active_paths = []
        self.disseminator = FlowDisseminator(self, self.collect_flow)
        self.state_lock = Lock()

    def emulation_loop(self):
        last_time = time()
        while True:
            with self.state_lock:
                self.reset_flow_state()
                last_time = self.check_active_flows(last_time)
            self.disseminate_active_flows()
            sleep(EmulationManager.POOL_PERIOD)
            with self.state_lock:
                self.recalculate_path_bandwidths()

    def reset_flow_state(self):
        for link_index in self.active_links:
            link = self.active_links[link_index]
            link.used_bandwidth_Kbps = 0
            del link.flows[:]

        self.active_links.clear()
        del self.active_paths[:]

    def check_active_flows(self, last_time):
        PathEmulation.update_usage()
        current_time = time()
        time_delta = current_time - last_time
        for service in self.graph.services:
            hosts = self.graph.services[service]
            for host in hosts:
                if host == self.graph.root:
                    continue
                # Calculate current throughput
                bytes = PathEmulation.query_usage(host)
                if bytes < host.last_bytes:
                    bytes_delta = bytes  # in case of overflow ignore the bytes before the overflow
                else:
                    bytes_delta = bytes - host.last_bytes
                kbits = (bytes_delta / 1000) * 8
                throughput = kbits / time_delta
                host.last_bytes = bytes

                # Get the network path
                path = self.graph.paths[host]

                # Check if this is an active flow
                if throughput <= (path.max_bandwidth * EmulationManager.ERROR_MARGIN):
                    path.used_bandwidth = 0
                    continue

                # This is an active flow
                path.used_bandwidth = throughput
                self.active_paths.append(path)
                for link in path.links:
                    self.active_links[link.index] = link
                    link.used_bandwidth_Kbps += throughput
                    link.flows.append(path)
        return current_time

    def disseminate_active_flows(self):
        self.disseminator.broadcast_flows(self.active_paths)

    def recalculate_path_bandwidths(self):
        for path in self.active_paths:
            for link in path.links:
                if link.used_bandwidth_Kbps > link.bandwidth_Kbps:
                    print("CONGESTION!!")

    def collect_flow(self, bandwidth, link_indices):
        with self.state_lock:
            rtt = 0
            for index in link_indices:
                if index in self.active_links:
                    link = self.active_links[index]
                    link.used_bandwidth_Kbps += bandwidth
                    link.flows += 1
                    rtt += link.latency*2
