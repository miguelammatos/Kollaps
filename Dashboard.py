import re
import struct
import sys

from flask import Flask, render_template, request, flash, redirect, url_for, jsonify, json
from threading import Lock, Thread
from time import sleep
import socket

from FlowDisseminator import FlowDisseminator
from NetGraph import NetGraph
from XMLGraphParser import XMLGraphParser

import dns.resolver

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List, Tuple

app = Flask(__name__, static_folder='static')
app.secret_key = 'sdjh234hj23409ea9[u-ad=12-eqhkdjaadj23jaksldj23objadskjalskdj-1=1dadsd;akdaldm11pnf'

proper_name = re.compile('^[a-zA-Z0-9 \-_]+$')
proper_number = re.compile('^[0-9]+$')

class DashboardState:
    graph = None
    lock = Lock()
    hosts = {}  # type: Dict[NetGraph.Node, Host]
    stopping = False
    lost_metadata = -1

class Host:
    def __init__(self, hostname, name):
        self.name = name
        self.hostname = hostname
        self.ip = 'Unknown'
        self.bandwidth = 0


def check_name(name):
    return re.match(proper_name, name)


def check_number(number):
    if re.match(proper_number, number):
        try:
            int(number)
            return True
        except:
            return False
    else:
        return False


@app.route('/')
def main():
    with DashboardState.lock:
        if graph is not None:
            return render_template('index.html', hosts=DashboardState.hosts, stopping=DashboardState.stopping, lost=DashboardState.lost_metadata)

@app.route('/stop')
def stop():
    Thread(target=stopExperiment, daemon=False).start()
    with DashboardState.lock:
        return render_template('index.html', hosts=DashboardState.hosts, stopping=DashboardState.stopping, lost=DashboardState.lost_metadata)

def stopExperiment():
    with DashboardState.lock:
        if DashboardState.stopping:
            return
        else:
            DashboardState.stopping = True
    # Do the actual shutdown (without lock)
    sent = 0
    received = 0

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for node in DashboardState.hosts:
        host = DashboardState.hosts[node]
        s.connect((host.ip, FlowDisseminator.TCP_PORT))
        s.send(struct.pack("<1B", FlowDisseminator.SHUTDOWN_COMMAND))
        data = s.recv(64)
        sent += struct.unpack_from("<1I", data, 0)
        received += struct.unpack_from("<1I", data, 4)

    with DashboardState.lock:
        DashboardState.lost_metadata = 1-(received/sent)


def resolve_hostnames():
    for service in graph.services:
        service_instances = graph.services[service]
        ips = []
        while len(ips) != len(service_instances):
            try:
                answers = dns.resolver.query(service, 'A')
                ips = [str(ip) for ip in answers]
                if len(ips) != len(service_instances):
                    sleep(3)
            except:
                sleep(3)
        ips.sort()  # needed for deterministic behaviour
        for i in range(len(DashboardState.hosts)):
                service_instances[i].ip = ips[i]
        for i, host in enumerate(service_instances):
            with DashboardState.lock:
                DashboardState.hosts[host].ip = ips[i]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        topology_file = "/topology.xml"
    else:
        topology_file = sys.argv[1]

    graph = NetGraph()
    XMLGraphParser(topology_file, graph).fill_graph()

    with DashboardState.lock:
        for service in graph.services:
            for i,host in enumerate(graph.services[service]):
                DashboardState.hosts[host] = Host(host.name, host.name + "." + str(i))

    dnsThread = Thread(target=resolve_hostnames)
    dnsThread.daemon = True
    dnsThread.start()
    app.run(host='0.0.0.0', port=8088)

