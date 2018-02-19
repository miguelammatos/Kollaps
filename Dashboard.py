import re
import struct
import sys
from collections import OrderedDict

from flask import Flask, render_template, request, flash, redirect, url_for, jsonify, json
from threading import Lock, Thread
from time import sleep
import socket

from CommunicationsManager import CommunicationsManager
from NetGraph import NetGraph
from XMLGraphParser import XMLGraphParser

import dns.resolver

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List, Tuple

app = Flask(__name__, static_folder='static')
app.secret_key = 'sdjh234hj23409ea9[u-ad=12-eqhkdjaadj23jaksldj23objadskjalskdj-1=1dadsd;akdaldm11pnf'

class DashboardState:
    graph = None  # type: NetGraph
    lock = Lock()
    hosts = {}  # type: Dict[NetGraph.Service, Host]
    flows = OrderedDict() # type: Dict[str, Tuple[int, int, int]]
    lost_metadata = -1
    comms = None  # type: CommunicationsManager
    stopping = False
    ready = False
    running = False

class Host:
    def __init__(self, hostname, name):
        self.name = name
        self.hostname = hostname
        self.ip = 'Unknown'
        self.status = 'Down'



@app.route('/')
def main():
    with DashboardState.lock:
        if graph is not None:
            answer = render_template('index.html', hosts=DashboardState.hosts, stopping=DashboardState.stopping,
                                     lost=DashboardState.lost_metadata)
            return answer


@app.route('/stop')
def stop():
    Thread(target=stopExperiment, daemon=False).start()
    return redirect(url_for('main'))

@app.route('/start')
def start():
    Thread(target=startExperiment, daemon=False).start()
    return redirect(url_for('main'))

@app.route('/flows')
def flows():
    with DashboardState.lock:
        answer = render_template('flows.html', flows=DashboardState.flows, graph=DashboardState.graph)
        DashboardState.flows.clear()
        return answer

@app.route('/graph')
def graph():
    return render_template('graph.html', graph=DashboardState.graph)

def stopExperiment():
    with DashboardState.lock:
        if DashboardState.stopping or not DashboardState.ready:
            return
        else:
            DashboardState.stopping = True
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
            s.connect((host.ip, CommunicationsManager.TCP_PORT))
            s.send(struct.pack("<1B", CommunicationsManager.STOP_COMMAND))
            s.close()
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
            s.connect((host.ip, CommunicationsManager.TCP_PORT))
            s.send(struct.pack("<1B", CommunicationsManager.SHUTDOWN_COMMAND))
            data = s.recv(64)
            s.close()
            data_tuple = struct.unpack("<2I", data)
            sent += data_tuple[0]
            received += data_tuple[1]
            with DashboardState.lock:
                host.status = 'Down'
                continue
        except OSError as e:
            print(e)
            to_kill.insert(0, host)
            sleep(0.5)

    with DashboardState.lock:
        received += DashboardState.comms.received
        DashboardState.lost_metadata = 1-(received/sent)
        DashboardState.stopping = False

def startExperiment():
    with DashboardState.lock:
        if DashboardState.stopping or not DashboardState.ready:
            return

    pending_nodes = []
    for node in DashboardState.hosts:
        host = DashboardState.hosts[node]
        if node.supervisor:
            continue
        pending_nodes.append(host)

    while pending_nodes:
        host = pending_nodes.pop()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((host.ip, CommunicationsManager.TCP_PORT))
            s.send(struct.pack("<1B", CommunicationsManager.START_COMMAND))
            s.close()
            with DashboardState.lock:
                host.status = 'Running'
                continue
        except OSError as e:
            print(e)
            pending_nodes.insert(0, host)
            sleep(0.5)

    with DashboardState.lock:
        DashboardState.running = True


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
                DashboardState.hosts[host].status = 'Pending'

def query_until_ready():
    resolve_hostnames()
    pending_nodes = []
    for node in DashboardState.hosts:
        host = DashboardState.hosts[node]
        if node.supervisor:
            continue
        pending_nodes.append(host)
    while pending_nodes:
        host = pending_nodes.pop()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((host.ip, CommunicationsManager.TCP_PORT))
            s.send(struct.pack("<1B", CommunicationsManager.READY_COMMAND))
            data = s.recv(64)
            s.close()
            if data != struct.pack("<1B", CommunicationsManager.ACK):
                pending_nodes.insert(0, host)
            with DashboardState.lock:
                host.status = 'Ready'
                continue
        except OSError as e:
            print(e)
            pending_nodes.insert(0, host)
            sleep(0.5)

    with DashboardState.lock:
        DashboardState.ready = True

def collect_flow(bandwidth, links):
    key = str(links[0]) + ":" + str(links[-1])
    with DashboardState.lock:
        DashboardState.flows[key] = (links[0], links[-1], bandwidth)


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

    DashboardState.comms = CommunicationsManager(collect_flow, graph)

    DashboardState.graph = graph

    startupThread = Thread(target=query_until_ready)
    startupThread.daemon = True
    startupThread.start()
    app.run(host='0.0.0.0', port=8088)


