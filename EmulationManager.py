from time import time, sleep
from NetGraph import NetGraph
import PathEmulation

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List

class EmulationManager:

    ERROR_MARGIN = 0.01  # in percent
    POOL_PERIOD = 0.05 # in seconds

    def __init__(self, graph):
        self.graph = graph  # type: NetGraph
        self.active_flows = {} # type: Dict[NetGraph.Service, NetGraph.Path]
        # self.active_links

    def emulation_loop(self):
        last_time = time()
        while True:
            self.reset_flow_state()
            last_time = self.check_active_flows(last_time)
            self.disseminate_active_flows()
            sleep(EmulationManager.POOL_PERIOD)
            self.recalculate_path_bandwidths()

    def reset_flow_state(self):
        for host in self.active_flows:
            flow = self.active_flows[host]
            for link in flow.links:
                link.used_bandwidth_Kbps = 0
                link.flows = 0

        self.active_flows.clear()

    def check_active_flows(self, last_time):
        PathEmulation.update_usage()
        current_time = time()
        time_delta = current_time - last_time
        for service in self.graph.services:
            hosts = self.graph.services[service]
            for host in hosts:
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
                    if host in self.active_flows:
                        del self.active_flows[host]
                    continue

                # This is an active flow
                if host not in self.active_flows:
                    self.active_flows[host] = path

                for link in path.links:
                    link.used_bandwidth_Kbps += throughput
                    link.flows.append(path)
        return current_time

    def disseminate_active_flows(self):
        pass

    def recalculate_path_bandwidths(self):
        pass

    def collect_flow(self, bandwidth, link_indices):
        pass