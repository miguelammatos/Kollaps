import struct
from collections import OrderedDict
from os import environ

from flask import Flask, render_template, request, flash, redirect, url_for, jsonify, json
from threading import Lock, Thread
from time import sleep
import socket

from NEED.CommunicationsManager import CommunicationsManager
from NEED.NetGraph import NetGraph
from NEED.XMLGraphParser import XMLGraphParser
from NEED.utils import int2ip, ip2int

import dns.resolver
import netifaces

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
    largest_produced_gap = -1
    largest_produced_gap_average = -1
    lost_packets = -1
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
        if DashboardState.graph is not None:
            answer = render_template('index.html', hosts=DashboardState.hosts, stopping=DashboardState.stopping,
                                     max_gap=DashboardState.largest_produced_gap,
                                     max_gap_avg=DashboardState.largest_produced_gap_average,
                                     lost_packets=DashboardState.lost_packets)
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
    produced = 0
    received = 0
    gaps = []

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
            if len(data) < struct.calcsize("<3Q"):
                s.close()
                print("Got less than 24 bytes for counters.")
                to_kill.insert(0, host)
                continue
            s.send(struct.pack("<1B", CommunicationsManager.ACK))
            s.close()
            data_tuple = struct.unpack("<3Q", data)
            produced += data_tuple[0]
            received += data_tuple[2]
            with DashboardState.lock:
                host.status = 'Down'
                continue
        except OSError as e:
            print("timed out")
            print(e)
            to_kill.insert(0, host)
            sleep(0.5)

    with DashboardState.lock:
        if produced > 0:
            DashboardState.lost_packets = 1-(received/produced)
        else:
            DashboardState.lost_packets = 0
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
    # See comments in NetGraph.py

    experimentUUID = environ.get('NEED_UUID', '')
    docker_resolver = dns.resolver.Resolver(configure=False)
    docker_resolver.nameservers = ['127.0.0.11']

    # We need to save our own ips for setting the root of the graph
    # Check the comment in CommunicationsManager.init for why this code is commented
    # own_ips = []
    # for interface in netifaces.interfaces():
    #     try:
    #         own_ips.append(netifaces.ifaddresses(interface)[netifaces.AF_INET][0]['addr'])
    #     except KeyError:
    #         pass

    for service in DashboardState.graph.services:
        service_instances = DashboardState.graph.services[service]
        ips = []
        while len(ips) != len(service_instances):
            try:
                answers = docker_resolver.query(service + "-" + experimentUUID, 'A')
                ips = [str(ip) for ip in answers]
                if len(ips) != len(service_instances):
                    sleep(3)
            except:
                sleep(3)
        ips.sort()  # needed for deterministic behaviour
        for i in range(len(service_instances)):
                service_instances[i].ip = ip2int(ips[i])
        for i, host in enumerate(service_instances):
            if host.supervisor:
                # for ip in own_ips:
                #     if ip == host.ip:
                #         DashboardState.graph.root = host
                continue
            with DashboardState.lock:
                DashboardState.hosts[host].ip = ips[i]
                DashboardState.hosts[host].status = 'Pending'

    # We can only instantiate the CommunicationsManager after the graphs root has been set
    DashboardState.comms = CommunicationsManager(collect_flow, DashboardState.graph)

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
        DashboardState.flows[key] = (links[0], links[-1], int(bandwidth/1000))
    return True


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


    DashboardState.graph = graph

    startupThread = Thread(target=query_until_ready)
    startupThread.daemon = True
    startupThread.start()
    app.run(host='0.0.0.0', port=8088)


