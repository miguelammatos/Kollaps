
import time
import socket
import json
from os import environ
from threading import Lock

from need.NEEDlib.CommunicationsManager import CommunicationsManager
from need.NEEDlib.NetGraph import NetGraph
from need.NEEDlib.XMLGraphParser import XMLGraphParser
from need.NEEDlib.utils import print_named

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List, Tuple

LOG_FILE = "/var/log/NEED_LOG.json"
DEFAULT_INTERVAL = 1.0

class LoggerState:
    graph = None  # type: NetGraph
    lock = Lock()
    flows = {} # type: Dict[str, List[int, int]]
    comms = None  # type: CommunicationsManager


def collect_flow(bandwidth, links):
    key = str(links[0]) + ":" + str(links[-1])
    with LoggerState.lock:
        if key in LoggerState.flows:
            LoggerState.flows[key][0] += int(bandwidth/1000)
            LoggerState.flows[key][1] += 1
            
        else:
            LoggerState.flows[key] = [int(bandwidth/1000), 1]
            
    return True


def main():
    if len(sys.argv) != 2:
        topology_file = "/topology.xml"
    else:
        topology_file = sys.argv[1]

    AVERAGE_INTERVAL = float(environ.get("AVERAGE_INTERVAL", str(DEFAULT_INTERVAL)))

    graph = NetGraph()
    XMLGraphParser(topology_file, graph).fill_graph()
    
    own_ip = socket.gethostbyname(socket.gethostname())
    LoggerState.comms = CommunicationsManager(collect_flow, graph, None, own_ip)

    LoggerState.graph = graph
    
    print_named("logger", "Logger ready!")  # PG

    log_file = open(LOG_FILE, 'w')

    starttime=time.time()
    output = {}
    while True:
        with LoggerState.lock:
            output["ts"] = time.time()
            for key in LoggerState.flows:
                output[key] = (LoggerState.flows[key][0]/LoggerState.flows[key][1], LoggerState.flows[key][1])
            LoggerState.flows.clear()
            
        if(len(output) > 1):
            json.dump(output, log_file)
            log_file.write("\n")
            log_file.flush()
            
        output.clear()
        sleep_time = AVERAGE_INTERVAL - ((time.time() - starttime) % AVERAGE_INTERVAL)
        time.sleep(sleep_time)

if __name__ == "__main__":
    main()
