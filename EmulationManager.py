from time import time, sleep
from NetGraph import NetGraph
import PathEmulation


class EmulationManager:

    ERROR_MARGIN = 0.01  # in percent
    POOL_PERIOD = 0.05 # in seconds

    def __init__(self, graph):
        self.graph = graph  # type: NetGraph
        self.active_flows = []

    def emulation_loop(self):
        last_time = time()
        while True:
            sleep(EmulationManager.POOL_PERIOD)

            PathEmulation.update_usage()
            current_time = time()
            time_delta = current_time - last_time

            for service in self.graph.services:
                hosts = self.graph.services[service]
                for host in hosts:
                    # Calculate current throughput
                    bytes = PathEmulation.query_usage(host)
                    if bytes < host.last_bytes:
                        bytes_delta = bytes #in case of overflow ignore the bytes before the overflow
                    else:
                        bytes_delta = bytes - host.last_bytes
                    throughput = bytes_delta / time_delta
                    host.last_bytes = bytes

                    #Get the network path
                    path = self.graph.paths[host]
                    if throughput <= (path.max_bandwidth*EmulationManager.ERROR_MARGIN):
                        continue

                    # TODO RTT-aware min-max
