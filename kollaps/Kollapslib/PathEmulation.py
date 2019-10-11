from kollaps.Kollapslib.NetGraph import NetGraph
from threading import Lock
from ctypes import CDLL, c_float, CFUNCTYPE, c_voidp, c_int, c_ulong, c_uint
from os import path

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List

class PEState:
    PathLock = Lock()
    shutdown = False
    TCAL = None
    callback = None  # We need to keep a reference otherwise gets garbage collected causing crashes

def init(controll_port):
    with PEState.PathLock:
        if not PEState.shutdown:
            # Get the libTCAL.so full path from the current file
            filepath = path.abspath(__file__)
            folderpath = "/".join(filepath.split('/')[0:-2])
            tcalPath = folderpath + "/TCAL/libTCAL.so"

            PEState.TCAL = CDLL(tcalPath)
            PEState.TCAL.init(controll_port, 1000)  # 1000 is the txquelen (unit is packets)


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
        if not PEState.shutdown and PEState.TCAL:
            PEState.TCAL.initDestination(destination.ip, int(bandwidth/1000), c_float(latency), c_float(jitter), c_float(drop))

def disablePath(service):
    """
    :param service: NetGraph.Service
    :return:
    We choose 10kbit rather randomly here. The problem is that bandwidth will only be changed for active paths,
    and if we take a super small value here, a path will never be active (in the emulation manager). Hence after
    activating the path disabled here (ie. by adding new links), nothing will flow through them. LL based on comments by JN
    """
    with PEState.PathLock:
        if not PEState.shutdown and PEState.TCAL:
            PEState.TCAL.initDestination(service.ip, 10000, c_float(1), c_float(0), c_float(1))


def update_usage():
    with PEState.PathLock:
        if not PEState.shutdown and PEState.TCAL:
            PEState.TCAL.updateUsage()


def query_usage(service):
    """
    :param service: NetGraph.Service
    :return: int  # in bytes
    """
    with PEState.PathLock:
        if not PEState.shutdown and PEState.TCAL:
            return PEState.TCAL.queryUsage(service.ip)
        else:
            return 0


def change_bandwidth(service, new_bandwidth):
    """
    :param service: NetGraph.Service
    :param new_bandwidth: int  # in bps
    :return:
    """
    with PEState.PathLock:
        if not PEState.shutdown and PEState.TCAL:
            PEState.TCAL.changeBandwidth(service.ip, int(new_bandwidth/1000))

def change_loss(service, new_loss):
    """
    :param service: NetGraph.Service
    :param new_loss: float
    :return:
    """
    with PEState.PathLock:
        if not PEState.shutdown and PEState.TCAL:
            PEState.TCAL.changeLoss(service.ip, c_float(new_loss))

def change_latency(service, latency, jitter):
    """
    :param service:
    :param latency:
    :param jitter:
    :return:
    """
    pass
    with PEState.PathLock:
        if not PEState.shutdown and PEState.TCAL:
            PEState.TCAL.changeLatency(service.ip, c_float(latency), c_float(jitter))

def register_usage_callback(callback):
    """
    :param callback: func
    :return:
    """
    CALLBACKTYPE = CFUNCTYPE(c_voidp, c_uint, c_ulong, c_uint)
    c_callback = CALLBACKTYPE(callback)
    PEState.callback = c_callback
    with PEState.PathLock:
        if not PEState.shutdown and PEState.TCAL:
            PEState.TCAL.registerUsageCallback(c_callback)


def disconnect():
    with PEState.PathLock:
        PEState.TCAL.disconnect()

def reconnect():
    with PEState.PathLock:
        PEState.TCAL.reconnect()

def tearDown():
    with PEState.PathLock:
        PEState.shutdown = True
        if PEState.TCAL:
            PEState.TCAL.tearDown(0)
