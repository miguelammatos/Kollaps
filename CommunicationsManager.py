from NetGraph import NetGraph
from utils import fail, start_experiment, stop_experiment, BYTE_LIMIT, SHORT_LIMIT
import PathEmulation

from threading import Thread, Lock
from _thread import interrupt_main
from time import time
import socket
import struct
import ctypes

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List

# Header:
# counter
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

    def __init__(self, flow_collector, graph):
        self.graph = graph  # type: NetGraph
        self.flow_collector = flow_collector
        self.sent = 0
        self.received = 0
        self.stop_lock = Lock()
        self.stop = False

        link_count = len(self.graph.links)
        if link_count <= BYTE_LIMIT:
            self.link_unit = "B"
        elif link_count <= SHORT_LIMIT:
            self.link_unit = "H"
        #elif link_count <= INT_LIMIT:
        #    self.link_unit = "I"
        else:
            fail("Topology has too many links: " + str(link_count))

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
        :param active_flows: List[NetGraph.Path]
        :return:
        """
        with self.stop_lock:
            if self.stop:
                return

        active_flows = active_paths[:]

        while active_flows:
            packet_flows = []

            # calculate size of packet
            fmt = "<1H"
            while active_flows:
                flow = active_flows.pop()
                fmt += "1i1"+self.link_unit
                for link in flow.links:
                    fmt += "1"+self.link_unit
                size = struct.calcsize(fmt)
                if size <= CommunicationsManager.BUFFER_LEN:  # If we fit in the packet append it
                    packet_flows.append(flow)
                    continue
                else:  # if we dont fit, send the other ones
                    active_flows.append(flow)  # and put the current one back in
                    break



            # Build the packet
            size = struct.calcsize(fmt)
            data = ctypes.create_string_buffer(size)
            accumulated_size = 0
            struct.pack_into("<1H", data, accumulated_size, len(packet_flows))
            accumulated_size += struct.calcsize("<1H")
            while packet_flows:
                flow = packet_flows.pop()
                struct.pack_into("<1i", data, accumulated_size, int(flow.used_bandwidth))
                accumulated_size += struct.calcsize("<1i")
                struct.pack_into("<1"+self.link_unit, data, accumulated_size, len(flow.links))
                accumulated_size += struct.calcsize("<1"+self.link_unit)
                for link in flow.links:
                    struct.pack_into("<1"+self.link_unit, data, accumulated_size, link.index)
                    accumulated_size += struct.calcsize("<1"+self.link_unit)

            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            for service in self.graph.services:
                hosts = self.graph.services[service]
                for host in hosts:
                    if host != self.graph.root:
                        s.sendto(data, (host.ip, CommunicationsManager.UDP_PORT))
                        self.sent += 1
            s.close()

    def receive_flows(self):
        while True:
            data, addr = self.sock.recvfrom(CommunicationsManager.BUFFER_LEN)
            self.received += 1
            offset = 0
            num_of_flows = struct.unpack_from("<1H", data, offset)[0]
            offset += struct.calcsize("<1H")
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
                self.flow_collector(bandwidth, links)

    def receive_dashboard_commands(self):
        self.dashboard_socket.listen(1)
        while True:
            connection, addr = self.dashboard_socket.accept()
            connection.settimeout(5)
            try:
                data = connection.recv(1)
                if data:
                    command = struct.unpack("<1B", data)[0]
                    if command == CommunicationsManager.STOP_COMMAND:
                        connection.close()
                        with self.stop_lock:
                            self.stop = True
                        stop_experiment()
                        PathEmulation.tearDown()

                    elif command == CommunicationsManager.SHUTDOWN_COMMAND:
                        connection.send(struct.pack("<2Q", self.sent, self.received))
                        ack = connection.recv(1)
                        if struct.unpack("<1B", ack) != CommunicationsManager.ACK:
                            connection.close()
                            continue
                        connection.close()
                        self.dashboard_socket.close()
                        self.sock.close()
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

