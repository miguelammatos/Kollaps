from NetGraph import NetGraph
from utils import fail, BYTE_LIMIT, INT_LIMIT, SHORT_LIMIT


from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor
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
    MIN_MTU = 576
    MAX_IP_HDR = 60
    UDP_HDR = 8
    BUFFER_LEN = MIN_MTU - MAX_IP_HDR - UDP_HDR

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
        elif link_count <= INT_LIMIT:
            self.link_unit = "I"
        else:
            fail("Topology has too many links: " + str(link_count))

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', FlowDisseminator.UDP_PORT))

        self.thread = Thread(target=self.receive_flows)
        self.thread.daemon = True
        self.thread.start()

        self.pool = ThreadPoolExecutor(max_workers=16)


    def broadcast_flows(self, active_flows):
        """
        :param active_flows: List[NetGraph.Path]
        :return:
        """
        # TODO List
        # Check if we need to split packets
        if len(active_flows) < 1:
            return

        self.sent += 1

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
                print("sent: " + self.sent)
                print("received" + self.received)
                sys.stdout.flush()
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


