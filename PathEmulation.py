from TCAL import pyTCAL as TCAL  # TODO this breaks compatibility with py2 for some reason...
from NetGraph import NetGraph

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List


def init():
    TCAL.init()


def initialize_path(path):
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

    TCAL.initDestination(destination.ip, bandwidth, latency, drop)

def update_usage():
    TCAL.updateUsage()

def query_usage(service):
    """
    :param service: NetGraph.Service
    :return: int  # in bytes
    """
    return TCAL.queryUsage(service.ip)

def change_bandwidth(service, new_bandwidth):
    """
    :param service: NetGraph.Service
    :param new_bandwidth: int  # in Kbps
    :return:
    """
    TCAL.changeBandwidth(service.ip, new_bandwidth)