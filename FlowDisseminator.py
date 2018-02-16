from NetGraph import NetGraph
from utils import fail, BYTE_LIMIT, SHORT_LIMIT
import PathEmulation

from threading import Thread, Lock
from time import time
import socket
import struct
import ctypes

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List

# Header:
# Num of flows
# Flow:
# throughput
# Num of links
# id's of links


class FlowDisseminator:
    UDP_PORT = 7073
    TCP_PORT = 7073
    MIN_MTU = 576
    MAX_IP_HDR = 60
    UDP_HDR = 8
    BUFFER_LEN = MIN_MTU - MAX_IP_HDR - UDP_HDR

    SHUTDOWN_COMMAND = 1

    def __init__(self, manager, flow_collector, graph):
        self.graph = graph  # type: NetGraph
        self.emuliation_manager = manager
        self.flow_collector = flow_collector
        self.sent = 0
        self.received = 0

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
        self.sock.bind(('0.0.0.0', FlowDisseminator.UDP_PORT))

        self.dashboard_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.dashboard_socket.bind(('0.0.0.0', FlowDisseminator.TCP_PORT))

        self.thread = Thread(target=self.receive_flows)
        self.thread.daemon = True
        self.thread.start()

        self.dashboard_thread = Thread(target=self.receive_dashboard_commands)
        self.dashboard_thread.daemon = True
        self.dashboard_thread.start()

    def broadcast_flows(self, active_flows):
        """
        :param active_flows: List[NetGraph.Path]
        :return:
        """
        # TODO List
        # Check if we need to split packets
        if len(active_flows) < 1:
            return


        # calculate size of packet
        fmt = "<1i"
        for flow in active_flows:
            fmt += "1i1"+self.link_unit
            for link in flow.links:
                fmt += "1"+self.link_unit
        size = struct.calcsize(fmt)

        # Build the packet
        data = ctypes.create_string_buffer(size)
        accumulated_size = 0
        struct.pack_into("<1i", data, accumulated_size, len(active_flows))
        accumulated_size += struct.calcsize("<1i")
        for flow in active_flows:
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
                    s.sendto(data, (host.ip, FlowDisseminator.UDP_PORT))
                    self.sent += 1
        s.close()

    def receive_flows(self):
        # TODO check for split packets
        last_time = time()
        while True:
            data, addr = self.sock.recvfrom(FlowDisseminator.BUFFER_LEN)
            self.received += 1
            current_time = time()
            if current_time - last_time > 10:
                last_time = current_time
            offset = 0
            num_of_flows = struct.unpack_from("<1i", data, offset)[0]
            offset += struct.calcsize("<1i")
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
            print("listening for supervisor commands")
            sys.stdout.flush()
            connection, addr = self.dashboard_socket.accept()
            data = connection.recv(1)
            if data:
                command = struct.unpack("<1B", data)[0]
                if command == FlowDisseminator.SHUTDOWN_COMMAND:
                    PathEmulation.tearDown()
                    connection.send(struct.pack("<2I", self.sent, self.received))
                    connection.close()
                    self.dashboard_socket.close()
                    self.sock.close()
                    exit(0)
