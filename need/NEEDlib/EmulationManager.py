from time import time, sleep
from threading import Lock
from os import environ

from need.NEEDlib.NetGraph import NetGraph
import need.NEEDlib.PathEmulation as PathEmulation
from need.NEEDlib.CommunicationsManager import CommunicationsManager
from need.NEEDlib.utils import ENVIRONMENT, message
from need.NEEDlib.EventScheduler import EventScheduler

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List, Tuple

# Global variable used within the callback to TCAL
emuManager = None  # type: EmulationManager


def collect_usage(ip, sent_bytes):
    emuManager.collect_own_flow(ip, sent_bytes)

class EmulationManager:

    # Generic loop tuning
    ERROR_MARGIN = 0.01  # in percent
    POOL_PERIOD = 0.05 # in seconds
    ITERATIONS_TO_INTEGRATE = 2

    # Exponential weighted moving average tuning
    ALPHA = 0.25
    ONE_MINUS_ALPHA = 1-ALPHA

    def __init__(self, net_graph, event_scheduler):
        self.graph = net_graph  # type: NetGraph
        self.scheduler = event_scheduler  # type: EventScheduler
        self.active_paths = []  # type: List[NetGraph.Path]
        self.active_paths_ids = [] # type: List[int]
        self.flow_accumulator = {}  # type: Dict[str, List[List[int], int]]
        self.state_lock = Lock()
        self.last_time = 0
        EmulationManager.POOL_PERIOD = float(environ.get(ENVIRONMENT.POOL_PERIOD, str(EmulationManager.POOL_PERIOD)))
        EmulationManager.ITERATIONS_TO_INTEGRATE = int(environ.get(ENVIRONMENT.ITERATION_COUNT,
                                                                   str(EmulationManager.ITERATIONS_TO_INTEGRATE)))
        message("Pool Period: " + str(EmulationManager.POOL_PERIOD))
        message("Iteration Count: " + str(EmulationManager.ITERATIONS_TO_INTEGRATE))

        self.check_flows_time_delta = 0
        #We need to give the callback a reference to ourselves (kind of hackish...)
        global emuManager
        emuManager = self

        self.comms = CommunicationsManager(self.collect_flow, self.graph, self.scheduler)

    def initialize(self):
        PathEmulation.init(CommunicationsManager.UDP_PORT)
        for service in self.graph.paths:
            if isinstance(service, NetGraph.Service):
                path = self.graph.paths[service]
                PathEmulation.initialize_path(path)
        PathEmulation.register_usage_callback(collect_usage)


    def emulation_loop(self):
        self.last_time = time()
        self.check_active_flows()  # to prevent bug where data has already passed through the filters before
        last_time = time()

        while True:
            for i in range(EmulationManager.ITERATIONS_TO_INTEGRATE):
                sleep_time = EmulationManager.POOL_PERIOD - (time() - last_time)
                if sleep_time > 0.0:
                    sleep(sleep_time)
                last_time = time()
                with self.state_lock:
                    self.active_paths.clear()
                    self.active_paths_ids.clear()
                    self.check_active_flows()
                self.comms.broadcast_flows(self.active_paths)
            with self.state_lock:
                self.apply_bandwidth()
                self.flow_accumulator.clear()

    def apply_flow(self, flow):
        INDICES = 0
        BW = 1
        link_indices = flow[INDICES]
        bandwidth = flow[BW]
        # Calculate RTT of this flow
        rtt = 0
        for index in link_indices:
            link = self.graph.links[index]
            with link.lock:
                rtt += (link.latency*2)
        # Add it to the link's flows
        for index in link_indices:
            self.graph.links[index].flows.append((rtt, bandwidth))


    def apply_bandwidth(self):
        INDICES = 0
        RTT = 0
        BW = 1

        # First update the graph with the information of the flows
        active_links = []

        # Add the info about our flows
        for path in self.active_paths:
            for link in path.links:
                active_links.append(link)
                link.flows.append((path.RTT, path.used_bandwidth))

        # Add the info about others flows
        for key in self.flow_accumulator:
            flow = self.flow_accumulator[key]
            link_indices = flow[INDICES]
            self.apply_flow(flow)
            for index in link_indices:
                link = self.graph.links[index]
                active_links.append(link)

        # Now apply the RTT Aware Min-Max to calculate the new BW
        for id in self.active_paths_ids:
            path = self.graph.paths_by_id[id]
            max_bandwidth = path.max_bandwidth
            for link in path.links:
                rtt_reverse_sum = 0
                for flow in link.flows:
                    rtt_reverse_sum += (1.0/flow[RTT])
                max_bandwidth_on_link = []
                # calculate our bandwidth
                max_bandwidth_on_link.append(((1.0/link.flows[0][RTT])/rtt_reverse_sum)*link.bandwidth_bps)

                # Maximize link utilization
                maximized_bw = max_bandwidth_on_link[0]
                spare_bw = link.bandwidth_bps - max_bandwidth_on_link[0]
                our_share = max_bandwidth_on_link[0]/link.bandwidth_bps
                hungry_usage_sum = our_share  # We must be before the loop to avoid division by zero
                # 1st calculate spare bw
                for i in range(1, len(link.flows)):
                    flow = link.flows[i]
                    # calculate the bandwidth for everyone
                    max_bandwidth_on_link.append(((1.0/flow[RTT])/rtt_reverse_sum)*link.bandwidth_bps)

                    spare_bw -= flow[BW]
                    # Check if a flow is "hungry" (wants more than its allocated share)
                    if flow[BW] > max_bandwidth_on_link[i]:
                        hungry_usage_sum += flow[BW]/link.bandwidth_bps

                # 2nd try to use that spare bw
                normalized_share = our_share/hungry_usage_sum  # we get a share of the spare proportional to our RTT
                maximized_bw += (normalized_share*spare_bw)
                spare_bw -= (normalized_share*spare_bw)
                if spare_bw < -link.bandwidth_bps*EmulationManager.ERROR_MARGIN:
                    maximized_bw = max_bandwidth_on_link[0]

                # If this link restricts us more than previously try to assume this bandwidth as the max
                if maximized_bw < max_bandwidth:
                    max_bandwidth = maximized_bw

            # Apply the new bandwidth on this path
            if max_bandwidth <= path.max_bandwidth and max_bandwidth != path.current_bandwidth:
                if max_bandwidth <= path.current_bandwidth:
                    path.current_bandwidth = max_bandwidth  # if its less then we now for sure it is correct
                else:
                    #  if it is more then we have to be careful, it might be a spike due to lost metadata
                    path.current_bandwidth = EmulationManager.ONE_MINUS_ALPHA* path.current_bandwidth + \
                                             EmulationManager.ALPHA * max_bandwidth
                service = path.links[-1].destination
                PathEmulation.change_bandwidth(service, path.current_bandwidth)

        # clear the state on the graph
        for link in active_links:
            link.flows.clear()

    def check_active_flows(self):
        current_time = time()
        self.check_flows_time_delta = current_time - self.last_time
        self.last_time = current_time
        PathEmulation.update_usage()

    def collect_own_flow(self, ip, sent_bytes):
        host = self.graph.hosts_by_ip[ip]
        # Calculate current throughput
        if sent_bytes < host.last_bytes:
            bytes_delta = sent_bytes  # in case of overflow ignore the bytes before the overflow
        else:
            bytes_delta = sent_bytes - host.last_bytes
        bits = (bytes_delta) * 8
        throughput = bits / self.check_flows_time_delta
        host.last_bytes = sent_bytes

        # Get the network path
        path = self.graph.paths[host]

        # Check if this is an active flow
        if throughput <= (path.max_bandwidth * EmulationManager.ERROR_MARGIN):
            path.used_bandwidth = 0
            return

        # This is an active flow
        path.used_bandwidth = throughput
        self.active_paths.append(path)
        self.active_paths_ids.append(path.id)


    def accumulate_flow(self, bandwidth, link_indices):
        """
        This method adds a flow to the accumulator (Note: it doesnt grab the lock)
        :param bandwidth: int
        :param link_indices: List[int]
        """
        INDICES = 0
        BW = 1
        key = str(link_indices[0]) + ":" + str(link_indices[-1])
        if key in self.flow_accumulator:
            flow = self.flow_accumulator[key]
            flow[BW] = bandwidth
        else:
            self.flow_accumulator[key] = [link_indices, bandwidth]

    def collect_flow(self, bandwidth, link_indices):
        """
        This method collects a flow from other nodes, it checks if it is interesting and if so calls accumulate_flow
        :param bandwidth: int
        :param link_indices: List[int]
        """
        # TODO the return value is no longer useful

        # Check if this flow is interesting to us
        with self.state_lock:
            self.accumulate_flow(bandwidth, link_indices)
        return True
