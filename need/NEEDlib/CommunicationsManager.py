import random

from need.NEEDlib.NetGraph import NetGraph
from need.NEEDlib.utils import fail, start_experiment, stop_experiment, BYTE_LIMIT, SHORT_LIMIT, error, int2ip
import need.NEEDlib.PathEmulation as PathEmulation

from threading import Thread, Lock
from multiprocessing import Pool
from _thread import interrupt_main
import socket
import struct
import ctypes
import os

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List

# Header:
# Num of flows
# Flow:
# throughput
# Num of links
# id's of links


# Global variable used within the process pool(so we dont need to create new ones all the time)
broadcast_sockets = {}  # type: Dict[socket.socket]


def initialize_process(ips):
    global broadcast_sockets
    for ip in ips:
        broadcast_sockets[ip] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_sockets[ip].connect((ip, CommunicationsManager.UDP_PORT))


def send_datagram(packet, fmt, ips):
    global broadcast_sockets
    size = struct.calcsize(fmt)
    data = ctypes.create_string_buffer(size)
    # We cant pickle structs...
    struct.pack_into(fmt, data, 0, *packet)
    for ip in ips:
        broadcast_sockets[ip].send(data)


class CommunicationsManager:
    UDP_PORT = 7073
    TCP_PORT = 7073
    MIN_MTU = 576
    MAX_IP_HDR = 60
    UDP_HDR = 8
    BUFFER_LEN = MIN_MTU - MAX_IP_HDR - UDP_HDR
    STOP_COMMAND = 1
    SHUTDOWN_COMMAND = 2
    READY_COMMAND = 3
    START_COMMAND = 4
    ACK = 250
    i_SIZE = struct.calcsize("<1i")
    MAX_WORKERS = 10

    def __init__(self, flow_collector, graph):
        self.graph = graph  # type: NetGraph
        self.flow_collector = flow_collector
        self.produced = 0
        self.received = 0
        self.consumed = 0
        self.largest_produced_gap = -1
        self.stop_lock = Lock()

        link_count = len(self.graph.links)
        if link_count <= BYTE_LIMIT:
            self.link_unit = "1B"
        elif link_count <= SHORT_LIMIT:
            self.link_unit = "1H"
        else:
            fail("Topology has too many links: " + str(link_count))
        self.link_size = struct.calcsize("<"+self.link_unit)

        self.supervisor_count = 0
        self.peer_count = 0

        broadcast_group = []
        for service in self.graph.services:
            hosts = self.graph.services[service]
            for host in hosts:
                if host != self.graph.root:
                    self.peer_count += 1
                    broadcast_group.append(int2ip(host.ip))
                if host.supervisor:
                    self.supervisor_count += 1
        self.peer_count -= self.supervisor_count

        workers = CommunicationsManager.MAX_WORKERS
        self.process_pool = Pool(processes=workers, initializer=initialize_process, initargs=(broadcast_group,))
        slice_count = int(len(broadcast_group)/workers)
        slice_count = slice_count if slice_count > 0 else 1
        self.broadcast_groups = [broadcast_group[i:i+slice_count] for i in range(0, len(broadcast_group), slice_count)]

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', CommunicationsManager.UDP_PORT))

        self.dashboard_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.dashboard_socket.bind(('0.0.0.0', CommunicationsManager.TCP_PORT))

        self.thread = Thread(target=self.receive_flows)
        self.thread.daemon = True
        self.thread.start()

        self.dashboard_thread = Thread(target=self.receive_dashboard_commands)
        self.dashboard_thread.daemon = True
        self.dashboard_thread.start()


    def broadcast_flows(self, active_paths):
        """
        :param active_paths: List[NetGraph.Path]
        :return:
        """

        i = 0
        while i < len(active_paths):
            packet = [0]
            flows_counter = 0
            fmt = ["<1H"]
            free_space = CommunicationsManager.BUFFER_LEN - struct.calcsize("".join(fmt))
            packet_append = packet.append
            fmt_append = fmt.append
            while i < len(active_paths):
                flow = active_paths[i]
                # check if this flow still fits
                if free_space-CommunicationsManager.i_SIZE-(self.link_size*(len(flow.links)+1)) < 0:
                    break
                i += 1
                flows_counter += 1
                fmt_append("1Q")
                for i in range(len(flow.links)+1):
                    fmt_append(self.link_unit)
                packet_append(int(flow.used_bandwidth))
                packet_append(len(flow.links))
                for link in flow.links:
                    packet_append(link.index)
            packet[0] = flows_counter
            # We cant pickle structs...
            # size = struct.calcsize(fmt)
            # data = ctypes.create_string_buffer(size)
            # struct.pack_into(fmt, data, 0, *packet)

            with self.stop_lock:
                self.produced += self.peer_count
                for slice in self.broadcast_groups:
                    self.process_pool.apply_async(send_datagram, (packet, "".join(fmt), slice,))

    def receive_flows(self):
        while True:
            data, addr = self.sock.recvfrom(CommunicationsManager.BUFFER_LEN)
            offset = 0
            num_of_flows = struct.unpack_from("<1H", data, offset)[0]
            offset += struct.calcsize("<1H")
            for i in range(num_of_flows):
                bandwidth = struct.unpack_from("<1Q", data, offset)[0]
                offset += struct.calcsize("<1Q")
                num_of_links = struct.unpack_from("<"+self.link_unit, data, offset)[0]
                offset += struct.calcsize("<"+self.link_unit)
                links = []
                for j in range(num_of_links):
                    index = struct.unpack_from("<"+self.link_unit, data, offset)[0]
                    offset += struct.calcsize("<"+self.link_unit)
                    links.append(index)

                self.flow_collector(bandwidth, links)
            self.received += 1

    def receive_dashboard_commands(self):
        self.dashboard_socket.listen()
        while True:
            connection, addr = self.dashboard_socket.accept()
            connection.settimeout(5)
            try:
                data = connection.recv(1)
                if data:
                    command = struct.unpack("<1B", data)[0]
                    if command == CommunicationsManager.STOP_COMMAND:
                        connection.close()
                        stop_experiment()
                        with self.stop_lock:
                            print("Stopping experiment")
                            PathEmulation.tearDown()
                            self.broadcast_groups = []

                    elif command == CommunicationsManager.SHUTDOWN_COMMAND:
                        print("Received Shutdown command")
                        connection.send(struct.pack("<3Q", self.produced, 50, self.received))
                        ack = connection.recv(1)
                        if len(ack) != 1:
                            error("Bad ACK")
                            connection.close()
                            continue
                        if struct.unpack("<1B", ack) != CommunicationsManager.ACK:
                            error("Bad ACK")
                            connection.close()
                            continue
                        connection.close()
                        with self.stop_lock:
                            self.process_pool.terminate()
                            self.dashboard_socket.close()
                            self.sock.close()
                            print("Shutting down")
                            interrupt_main()

                    elif command == CommunicationsManager.READY_COMMAND:
                        connection.send(struct.pack("<1B", CommunicationsManager.ACK))
                        connection.close()

                    elif command == CommunicationsManager.START_COMMAND:
                        connection.close()
                        print("Starting Experiment!")
                        start_experiment()
            except OSError as e:
                continue  # Connection timed out (most likely)
