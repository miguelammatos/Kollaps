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

class DashboardState:
    graph = None
    lock = Lock()
    hosts = {}  # type: Dict[NetGraph.Service, Host]
    stopping = False
    failed_to_shutdown = False
    lost_metadata = -1

class Host:
    def __init__(self, hostname, name):
        self.name = name
        self.hostname = hostname
        self.ip = 'Unknown'
        self.down = True



@app.route('/')
def main():
    with DashboardState.lock:
        if graph is not None:
            answer = render_template('index.html', hosts=DashboardState.hosts, stopping=DashboardState.stopping,
                                     lost=DashboardState.lost_metadata, failed=DashboardState.failed_to_shutdown)
            return answer


@app.route('/stop')
def stop():
    Thread(target=stopExperiment, daemon=False).start()
    return redirect(url_for('main'))


def stopExperiment():
    with DashboardState.lock:
        if DashboardState.stopping:
            return
        else:
            DashboardState.stopping = True
            DashboardState.failed_to_shutdown = False
    sent = 0
    received = 0

    to_kill = []
    for node in DashboardState.hosts:
        host = DashboardState.hosts[node]
        if node.supervisor:
            continue
        to_kill.append(host)
    to_stop = to_kill[:]

    # Stop all services
    while to_stop:
        host = to_stop.pop()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((host.ip, FlowDisseminator.TCP_PORT))
            s.send(struct.pack("<1B", FlowDisseminator.STOP_COMMAND))
        except OSError as e:
            print(e)
            to_stop.insert(0, host)
            sleep(0.5)

    # Collect sent/received statistics and shutdown
    while to_kill:
        host = to_kill.pop()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((host.ip, FlowDisseminator.TCP_PORT))
            s.send(struct.pack("<1B", FlowDisseminator.SHUTDOWN_COMMAND))
            data = s.recv(64)
            s.close()
            data_tuple = struct.unpack("<2I", data)
            sent += data_tuple[0]
            received += data_tuple[1]
            with DashboardState.lock:
                host.down = True
                continue
        except OSError as e:
            print(e)
            to_kill.insert(0, host)
            sleep(0.5)

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
        for i in range(len(service_instances)):
                service_instances[i].ip = ips[i]
        for i, host in enumerate(service_instances):
            if host.supervisor:
                continue
            with DashboardState.lock:
                DashboardState.hosts[host].ip = ips[i]
                DashboardState.hosts[host].down = False

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
                if host.supervisor:
                    continue
                DashboardState.hosts[host] = Host(host.name, host.name + "." + str(i))

    dnsThread = Thread(target=resolve_hostnames)
    dnsThread.daemon = True
    dnsThread.start()
    app.run(host='0.0.0.0', port=8088)

