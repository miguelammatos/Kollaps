
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from locale import DAY_1
import socket
import struct
from os import environ, getenv
from collections import OrderedDict
from threading import Lock, Thread
from time import sleep

import dns.resolver
from kubernetes import client, config

from flask import Flask, render_template, request, flash, redirect, url_for, jsonify, json

from kollaps.Kollapslib.NetGraph import NetGraph
from kollaps.Kollapslib.XMLGraphParser import XMLGraphParser
from kollaps.Kollapslib.utils import int2ip, ip2int, setup_container, CONTAINER, BYTE_LIMIT
from kollaps.Kollapslib.utils import print_message, print_error, print_and_fail, print_named

import sys
import libcommunicationcore
import pathlib

from openssh_wrapper import SSHConnection
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
    ready = False
    initialized = False
    running = False
    stopping = False
    mode = None
    UDP_PORT = 7073
    TCP_PORT = 7073
    STOP_COMMAND = 1
    SHUTDOWN_COMMAND = 2
    READY_COMMAND = 3
    START_COMMAND = 4
    ACK = 120
    ip = ""
    controller = None
    topology_file = ""
    kollaps_folder = ""
    interact_button_pressed = 0
    links = OrderedDict()
    link_error = OrderedDict()


class Host:
    def __init__(self, name, machinename):
        self.name = name
        self.machinename = machinename
        self.ip = 'Unknown'
        self.status = 'Down'
        self.socket = None
        self.ssh = None
        self.topology_file = ""
        self.kollaps_folder = ""

class RustComms:
    def __init__(self,collect_flow):
        self.collect_flow = collect_flow


    def receive_flow(self, bandwidth, link_count, link_list):
        self.collect_flow(bandwidth, link_list[:link_count])


def get_own_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    last_ip = None
    # Connect to at least 2 to avoid using our loopback ip
    for service,host in DashboardState.hosts.items():
        print_message("ip is" + str(host.ip))
        s.connect((int2ip(host.ip), 1))
        new_ip = s.getsockname()[0]
        if new_ip == last_ip:
            break
        last_ip = new_ip
    return last_ip


@app.route('/')
def main_page():
    with DashboardState.lock:
        if DashboardState.graph is not None:
            if DashboardState.mode == "baremetal":
                answer = render_template('index_baremetal.html',
                                        hosts=DashboardState.hosts,
                                        stopping=DashboardState.stopping,
                                        max_gap=DashboardState.largest_produced_gap,
                                        max_gap_avg=DashboardState.largest_produced_gap_average,
                                        lost_packets=DashboardState.lost_packets)
            else:
                answer = render_template('index.html',
                                        hosts=DashboardState.hosts,
                                        stopping=DashboardState.stopping,
                                        max_gap=DashboardState.largest_produced_gap,
                                        max_gap_avg=DashboardState.largest_produced_gap_average,
                                        lost_packets=DashboardState.lost_packets)
            return answer

@app.route('/stop')
def stop():
    Thread(target=stopExperiment, daemon=False).start()
    return redirect(url_for('main_page'))

@app.route('/start')
def start():
    Thread(target=startExperiment, daemon=False).start()
    return redirect(url_for('main_page'))

@app.route('/initialize')
def initialize():
    Thread(target=initialize, daemon=False).start()
    return redirect(url_for('main_page'))


@app.route('/flows')
def flows():
    with DashboardState.lock:
        if DashboardState.mode == "baremetal":
            answer = render_template('flows_baremetal.html', flows=DashboardState.flows, graph=DashboardState.graph)
        else:
            answer = render_template('flows.html', flows=DashboardState.flows, graph=DashboardState.graph)
            DashboardState.flows.clear()
        return answer

@app.route('/links_state')
def links_state():
    with DashboardState.lock:
        for link in DashboardState.links:
            bandwidth = sum(DashboardState.links[link].values())
            maximum_bandwidth = DashboardState.graph.links[link].bandwidth_bps
            DashboardState.link_error[link] = ((maximum_bandwidth-bandwidth)/maximum_bandwidth)*100
            print("max_bw: " + str(maximum_bandwidth) + " and " + " bw" + str(bandwidth) + " in link " + str(link))
        if DashboardState.mode == "container":
            answer = render_template('links_state.html', link_error=DashboardState.link_error, graph=DashboardState.graph)
        for link in DashboardState.links:
            DashboardState.links[link] = {}
        return answer
    

@app.route('/graph')
def graph():
    if DashboardState.mode == "baremetal":
            return render_template('graph_baremetal.html', graph=DashboardState.graph)
    else:        
        return render_template('graph.html', graph=DashboardState.graph)

@app.route('/interact')
def interact():
    if DashboardState.mode == "baremetal":
            return
    else:        
        return render_template('interact.html', graph=DashboardState.graph)

@app.route('/next', methods=['GET', 'POST'])
def next():
    print(request.form.get("Options"), file=sys.stderr)
    if request.form.get("Options") == "start":
        return render_template('interactstart.html', graph=DashboardState.graph)
    elif request.form.get("Options") == "stop":
        return render_template('interactstop.html', graph=DashboardState.graph)
    elif request.form.get("Options") == "changelink":
        return render_template('interactchangelink.html', graph=DashboardState.graph)
    else:
        return render_template('interact.html', graph=DashboardState.graph)

def initialize():
    with DashboardState.lock:
        if DashboardState.stopping:
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
            command = 'cd '+ host.kollaps_folder + ';nohup sh start.sh ' + host.topology_file + " > foo.out 2> foo.err < /dev/null &"
            print(command)
            ret = host.ssh.run(command)
            print(ret.stdout)
            host.status = "Initialized"
        except OSError as e:
            print_error(e)
            pending_nodes.insert(0, host)
            sleep(0.5)


    command = 'cd '+ DashboardState.kollaps_folder + ';sudo ./controller ' + DashboardState.topology_file +" ready"
    print(command)
    result = DashboardState.controller.run(command)
    print_named("Controller",result)

    with DashboardState.lock:
        DashboardState.initialized = True


def collect_flow(bandwidth, links):
    key = str(links[0]) + ":" + str(links[-1])
    with DashboardState.lock:
        #print("Received from " + str(DashboardState.graph.links[links[0]].source.name) + " to " + str(DashboardState.graph.links[links[-1]].destination.name),"to",str(bandwidth))
        DashboardState.flows[key] = (links[0], links[-1], int(bandwidth/1000))
        for link in links:
            DashboardState.links[link][key] = bandwidth
            #print("ADDED BW ",bandwidth," to ", link)


    return True


def stopExperiment():
    with DashboardState.lock:
        if DashboardState.mode =="baremetal":
            if DashboardState.stopping:
                return
        else:
            if DashboardState.stopping or not DashboardState.ready:
                return
    

    produced = 0
    received = 0

    to_kill = []
    if DashboardState.mode == "baremetal":
        command = 'cd ' + DashboardState.kollaps_folder +';sudo ./controller ' + DashboardState.topology_file + " stop"
        print(command)
        result = DashboardState.controller.run(command)
        print_named("Controller",result)
        for node in DashboardState.hosts:
            host = DashboardState.hosts[node]
            if node.supervisor:
                continue
            host.status = 'Stopped'
        return

    DashboardState.stopping = True

    for node in DashboardState.hosts:
        host = DashboardState.hosts[node]
        if node.supervisor:
            continue
        to_kill.append(host)
    while to_kill:
        host = to_kill.pop()
        try:
            print_message("host is " + host.name + " sent")
            host.socket.send(struct.pack("<1B", DashboardState.SHUTDOWN_COMMAND))
            # data = host.socket.recv(4096)
            host.socket.close()
            # data_tuple = struct.unpack("<LL", data)
            # print_named("Dashboard received: ",data_tuple)
            # produced += data_tuple[0]
            # received += data_tuple[1]

            with DashboardState.lock:
                host.status = 'Down'
                continue

        except OSError as e:
            print_error("timed out\n" + str(e))
            to_kill.insert(0, host)
            sleep(0.5)

    with DashboardState.lock:
    
        print_named("dashboard", "packets: recv " + str(received) + ", prod " + str(produced))
        sys.stdout.flush()
        
        if produced > 0:
            DashboardState.lost_packets = 1-(received/produced)
        else:
            DashboardState.lost_packets = 0
        DashboardState.stopping = False


def startExperiment():
    with DashboardState.lock:
        if DashboardState.mode == "baremetal":
            if not DashboardState.initialized:
                return
        else:
            if DashboardState.stopping or not DashboardState.ready:
                return

    if DashboardState.mode == "baremetal":
        command = 'cd '+ DashboardState.kollaps_folder + ';sudo ./controller ' + DashboardState.topology_file + " start"
        print(command)
        result = DashboardState.controller.run(command)
        print_named("Controller",result)
        for node in DashboardState.hosts:
            host = DashboardState.hosts[node]
            if node.supervisor:
                continue
            
    else:
        pending_nodes = []
        for node in DashboardState.hosts:
            host = DashboardState.hosts[node]
            if node.supervisor:
                continue
            pending_nodes.append(host)

        while pending_nodes:
                host = pending_nodes.pop()
                try:
                    host.socket.send(struct.pack("<1B", DashboardState.START_COMMAND))
                    with DashboardState.lock:
                        host.status = 'Running'
                        continue
                    
                except OSError as e:
                    print_error(e)
                    pending_nodes.insert(0, host)
                    sleep(0.5)

    with DashboardState.lock:
        DashboardState.running = True


def resolve_hostnames():


    experimentUUID = environ.get('KOLLAPS_UUID', '')
    
    orchestrator = getenv('KOLLAPS_ORCHESTRATOR', 'swarm')
    if orchestrator == 'kubernetes':
        config.load_incluster_config()
        kubeAPIInstance = client.CoreV1Api()
        need_pods = kubeAPIInstance.list_namespaced_pod('default')
        
        for service in DashboardState.graph.services:
            service_instances = DashboardState.graph.services[service]
            answers = []
            ips = []
            
            while len(ips) != len(service_instances):
                try:
                    for pod in need_pods.items:
                        if pod.metadata.name.startswith(service + "-" + experimentUUID):
                            if pod.status.pod_ip is not None:  # LL
                                answers.append(pod.status.pod_ip)
                                
                    ips = [str(ip) for ip in answers]
                    
                    if len(ips) != len(service_instances):
                        answers = []
                        sleep(3)
                        need_pods = kubeAPIInstance.list_namespaced_pod('default')
                        
                except Exception as e:
                    print_error(e)
                    sys.stdout.flush()
                    sys.stderr.flush()
                    sleep(3)
                    
            ips.sort()  # needed for deterministic behaviour
            for i in range(len(service_instances)):
                service_instances[i].ip = ip2int(ips[i])

            for i, host in enumerate(service_instances):
                if host.supervisor:
                    DashboardState.ip = ips[i]
                    continue
                    
                with DashboardState.lock:
                    DashboardState.hosts[host].ip = ips[i]
                    DashboardState.hosts[host].status = 'Pending'

    else:
        if orchestrator != 'swarm':
            print_named("dashboard", "Unrecognized orchestrator. Using default docker swarm.")

        docker_resolver = dns.resolver.Resolver(configure=False)
        docker_resolver.nameservers = ['127.0.0.11']

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
                    continue
        
                with DashboardState.lock:
                    DashboardState.hosts[host].ip = ips[i]
                    DashboardState.hosts[host].status = 'Pending'



def start_rust():
    link_count = len(DashboardState.graph.links)

    if DashboardState.graph.root is None:
        print_named("dashboard","STARTED RUST")
        libcommunicationcore.start(CONTAINER.id,"dashboard",0,link_count)
    
    
    # if link_count <= BYTE_LIMIT:
    #     print_message("Started reading with u8")
    #     libcommunicationcore.start_polling_u8()

    # else:
        # print_message("Started reading with u16")
        # libcommunicationcore.start_polling_u16()
        
    libcommunicationcore.start_polling_u16()

    libcommunicationcore.register_communicationmanager(RustComms(collect_flow))

def query_until_ready():
    start_rust()
    resolve_hostnames()
    print_named("Dashboard", "resolved all hostnames.")
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
            #s.settimeout(2)
            print_named("Dashboard", "connecting to " + str(host.ip))
            s.connect((host.ip, DashboardState.TCP_PORT))
            print_named("Dashboard", "connected to " + str(host.ip))
            s.send(struct.pack("<1B", DashboardState.READY_COMMAND))
            print_named("Dashboard", "sent to " + str(host.ip))
            data = s.recv(64)
            print_named("Dashboard", "received from " + str(host.ip))
            if data != struct.pack("<1B", DashboardState.ACK):
                pending_nodes.insert(0, host)
                s.close()
            with DashboardState.lock:
                host.status = 'Ready'
                host.socket = s
                continue
        
        except OSError as e:
            print_error(e)
            print_named("dashboard","Failed to connect to " + host.name)
            pending_nodes.insert(0, host)
            s.close()
            sleep(1)
    
    with DashboardState.lock:
        DashboardState.ready = True
        
    print_named("dashboard", "Access dashboard here: " + "http://" + str(DashboardState.ip) + ":8088")
    print_named("dashboard", "Dashboard: ready!")  # PG

def controller_ready():

    pending_nodes = []
    for node in DashboardState.hosts:
        host = DashboardState.hosts[node]
        if node.supervisor:
            continue
        pending_nodes.append(host)
    
    while pending_nodes:
        host = pending_nodes.pop()
        try:
            conn = SSHConnection(host.machinename)
            host.ssh = conn
            ret = conn.run("whoami")
            print(ret)
            with DashboardState.lock:
                host.status = 'Ready'
                host.socket = client
                continue
        except Exception as e:
            print_error(e)
            print_named("dashboard","Failed to connect to " + host.machinename)
            pending_nodes.insert(0, host)
            sleep(1)
    
    conn = SSHConnection(DashboardState.controllername)
    DashboardState.controller = conn
    command = ("whoami")
    ret = DashboardState.controller.run(command)
    #send ready command to controller
    print_named("Dashboard", "Controller and host machines: up!")  # PG

    return



def add_dashboard_id(id):
        file= open("/tmp/topoinfodashboard", "a")
        file.write(id+"\n")
        file.close()

def baremetal_deployment():
    topology_file = sys.argv[1]
    DashboardState.mode = "baremetal"
    DashboardState.topology_file = topology_file
    graph = NetGraph()
    XMLGraphParser(topology_file, graph,"baremetal").fill_graph()

    with DashboardState.lock:
        for service in graph.services:
            for i, host in enumerate(graph.services[service]):
                if host.supervisor:
                    DashboardState.controllername = host.controllername
                    continue
                print_named("dashboard","Host has name " + host.machinename + " and ip " + host.ip)
                DashboardState.hosts[host] = Host(host.name, host.machinename)
                DashboardState.hosts[host].ip = host.ip
                DashboardState.hosts[host].topology_file = host.topology_file
                DashboardState.hosts[host].kollaps_folder = host.kollaps_folder
                if DashboardState.controllername == host.machinename:
                    DashboardState.topology_file = host.topology_file
                    DashboardState.kollaps_folder = host.kollaps_folder



    DashboardState.graph = graph
    
    if getenv('RUNTIME_EMULATION', 'true') != 'false':
        startup_thread = Thread(target=controller_ready)
        startup_thread.daemon = True
        startup_thread.start()
        
    app.run(host='0.0.0.0', port=8088)

def container_deployment():
    
    topology_file = "/topology.xml"

    DashboardState.mode = "container"
    setup_container(sys.argv[2], sys.argv[3])
    graph = NetGraph()
    XMLGraphParser(topology_file, graph,"container").fill_graph()

    with DashboardState.lock:
        for service in graph.services:
            for i, host in enumerate(graph.services[service]):
                if host.supervisor:
                    continue
                DashboardState.hosts[host] = Host(host.name, host.machinename)
    
    DashboardState.graph = graph

    for link in graph.links:
        DashboardState.links[link.index] = {}
    
    if getenv('RUNTIME_EMULATION', 'true') != 'false':
        startup_thread = Thread(target=query_until_ready)
        startup_thread.daemon = True
        startup_thread.start()
        
    app.run(host='0.0.0.0', port=8088)

def main():
    if len(sys.argv) == 2:
         baremetal_deployment()
    else:
         container_deployment()
    return 

if __name__ == "__main__":
    main()
