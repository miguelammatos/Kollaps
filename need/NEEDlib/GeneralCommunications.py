
from need.NEEDlib.NetGraph import NetGraph
from need.NEEDlib.utils import fail, message, start_experiment, stop_experiment, BYTE_LIMIT, SHORT_LIMIT, error, int2ip
import need.NEEDlib.PathEmulation as PathEmulation
from need.NEEDlib.EventScheduler import EventScheduler

from threading import Thread, Lock
from multiprocessing import Pool
from _thread import interrupt_main
from ctypes import CFUNCTYPE, POINTER, c_voidp, c_int
import socket
import struct
import ctypes

import sys
if sys.version_info >= (3, 0):
	from typing import Dict, List


# FIXME solve lib folder because compilation with cmake nonsense
AERON_LIB_PATH = "/home/daedalus/Documents/aeron4need/cppbuild/Release/lib/libaeronlib.so"


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
	ACK = 120
	i_SIZE = struct.calcsize("<1i")
	MAX_WORKERS = 10
	
	
	
	def __init__(self, flow_collector, graph, event_scheduler):
		self.graph = graph  # type: NetGraph
		self.scheduler = event_scheduler  # type: EventScheduler
		self.flow_collector = flow_collector
		self.produced = 0
		self.received = 0
		self.consumed = 0
		self.largest_produced_gap = -1
		self.stop_lock = Lock()
		
		self.aeron_lib = None
		self.aeron_id = None
		self.aeron_sub_list = None

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
		
		self.aeron_id = self.graph.root.ip
		self.aeron_sub_list = []
		for service in self.graph.services:
			hosts = self.graph.services[service]
			for host in hosts:
				if host != self.graph.root:
					self.peer_count += 1
					self.aeron_sub_list.append(host.ip)
				if host.supervisor:
					self.supervisor_count += 1
		self.peer_count -= self.supervisor_count
		

		print("\n\nroot: " + str(self.aeron_id) + " ip: " + int2ip(self.aeron_id))
		print("list: " + str(self.aeron_sub_list))
		sys.stdout.flush()
		
		
		# setup python callback
		self.aeron_lib = ctypes.CDLL(AERON_LIB_PATH)
		self.aeron_lib.init(self.aeron_id, len(self.aeron_sub_list), (c_int * len(self.aeron_sub_list))(*self.aeron_sub_list))
		CALLBACKTYPE = CFUNCTYPE(c_voidp, c_int, c_int, POINTER(c_int))
		c_callback = CALLBACKTYPE(self.receive_flow)
		self.callback = c_callback  # keep reference so it does not get garbage collected
		self.aeron_lib.registerCallback(self.callback)

		# broadcast_group = []
		# for service in self.graph.services:
		# 	hosts = self.graph.services[service]
		# 	for host in hosts:
		# 		if host != self.graph.root:
		# 			self.peer_count += 1
		# 			broadcast_group.append(int2ip(host.ip))
		# 		if host.supervisor:
		# 			self.supervisor_count += 1
		# self.peer_count -= self.supervisor_count
		#
		# workers = CommunicationsManager.MAX_WORKERS
		# self.process_pool = Pool(processes=workers, initializer=initialize_process, initargs=(broadcast_group,))
		# slice_count = int(len(broadcast_group)/workers)
		# slice_count = slice_count if slice_count > 0 else 1
		# self.broadcast_groups = [broadcast_group[i:i+slice_count] for i in range(0, len(broadcast_group), slice_count)]

		# self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		# self.sock.bind(('0.0.0.0', CommunicationsManager.UDP_PORT))

		# self.thread = Thread(target=self.receive_flows)
		# self.thread.daemon = True
		# self.thread.start()

		self.dashboard_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.dashboard_socket.bind(('0.0.0.0', CommunicationsManager.TCP_PORT))

		self.dashboard_thread = Thread(target=self.receive_dashboard_commands)
		self.dashboard_thread.daemon = True
		self.dashboard_thread.start()


	def add_flow(self, throughput, link_list):
		self.aeron_lib.addFlow(throughput, len(link_list), (c_int * len(link_list))(*link_list))


	def receive_flow(self, bandwidth, link_count, link_list):
		print("Python: throughput: " + str(bandwidth) + " links: " + str(link_list[:link_count]), end="")
		print()
		sys.stdout.flush()
		self.flow_collector(bandwidth, link_list[:link_count])
		self.received += 1


	def broadcast_flows(self, active_paths):
		"""
		:param active_paths: List[NetGraph.Path]
		:return:
		"""
		
		# FIXME add_flow directly in EmulationManager.py
		for path in active_paths:
			links = [link.index for link in path.links]
			self.aeron_lib.addFlow(int(path.used_bandwidth), len(links), (c_int * len(links))(*links))
			
		self.aeron_lib.flush()
		
	
	def shutdown(self):
		self.aeron_lib.shutdown()
	
	
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
						with self.stop_lock:
							message("Stopping experiment")
							self.broadcast_groups = []
							#TODO Stop is now useless, probably best to just replace with shutdown

					elif command == CommunicationsManager.SHUTDOWN_COMMAND:
						message("Received Shutdown command")
						connection.send(struct.pack("<3Q", self.produced, 50, self.received))
						ack = connection.recv(1)
						if len(ack) != 1:
							error("Bad ACK len:" + str(len(ack)))
							connection.close()
							continue
						if struct.unpack("<1B", ack)[0] != CommunicationsManager.ACK:
							error("Bad ACK, not and ACK" + str(struct.unpack("<1B", ack)))
							connection.close()
							continue
						connection.close()
						with self.stop_lock:
							self.process_pool.terminate()
							self.process_pool.join()
							self.dashboard_socket.close()
							for s in broadcast_sockets:
								s.close()
							self.sock.close()
							PathEmulation.tearDown()
							message("Shutting down")
							sys.stdout.flush()
							sys.stderr.flush()
							stop_experiment()
							interrupt_main()
							return

					elif command == CommunicationsManager.READY_COMMAND:
						connection.send(struct.pack("<1B", CommunicationsManager.ACK))
						connection.close()

					elif command == CommunicationsManager.START_COMMAND:
						connection.close()
						message("Starting Experiment!")
						self.scheduler.start()
						
			except OSError as e:
				continue  # Connection timed out (most likely)
