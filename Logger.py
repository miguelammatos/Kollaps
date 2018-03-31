from threading import Lock
import time
import json

from CommunicationsManager import CommunicationsManager
from NetGraph import NetGraph
from XMLGraphParser import XMLGraphParser

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List, Tuple

LOG_FILE = "/var/log/NEED_LOG.json"
AVERAGE_INTERVAL = 1.0

class LoggerState:
    graph = None  # type: NetGraph
    lock = Lock()
    flows = {} # type: Dict[str, List[int, int]]
    comms = None  # type: CommunicationsManager


def collect_flow(bandwidth, links):
    key = str(links[0]) + ":" + str(links[-1])
    with LoggerState.lock:
        if key in LoggerState.flows:
            LoggerState.flows[key][0] += bandwidth
            LoggerState.flows[key][1] += 1
        else:
            LoggerState.flows[key] = [bandwidth, 1]
    return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        topology_file = "/topology.xml"
    else:
        topology_file = sys.argv[1]

    graph = NetGraph()
    XMLGraphParser(topology_file, graph).fill_graph()

    LoggerState.comms = CommunicationsManager(collect_flow, graph)

    LoggerState.graph = graph

    log_file = open(LOG_FILE, 'w')

    starttime=time.time()
    output = {}
    while True:
        with LoggerState.lock:
            output["ts"] = time.time()
            for key in LoggerState.flows:
                output[key] = LoggerState.flows[key][0]/LoggerState.flows[key][1]
            LoggerState.flows.clear()
        json.dump(output, log_file)
        log_file.write("\n")
        log_file.flush()
        output.clear()
        sleep_time = AVERAGE_INTERVAL - ((time.time() - starttime) % AVERAGE_INTERVAL)
        time.sleep(sleep_time)
