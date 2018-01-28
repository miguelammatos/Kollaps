from TCAL import pyTCAL as TCAL  # TODO this breaks compatibility with py2 for some reason...
from NetGraph import NetGraph

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List


def init():
    TCAL.init()


def initialize_path(path):
    """
    :param path: List[NetGraph.Link]
    :return:
    """
    if len(path) < 1:
        return
    destination = path[-1].destination  # type: NetGraph.Service
    bandwidth = NetGraph.calculate_path_max_initial_bandwidth(path)
    latency = NetGraph.calculate_path_latency(path)
    drop = NetGraph.calculate_path_drop(path)

    TCAL.initDestination(destination.ip, bandwidth, latency, drop)
