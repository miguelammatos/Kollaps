from time import time, sleep
from threading import Lock, Timer, active_count

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
        self.repeat_detection = {}
        self.state_lock = Lock()
        self.disseminator = FlowDisseminator(self, self.collect_flow, self.graph)
        self.last_time = 0

    def initialize(self):
        PathEmulation.init(FlowDisseminator.UDP_PORT)
        for service in self.graph.paths:
            if isinstance(service, NetGraph.Service):
                path = self.graph.paths[service]
                PathEmulation.initialize_path(path)


    def emulation_loop(self):
        self.last_time = time()
        self.check_active_flows()  # to prevent bug where data has already passed through the filters before
        while True:
            with self.state_lock:
                self.recalculate_path_bandwidths()
                self.reset_flow_state()
                self.check_active_flows()
            self.disseminator.broadcast_flows(self.active_paths)
            sleep(EmulationManager.POOL_PERIOD)


    def reset_flow_state(self):
        for link_index in self.active_links:
            link = self.active_links[link_index]
            del link.flows[:]

        self.active_links.clear()
        del self.active_paths[:]
        self.repeat_detection.clear()

    def check_active_flows(self):
        PathEmulation.update_usage()
        current_time = time()
        time_delta = current_time - self.last_time
        for service in self.graph.services:
            hosts = self.graph.services[service]
            for host in hosts:
                if host == self.graph.root:
                    continue
                if host not in self.graph.paths:  # unreachable
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
                    link.flows.append((path.RTT, throughput))
        self.last_time = current_time


    def recalculate_path_bandwidths(self):
        RTT = 0
        BW = 1
        for path in self.active_paths:
            max_bandwidth = path.max_bandwidth
            for link in path.links:
                used_bandwidth = 0
                rtt_reverse_sum = 0
                for flow in link.flows:
                    used_bandwidth += flow[BW]
                    rtt_reverse_sum += (1.0/flow[RTT])
                max_bandwidth_on_link = []
                # calculate the bandwidth for everyone
                for flow in link.flows:
                    max_bandwidth_on_link.append(((1.0/flow[RTT])/rtt_reverse_sum)*link.bandwidth_Kbps)

                # Maximize link utilization to 100%
                spare_bw = link.bandwidth_Kbps - max_bandwidth_on_link[0]
                our_share = max_bandwidth_on_link[0]/link.bandwidth_Kbps
                hungry_usage_sum = our_share
                for i, flow in enumerate(link.flows[1:]):
                    # Check if a flow is "hungry" (wants more than its allocated share)
                    if flow[BW] > max_bandwidth_on_link[i]:
                        spare_bw -= max_bandwidth_on_link[i]
                        hungry_usage_sum += max_bandwidth_on_link[i]/link.bandwidth_Kbps
                    else:
                        spare_bw -= flow[BW]

                normalized_share = our_share/hungry_usage_sum  # we get a share of the spare proportional to our RTT
                max_bandwidth_on_link[0] += (normalized_share*spare_bw)

                # If this link restricts us more than previously assume this bandwidth as the max
                if max_bandwidth_on_link[0] < max_bandwidth:
                    max_bandwidth = max_bandwidth_on_link[0]

            # Apply the new bandwidth on this path
            if max_bandwidth <= path.max_bandwidth and max_bandwidth != path.current_bandwidth:
                PathEmulation.change_bandwidth(path.links[-1].destination, max_bandwidth)
                path.current_bandwidth = max_bandwidth

    def collect_flow(self, bandwidth, link_indices):
        key = str(link_indices[0]) + str(link_indices[-1])
        with self.state_lock:
            if key in self.repeat_detection:
                return
            else:
                self.repeat_detection[key] = True
            concurrent_links = []
            # Calculate RTT of this flow and check if we are sharing any link with it
            rtt = 0
            for index in link_indices:
                link = self.graph.links[index]
                rtt += (link.latency*2)
                if index in self.active_links:
                    concurrent_links.append(link)

            # If we are sharing links, then update them with this flows bandwidth usage and RTT
            if len(concurrent_links) > 0:
                for link in concurrent_links:
                    link.flows.append((rtt, bandwidth))
