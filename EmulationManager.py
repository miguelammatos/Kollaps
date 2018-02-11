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
        def cycle():
            Timer(EmulationManager.POOL_PERIOD, cycle).start()
            self.disseminator.broadcast_flows(self.active_paths)
            with self.state_lock:
                self.recalculate_path_bandwidths()
                self.reset_flow_state()
                self.check_active_flows()

        cycle()

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
                for flow in link.flows:
                    used_bandwidth += flow[BW]
                if used_bandwidth > link.bandwidth_Kbps:  # We have congestion: apply RTT-aware Min-Max model
                    rtt_reverse_sum = 0
                    for flow in link.flows:
                        rtt_reverse_sum += (1.0/flow[RTT])
                    max_bandwidth_on_link = []
                    our_share = (1.0/path.RTT)/rtt_reverse_sum
                    # calculate the bandwidth for everyone
                    for flow in link.flows:
                        max_bandwidth_on_link.append(((1.0/flow[RTT])/rtt_reverse_sum)*link.bandwidth_Kbps)

                    # Maximize link utilization to 100%
                    # TODO Experimentally verify this is correct (impossible to verify with offline mocks)
                    # This is not complete on a single cycle, there can still be wastage (but never exceed 100%)
                    # but it should converge to 100% usage over 2 distributed cycles
                    # as the other nodes calculate their share and apply it.
                    # Example:
                    # Node1 receives extra spare bw on Link1
                    # Node1 is however further restricted by Link2 and doesnt use the extra spare bw
                    # Node2 takes into consideration Node1's extra spare bw on Link1
                    # Utilization should converge on the next cycle when Node1 broadcasts its bw restricted by Link2
                    # Note: this is a greedy approach, the non-greedy approach would require full knowledge of the
                    #       entire network state since right now Node2 might not have Link2 in its active paths,
                    #       and therefore cant consider it
                    spare_bw = 1.0
                    max_usage_sum = 0  # this is used later for normalization
                    using_less_than_allocated = True if max_bandwidth_on_link[0] > link.flows[0][BW] else False
                    for i, flow in enumerate(link.flows):
                        if(max_bandwidth_on_link[i] > flow[BW]):  # this flow got allocated more than what is using
                            max_bandwidth_on_link[i] = flow[BW]
                        else:
                            # add together all shares that are competing for more than their fair share
                            max_usage_sum += max_bandwidth_on_link[i]/link.bandwidth_Kbps
                        spare_bw -= max_bandwidth_on_link[i]/link.bandwidth_Kbps  # decrement by this flows share

                    # If we are competing for more than our share try to get some spare bw
                    if not using_less_than_allocated:
                        # normalize our usage
                        normalized = our_share/max_usage_sum
                        our_share += normalized*spare_bw  # allocate extra bw according to our weight
                        max_bandwidth_on_link[0] = our_share*link.bandwidth_Kbps

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
