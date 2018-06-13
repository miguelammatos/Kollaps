from time import time, sleep
from threading import Lock
from multiprocessing import Pool
from multiprocessing.pool import AsyncResult
from os import environ
from copy import copy

from NEED.NetGraph import NetGraph
import NEED.PathEmulation as PathEmulation
from NEED.CommunicationsManager import CommunicationsManager
from NEED.utils import ENVIRONMENT

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List, Tuple

# Global variable used within the worker process
graph = None  # type: NetGraph


def initialize_worker(graph_copy):
    global graph  # type: NetGraph
    graph = graph_copy


def apply_flow(flow, g):
    INDICES = 0
    BW = 1
    link_indices = flow[INDICES]
    bandwidth = flow[BW]
    # Calculate RTT of this flow
    rtt = 0
    for index in link_indices:
        link = graph.links[index]
        rtt += (link.latency*2)
    # Add it to the link's flows
    for index in link_indices:
        graph.links[index].flows.append((rtt, bandwidth))


def apply_bandwidth(our_flows, flow_accumulator, active_paths_ids):
    global graph  # type: NetGraph
    INDICES = 0
    RTT = 0
    BW = 1

    # First update the graph with the information of the flows
    active_links = []

    # Why is this block repeated twice? because our flows are assumed to be the first entry in link.flows
    for flow in our_flows:
        link_indices = flow[INDICES]
        apply_flow(flow, graph)
        for index in link_indices:
            link = graph.links[index]
            active_links.append(link)

    for flow in flow_accumulator:
        link_indices = flow[INDICES]
        apply_flow(flow, graph)
        for index in link_indices:
            link = graph.links[index]
            active_links.append(link)

    # Now apply the RTT Aware Min-Max to calculate the new BW
    changes = []
    for id in active_paths_ids:
        path = graph.paths_by_id[id]
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
                max_bandwidth = max_bandwidth_on_link[0]

        # Apply the new bandwidth on this path
        if max_bandwidth <= path.max_bandwidth and max_bandwidth != path.current_bandwidth:
            if max_bandwidth <= path.current_bandwidth:
                path.current_bandwidth = max_bandwidth  # if its less then we now for sure it is correct
            else:
                #  if it is more then we have to be careful, it might be a spike due to lost metadata
                path.current_bandwidth = EmulationManager.ONE_MINUS_ALPHA* path.current_bandwidth + \
                                         EmulationManager.ALPHA * max_bandwidth
            changes.append((path.links[-1].index, path.current_bandwidth))

    # clear the state on the graph
    for link in active_links:
        link.flows.clear()

    return changes

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
        self.active_paths = []  # type: List[NetGraph.Path]
        self.active_paths_ids = [] # type: List[int]
        self.flow_accumulator = {}  # type: Dict[str, List[List[int], int]]
        self.state_lock = Lock()
        self.comms = CommunicationsManager(self.collect_flow, self.graph)
        self.last_time = 0
        EmulationManager.POOL_PERIOD = float(environ.get(ENVIRONMENT.POOL_PERIOD, str(EmulationManager.POOL_PERIOD)))
        print("Pool Period: " + str(EmulationManager.POOL_PERIOD))
        self.worker_process = Pool(processes=1, initializer=initialize_worker, initargs=(self.graph,))

    def initialize(self):
        PathEmulation.init(CommunicationsManager.UDP_PORT)
        for service in self.graph.paths:
            if isinstance(service, NetGraph.Service):
                path = self.graph.paths[service]
                PathEmulation.initialize_path(path)


    def emulation_loop(self):
        self.last_time = time()
        self.check_active_flows()  # to prevent bug where data has already passed through the filters before
        last_time = time()
        async_result = None  # type: AsyncResult
        async_result = self.worker_process.apply_async(apply_bandwidth, ([], [], [],))  # needed to initialize result
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
                if async_result.ready():  # apply the changes and prepare for new calculations
                    changes = async_result.get()
                    for change in changes:
                        PathEmulation.change_bandwidth(self.graph.links[change[0]].destination, change[1])
                    our_flows = []
                    for path in self.active_paths:
                        our_flows.append(([l.index for l in path.links], path.used_bandwidth))
                    # We need shallow copies otherwise the dict/list is emptied before being pickled!
                    flow_accumulator_copy = copy(list(self.flow_accumulator.values()))
                    active_paths_ids_copy = copy(self.active_paths_ids)
                    async_result = self.worker_process.apply_async(apply_bandwidth, (our_flows,
                                                                                     flow_accumulator_copy,
                                                                                     active_paths_ids_copy,))
                self.flow_accumulator.clear()

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
                self.active_paths_ids.append(path.id)

                # Collect our own flow
                # self.accumulate_flow(throughput, [l.index for l in path.links])
                # We no longer accumulate our flow, these are treated separately

        self.last_time = current_time

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
