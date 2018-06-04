from time import time, sleep
from threading import Lock
from itertools import islice
from os import environ

from NEED.NetGraph import NetGraph
import NEED.PathEmulation as PathEmulation
from NEED.CommunicationsManager import CommunicationsManager
from NEED.utils import ENVIRONMENT

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
        EmulationManager.POOL_PERIOD = float(environ.get(ENVIRONMENT.POOL_PERIOD, str(EmulationManager.POOL_PERIOD)))
        print("Pool Period: " + str(EmulationManager.POOL_PERIOD))

    def initialize(self):
        PathEmulation.init(CommunicationsManager.UDP_PORT)
        for service in self.graph.paths:
            if isinstance(service, NetGraph.Service):
                path = self.graph.paths[service]
                PathEmulation.initialize_path(path)


    def emulation_loop(self):
        self.last_time = time()
        self.check_active_flows()  # to prevent bug where data has already passed through the filters before
        starttime = time()
        while True:
            for i in range(EmulationManager.ITERATIONS_TO_INTEGRATE):
                with self.state_lock:
                    self.active_links.clear()
                    self.active_paths.clear()
                    self.check_active_flows()
                self.comms.broadcast_flows(self.active_paths)
                sleep_time = EmulationManager.POOL_PERIOD - ((time() - starttime) % EmulationManager.POOL_PERIOD)
                sleep(sleep_time)
            with self.state_lock:
                for key in self.concurrent_flows_keys:
                    self.add_flow(key)
                self.recalculate_path_bandwidths()
                self.concurrent_flows_keys.clear()
                self.flow_accumulator.clear()
                for link_index in self.active_links:
                    self.active_links[link_index].last_flows_count = len(self.active_links[link_index].flows)
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
                bits = (bytes_delta) * 8
                throughput = bits / time_delta
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
                # calculate our bandwidth
                max_bandwidth_on_link.append(((1.0/link.flows[0][RTT])/rtt_reverse_sum)*link.bandwidth_bps)
                spare_bw = link.bandwidth_bps - max_bandwidth_on_link[0]
                our_share = max_bandwidth_on_link[0]/link.bandwidth_bps
                hungry_usage_sum = our_share  # We must be out of the loop to avoid division by zero
                for i in range(1, len(link.flows)):
                    flow = link.flows[i]
                    # calculate the bandwidth for everyone
                    max_bandwidth_on_link.append(((1.0/flow[RTT])/rtt_reverse_sum)*link.bandwidth_bps)

                    # Maximize link utilization to 100%
                    # Check if a flow is "hungry" (wants more than its allocated share)
                    if flow[BW] > max_bandwidth_on_link[i]:
                        spare_bw -= max_bandwidth_on_link[i]
                        hungry_usage_sum += max_bandwidth_on_link[i]/link.bandwidth_bps
                    else:
                        spare_bw -= flow[BW]

                normalized_share = our_share/hungry_usage_sum  # we get a share of the spare proportional to our RTT
                max_bandwidth_on_link[0] += (normalized_share*spare_bw)

                # If this link restricts us more than previously try to assume this bandwidth as the max
                if max_bandwidth_on_link[0] < max_bandwidth:
                    # hold off increasing bandwidth for 1 cycle if there are less flows than last time
                    if len(link.flows) >= link.last_flows_count:
                        max_bandwidth = max_bandwidth_on_link[0]
                    else:
                        max_bandwidth = path.current_bandwidth

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
            for i in link_indices:
                if i in self.active_links:
                    self.accumulate_flow(bandwidth, link_indices)
                    break
        return True
