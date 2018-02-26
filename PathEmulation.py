from TCAL import pyTCAL as TCAL  # TODO this breaks compatibility with py2 for some reason...
from NetGraph import NetGraph
from threading import Lock

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List

class PEState:
    PathLock = Lock()
    shutdown = False

def init(controll_port):
    return 0
    with PEState.PathLock:
        if not PEState.shutdown:
            TCAL.init(controll_port)


def initialize_path(path):
    return 0
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

    with PEState.PathLock:
        if not PEState.shutdown:
            TCAL.initDestination(destination.ip, bandwidth, latency, drop)


def update_usage():
    return 0
    with PEState.PathLock:
        if not PEState.shutdown:
            TCAL.updateUsage()


def query_usage(service):
    return 0
    """
    :param service: NetGraph.Service
    :return: int  # in bytes
    """
    with PEState.PathLock:
        if not PEState.shutdown:
            return TCAL.queryUsage(service.ip)
        else:
            return 0


def change_bandwidth(service, new_bandwidth):
    return 0
    """
    :param service: NetGraph.Service
    :param new_bandwidth: int  # in Kbps
    :return:
    """
    with PEState.PathLock:
        if not PEState.shutdown:
            TCAL.changeBandwidth(service.ip, int(new_bandwidth))

def tearDown():
    return 0
    with PEState.PathLock:
        PEState.shutdown = True
        TCAL.tearDown()