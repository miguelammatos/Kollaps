from TCAL import pyTCAL as TCAL  # TODO this breaks compatibility with py2 for some reason...
from NEED.NetGraph import NetGraph
from threading import Lock

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List

class PEState:
    PathLock = Lock()
    shutdown = False

def init(controll_port):
    with PEState.PathLock:
        if not PEState.shutdown:
            TCAL.init(controll_port)


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
    jitter = path.jitter
    drop = path.drop

    with PEState.PathLock:
        if not PEState.shutdown:
            TCAL.initDestination(destination.ip, int(bandwidth/1000), latency, jitter, drop)


def update_usage():
    with PEState.PathLock:
        if not PEState.shutdown:
            TCAL.updateUsage()


def query_usage(service):
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
    """
    :param service: NetGraph.Service
    :param new_bandwidth: int  # in bps
    :return:
    """
    with PEState.PathLock:
        if not PEState.shutdown:
            TCAL.changeBandwidth(service.ip, int(new_bandwidth/1000))

def tearDown():
    with PEState.PathLock:
        PEState.shutdown = True
        TCAL.tearDown()