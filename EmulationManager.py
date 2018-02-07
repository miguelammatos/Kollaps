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
        self.state_lock = Lock()
        self.disseminator = FlowDisseminator(self, self.collect_flow)

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
                    link.flows.append((path.RTT, throughput))
        return current_time

    def disseminate_active_flows(self):
        self.disseminator.broadcast_flows(self.active_paths)

    def recalculate_path_bandwidths(self):
        RTT = 0
        BW = 1
        for path in self.active_paths:
            max_bandwidth = path.max_bandwidth
            for link in path.links:
                used_bandwidth = 0
                for flow in link.flows:
                    used_bandwidth += flow[BW]
                if used_bandwidth > link.bandwidth_Kbps:  # We have congestion apply RTT-aware Min-Max model
                    rtt_reverse_sum = 0
                    for flow in link.flows:
                        rtt_reverse_sum += (1.0/flow[RTT])
                    max_bandwidth_on_link = []
                    our_share = (1.0/path.RTT)/rtt_reverse_sum
                    # calculate the bandwidth for the everyone
                    for flow in link.flows:
                        max_bandwidth_on_link.append(((1.0/flow[RTT])/rtt_reverse_sum)*link.bandwidth_Kbps)


                    # Maximize link utilization to 100%
                    # TODO Experimentally verify this is correct (impossible to verify with offline mocks)
                    # This is not complete on a single cycle, there can still be wastage (but never exceed 100%)
                    # but it should converge to 100% usage over 2 distributed cycles
                    # as the other nodes calculate their share and apply it
                    spare_bw = 1.0
                    max_usage_sum = 0  # this is used later for normalization
                    using_less_than_allocated = True if max_bandwidth_on_link[0] > link.flows[0][BW] else False
                    for i, flow in enumerate(link.flows):
                        if(max_bandwidth_on_link[i] > flow[BW]):
                            max_bandwidth_on_link[i] = flow[BW]
                        else:
                            # add together all shares that are competing for more than their fair share
                            max_usage_sum += max_bandwidth_on_link[i]/link.bandwidth_Kbps
                        spare_bw -= max_bandwidth_on_link[i]/link.bandwidth_Kbps

                    #If we are competing for more than our share try to get some spare bw
                    if not using_less_than_allocated:
                        # normalize our usage
                        normalized = our_share/max_usage_sum
                        our_share += normalized*spare_bw
                        max_bandwidth_on_link[0] = our_share*link.bandwidth_Kbps

                    if max_bandwidth_on_link[0] < max_bandwidth:
                        max_bandwidth = max_bandwidth_on_link[0]

            # Apply the new bandwidth on this path
            if max_bandwidth <= path.max_bandwidth and max_bandwidth != path.current_bandwidth:
                PathEmulation.change_bandwidth(path.links[-1].destination, max_bandwidth)
                path.current_bandwidth = max_bandwidth

    def collect_flow(self, bandwidth, link_indices):
        with self.state_lock:
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

