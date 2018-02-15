import re
import sys

from flask import Flask, render_template, request, flash, redirect, url_for, jsonify, json
from threading import Lock, Thread
from time import sleep

from NetGraph import NetGraph
from XMLGraphParser import XMLGraphParser

import dns.resolver

app = Flask(__name__, static_folder='static')
app.secret_key = 'sdjh234hj23409ea9[u-ad=12-eqhkdjaadj23jaksldj23objadskjalskdj-1=1dadsd;akdaldm11pnf'

proper_name = re.compile('^[a-zA-Z0-9 \-_]+$')
proper_number = re.compile('^[0-9]+$')

class DashboardState:
    graph = None
    lock = Lock()
    hosts = {}
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

