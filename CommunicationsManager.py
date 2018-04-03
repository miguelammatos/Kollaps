import random

from NetGraph import NetGraph
from utils import fail, start_experiment, stop_experiment, BYTE_LIMIT, SHORT_LIMIT, error
import PathEmulation

from threading import Thread, Lock
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
            self.link_unit = "B"
        elif link_count <= SHORT_LIMIT:
            self.link_unit = "H"
        else:
            fail("Topology has too many links: " + str(link_count))
        self.link_size = struct.calcsize("<1"+self.link_unit)

        self.broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.broadcast_group = []
        self.supervisor_count = 0
        self.peer_count = 0
        broadcast = os.environ.get('BROADCAST_ADDRESS', '')
        if broadcast:
            self.broadcast_group.append(broadcast)
            self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        for service in self.graph.services:
            hosts = self.graph.services[service]
            for host in hosts:
                if host != self.graph.root and not broadcast:
                    self.broadcast_group.append(host.ip)
                if host.supervisor:
                    self.supervisor_count += 1
                else:
                    if host != self.graph.root:
                        self.peer_count += 1

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
        ########################################
        # After profiling, this method was found to be responsible for 1/2 of cpu usage
        # The code that follows has been optimized
        # Check an older commit for more readable code, the functionality has not changed since
        # commit ca5c9c62e583e07d7b6d7ec7950737aacdf656fb
        ########################################



        #  This code is expensive
        # if self.largest_produced_gap < 0:
        #     self.produced_ts = time()
        # current_time = time()
        # produced_gap = current_time - self.produced_ts
        # if produced_gap > self.largest_produced_gap:
        #     self.largest_produced_gap = produced_gap
        # self.produced_ts = current_time

        i = 0
        while i < len(active_paths):
            packet = [0]
            flows_counter = 0
            fmt = "<1H"
            free_space = CommunicationsManager.BUFFER_LEN - struct.calcsize(fmt)
            while i < len(active_paths):
                flow = active_paths[i]
                # check if this flow still fits
                if free_space-CommunicationsManager.i_SIZE-(self.link_size*(len(flow.links)+1)) < 0:
                    break
                i += 1
                flows_counter += 1
                fmt += "1i"+("1"+self.link_unit)*(len(flow.links)+1)
                packet.append(int(flow.used_bandwidth))
                packet.append(len(flow.links))
                for link in flow.links:
                    packet.append(link.index)
            packet[0] = flows_counter
            size = struct.calcsize(fmt)
            data = ctypes.create_string_buffer(size)
            struct.pack_into(fmt, data, 0, *packet)
            # The following line can improve results under some scenarios but is overall too expensive
            #random.shuffle(self.broadcast_group)  # takes ~0.5ms on a list of 500 strings

            with self.stop_lock:
                self.produced += self.peer_count if len(self.broadcast_group) > 0 else 0
                for ip in self.broadcast_group:
                    self.broadcast_socket.sendto(data, (ip, CommunicationsManager.UDP_PORT))

    def receive_flows(self):
        while True:
            data, addr = self.sock.recvfrom(CommunicationsManager.BUFFER_LEN)
            offset = 0
            num_of_flows = struct.unpack_from("<1H", data, offset)[0]
            offset += struct.calcsize("<1H")
            accepted = False
            for i in range(num_of_flows):
                bandwidth = struct.unpack_from("<1i", data, offset)[0]
                offset += struct.calcsize("<1i")
                num_of_links = struct.unpack_from("<1"+self.link_unit, data, offset)[0]
                offset += struct.calcsize("<1"+self.link_unit)
                links = []
                for j in range(num_of_links):
                    index = struct.unpack_from("<1"+self.link_unit, data, offset)[0]
                    offset += struct.calcsize("<1"+self.link_unit)
                    links.append(index)

                accepted = accepted or self.flow_collector(bandwidth, links)
            if accepted:
                self.consumed += 1  # only count a packet as received if it is not dropped by the emulation manager
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
                            self.broadcast_group = []

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
                            self.broadcast_socket.close()
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
