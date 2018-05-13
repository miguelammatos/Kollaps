from time import time, sleep
from threading import Lock
from itertools import islice

from NEED.NetGraph import NetGraph
import NEED.PathEmulation as PathEmulation
from NEED.CommunicationsManager import CommunicationsManager

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List, Tuple


class EmulationManager:

    # Generic loop tuning
    ERROR_MARGIN = 0.01  # in percent
    POOL_PERIOD = 0.05 # in seconds
    ITERATIONS_TO_INTEGRATE = 2

    # Exponential weighted moving average tuning
    ALPHA = 0.25
    ONE_MINUS_ALPHA = 1-ALPHA

    def __init__(self, graph):
        self.graph = graph  # type: NetGraph
        self.active_links = {}  # type: Dict[int, NetGraph.Link]
        self.active_paths = []  # type: List[NetGraph.Path]
        self.flow_accumulator = {}  # type: Dict[str, List[List[int], int, int]]
        self.concurrent_flows_keys = []
        self.state_lock = Lock()
        self.comms = CommunicationsManager(self.collect_flow, self.graph)
        self.last_time = 0

    def initialize(self):
        PathEmulation.init(CommunicationsManager.UDP_PORT)
        for service in self.graph.paths:
            if isinstance(service, NetGraph.Service):
                path = self.graph.paths[service]
                PathEmulation.initialize_path(path)


    def emulation_loop(self):
        self.last_time = time()
        self.check_active_flows()  # to prevent bug where data has already passed through the filters before
        while True:
            for i in range(EmulationManager.ITERATIONS_TO_INTEGRATE):
                with self.state_lock:
                    self.active_links.clear()
                    self.active_paths.clear()
                    self.check_active_flows()
                self.comms.broadcast_flows(self.active_paths)
                sleep(EmulationManager.POOL_PERIOD)
            with self.state_lock:
                for key in self.concurrent_flows_keys:
                    self.add_flow(key)
                self.recalculate_path_bandwidths()
                self.concurrent_flows_keys.clear()
                self.flow_accumulator.clear()
                for link_index in self.active_links:
                    self.active_links[link_index].flows.clear()

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
                link_indices = []
                for link in path.links:
                    self.active_links[link.index] = link
                    link_indices.append(link.index)

                # Collect our own flow
                self.accumulate_flow(throughput, link_indices)

        self.last_time = current_time


    def recalculate_path_bandwidths(self):
        RTT = 0
        BW = 1
        for path in self.active_paths:
            max_bandwidth = path.max_bandwidth
            for link in path.links:
                rtt_reverse_sum = 0
                for flow in link.flows:
                    rtt_reverse_sum += (1.0/flow[RTT])
                max_bandwidth_on_link = []
                # calculate the bandwidth for everyone
                for flow in link.flows:
                    max_bandwidth_on_link.append(((1.0/flow[RTT])/rtt_reverse_sum)*link.bandwidth_Kbps)

                # Maximize link utilization to 100%
                spare_bw = link.bandwidth_Kbps - max_bandwidth_on_link[0]
                our_share = max_bandwidth_on_link[0]/link.bandwidth_Kbps
                hungry_usage_sum = our_share  # We must be out of the loop to avoid division by zero
                for i, flow in islice(enumerate(link.flows), 1, None):
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
                if max_bandwidth <= path.current_bandwidth:
                    path.current_bandwidth = max_bandwidth  # if its less then we now for sure it is correct
                else:
                    #  if it is more then we have to be careful, it might be a spike due to lost metadata
                    path.current_bandwidth = EmulationManager.ONE_MINUS_ALPHA* path.current_bandwidth + \
                                             EmulationManager.ALPHA * max_bandwidth
                PathEmulation.change_bandwidth(path.links[-1].destination, path.current_bandwidth)

    def add_flow(self, key):
        """
        This method grabs an accumulated flow, and adds the corresponding information to the active links
        :param bandwidth: int
        :param link_indices: List[int]
        """
        INDICES = 0
        BW = 1
        COUNTER = 2

        flow = self.flow_accumulator[key]
        link_indices = flow[INDICES]
        bandwidth = flow[BW] #/flow[COUNTER]

        concurrent_links = []
        # Calculate RTT of this flow and check if we are sharing any link with it
        rtt = 0
        for index in link_indices:
            link = self.graph.links[index]
            rtt += (link.latency*2)
            if index in self.active_links:
                concurrent_links.append(link)
        for link in concurrent_links:
            link.flows.append((rtt, bandwidth))

    def accumulate_flow(self, bandwidth, link_indices):
        """
        This method adds a flow to the accumulator (Note: it doesnt grab the lock)
        :param bandwidth: int
        :param link_indices: List[int]
        """
        INDICES = 0
        BW = 1
        COUNTER = 2
        key = str(link_indices[0]) + ":" + str(link_indices[-1])
        if key in self.flow_accumulator:
            flow = self.flow_accumulator[key]
            flow[BW] = bandwidth
            # flow[COUNTER] += 1
        else:
            self.flow_accumulator[key] = [link_indices, bandwidth, 1]
            self.concurrent_flows_keys.append(key)

    def collect_flow(self, bandwidth, link_indices):
        """
        This method collects a flow from other nodes, it checks if it is interesting and if so calls accumulate_flow
        :param bandwidth: int
        :param link_indices: List[int]
        :return: Whether or not the packet is useful (not duplicated) deprecated!
        """
        # TODO the return value is no longer useful

        # Check if this flow is interesting to us
        with self.state_lock:
            concurrent = False
            for i in link_indices:
                concurrent = (concurrent or (i in self.active_links))
            if concurrent:
                self.accumulate_flow(bandwidth, link_indices)
        return True
