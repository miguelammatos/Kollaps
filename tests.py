#! /usr/bin/python
from NetGraph import NetGraph
from XMLGraphParser import XMLGraphParser
from EmulationManager import EmulationManager
from utils import fail

import PathEmulation
from FlowDisseminator import FlowDisseminator

from threading import Thread
from sched import scheduler

import sys
from time import time, sleep


def mock_init():
    print("TC init called")


def mock_initialize_path(path):
    """
    :param path: NetGraph.Path
    :return:
    """
    if len(path.links) < 1:
        return
    destination = path.links[-1].destination  # type: NetGraph.Service
    bandwidth = path.max_bandwidth
    latency = path.latency
    drop = path.drop
    print("Initializing " + destination.name + ":" + str(destination.__hash__()) + " with "
          + str(latency) + "ms "
          + str(bandwidth) + "Kbps "
          + str(drop) + "drop")


def mock_update_usage():
    current_time = time()
    mock_update_usage.time_delta = current_time - mock_update_usage.last_time
    mock_update_usage.last_time = current_time
    print("Updating data usage")

mock_sent_bytes = {}
def mock_query_usage(service):
    """
    :param service: NetGraph.Service
    :return: int  # in bytes
    """
    if service.name != "server1":
        return 0
    Mbits = 50
    sent_delta = ((Mbits*1000*1000)/8)*mock_update_usage.time_delta
    if service in mock_sent_bytes:
        mock_sent_bytes[service] += sent_delta
    else:
        mock_sent_bytes[service] = sent_delta

    return mock_sent_bytes[service]


def mock_change_bandwidth(service, new_bandwidth):
    """
    :param service: NetGraph.Service
    :param new_bandwidth: int  # in Kbps
    :return:
    """
    print("Changing " + service.name + ":" + str(service.__hash__()) + " to " + str(new_bandwidth) + "Kbps")


class MockFlowDisseminator:
    def __init__(self, manager, flow_collector):
        self.emulation_manager = manager
        self.flow_collector = flow_collector
        self.concurrency_timer = 5
        self.s = scheduler(time, sleep)
        self.thread = Thread(target=self.receive_flows, args=([],))
        self.thread.start()

    def broadcast_flows(self, active_flows):
        """
        :param active_flows: List[NetGraph.Path]
        :return:
        """
        print("Active Flows: " + str(len(active_flows)))
        for path in active_flows:
            print("    " + str(path.used_bandwidth))
            print("    " + str(len(path.links)))
            for link in path.links:
                print("        " + str(link.index))

    def receive_flows(self, data):
        bandwidthMbps = 51
        path = [2, 4, 7]
        self.flow_collector(bandwidthMbps*1000, path)
        bandwidthMbps = 51
        path = [2, 4, 6]
        self.flow_collector(bandwidthMbps*1000, path)
        print("Active Concurrent Flow")
        print("    " + str(bandwidthMbps*1000))
        for i in path:
            print("    " + str(i))
        self.concurrency_timer -= 1
        if self.concurrency_timer > 0:
            self.s.enter(0.05, 1, self.receive_flows,argument=([],))
            self.s.run()

def setup_mocking():
    PathEmulation.init = mock_init
    PathEmulation.initialize_path = mock_initialize_path
    PathEmulation.update_usage = mock_update_usage
    PathEmulation.query_usage = mock_query_usage
    mock_update_usage.last_time = time()
    mock_query_usage.sent_bytes = 0
    PathEmulation.change_bandwidth = mock_change_bandwidth

    FlowDisseminator.__init__ = MockFlowDisseminator.__init__
    FlowDisseminator.broadcast_flows = MockFlowDisseminator.broadcast_flows
    FlowDisseminator.receive_flows = MockFlowDisseminator.receive_flows

def main():
    setup_mocking()

    topology_file = sys.argv[1]

    graph = NetGraph()

    XMLGraphParser(topology_file, graph).fill_graph()
    print("Done parsing topology")

    #__debug_print_paths(graph)
    #return

    print("Skipping Resolving hostnames...")
    #graph.resolve_hostnames()
    #print("All hosts found!")

    print("Determining the root of the tree...")
    graph.root = graph.services["client1"][0]


    if graph.root is None:
        fail("Failed to identify current service instance in topology!")

    print("Calculating shortest paths...")
    graph.calculate_shortest_paths()

    for node in graph.paths:
        path = graph.paths[node]
        print("##############################")
        print(graph.root.name + " -> " + node.name + ":" + str(node.__hash__()))
        print("latency: " + str(path.latency))
        print("drop: " + str(path.drop))
        print("bandwidth: " + str(path.max_bandwidth))
        print("------------------------------")
        for link in path.links:
            print("   " + link.source.name + " hop " + link.destination.name + " i:" + str(link.index))

    print("Initializing network emulation conditions...")
    PathEmulation.init()
    for service in graph.paths:
        if isinstance(service, NetGraph.Service):
            path = graph.paths[service]
            PathEmulation.initialize_path(path)


    print("Starting experiment!")
    # Enter the emulation loop
    manager = EmulationManager(graph)
    manager.emulation_loop()


if __name__ == '__main__':
    main()
