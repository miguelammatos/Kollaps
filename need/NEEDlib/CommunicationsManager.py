
from need.NEEDlib.NetGraph import NetGraph
import need.NEEDlib.PathEmulation as PathEmulation
from need.NEEDlib.EventScheduler import EventScheduler
from need.NEEDlib.utils import start_experiment, stop_experiment, BYTE_LIMIT, SHORT_LIMIT
from need.NEEDlib.utils import LOCAL_IPS_FILE, REMOTE_IPS_FILE, AERON_LIB_PATH
from need.NEEDlib.utils import int2ip, ip2int, print_identified, print_error, print_and_fail, print_message, print_named

from threading import Thread, Lock
from multiprocessing import Pool
from _thread import interrupt_main
from ctypes import CFUNCTYPE, POINTER, c_voidp, c_uint, c_ushort, c_bool
import socket
import struct
import json
import ctypes

import sys
if sys.version_info >= (3, 0):
	from typing import Dict, List


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
	MAX_WORKERS = 2
	
	
	def __init__(self, flow_collector, graph, event_scheduler, ip=None):
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
		self.local_ips = {}
		self.remote_ips = {}


		link_count = len(self.graph.links)
		if link_count <= BYTE_LIMIT:
			self.link_unit = "1B"
		elif link_count <= SHORT_LIMIT:
			self.link_unit = "1H"
		else:
			print_and_fail("Topology has too many links: " + str(link_count))
		self.link_size = struct.calcsize("<"+self.link_unit)

		self.supervisor_count = 0
		self.peer_count = 0
		
		if ip is None:
			self.aeron_id = self.graph.root.ip
		else:
			self.aeron_id = ip2int(ip)
			# self.aeron_id = ip2int(socket.gethostbyname(socket.gethostname()))
			
		for service in self.graph.services:
			hosts = self.graph.services[service]
			for host in hosts:
				if host != self.graph.root:
					self.peer_count += 1
					
				if host.supervisor:
					self.supervisor_count += 1
		self.peer_count -= self.supervisor_count


		# setup python callback
		self.aeron_lib = ctypes.CDLL(AERON_LIB_PATH)
		
		if link_count <= BYTE_LIMIT:
			self.aeron_lib.init(self.aeron_id, False)
			self.flow_adding_func = self.aeron_lib.addFlow8

		else:
			self.aeron_lib.init(self.aeron_id, True)
			self.flow_adding_func = self.aeron_lib.addFlow16
		
		CALLBACKTYPE = CFUNCTYPE(c_voidp, c_uint, c_uint, POINTER(c_uint))
		c_callback = CALLBACKTYPE(self.receive_flow)
		self.callback = c_callback  # keep reference so it does not get garbage collected
		self.aeron_lib.registerCallback(self.callback)
		
		
		# TODO PG run through this again, rename variables to match new god logs functionality
		my_starting_links = []
		for key, path in self.graph.paths_by_id.items():
			if len(path.links) > 0 and path.links[0].index not in my_starting_links:
				my_starting_links.append(path.links[0].index)
						
		
		with open(LOCAL_IPS_FILE, 'r') as file:
			for line in file.readlines():
				self.aeron_lib.addLocalSubs(int(line), len(my_starting_links), (c_uint * len(my_starting_links))(*my_starting_links))
				
		with open(REMOTE_IPS_FILE, 'r') as file:
			for line in file.readlines():
				self.aeron_lib.addRemoteSubs(int(line))
		
		self.aeron_lib.startPolling()
		
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
		workers = CommunicationsManager.MAX_WORKERS
		self.process_pool = Pool(processes=workers)
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
		self.flow_adding_func(throughput, len(link_list), (c_uint * len(link_list))(*link_list))


	def receive_flow(self, bandwidth, link_count, link_list):
		# print_named("(received)", "throughput: " + str(bandwidth) + " links: " + str(link_list[:link_count]))
		self.flow_collector(bandwidth, link_list[:link_count])
		self.received += 1
		
		
	def clear_flows_to_be_sent(self):
		self.aeron_lib.clearFlows()
	
	
	def broadcast_flows(self, active_paths):
		self.aeron_lib.flush()
		
	
	def shutdown(self):
		self.aeron_lib.teardown()
	
	
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
							print_message("Stopping experiment")
							self.broadcast_groups = []
							#TODO Stop is now useless, probably best to just replace with shutdown

					elif command == CommunicationsManager.SHUTDOWN_COMMAND:
						print_message("Received Shutdown command")
						
						msg = "packets: recv " + str(self.received) + ", prod " + str(self.produced)
						print_identified(self.graph, msg)
						
						connection.send(struct.pack("<3Q", self.produced, 50, self.received))
						ack = connection.recv(1)
						
						if len(ack) != 1:
							print_error("Bad ACK len:" + str(len(ack)))
							connection.close()
							continue
							
						if struct.unpack("<1B", ack)[0] != CommunicationsManager.ACK:
							print_error("Bad ACK, not and ACK" + str(struct.unpack("<1B", ack)))
							connection.close()
							continue
							
						connection.close()
						
						with self.stop_lock:
							# self.process_pool.terminate()
							# self.process_pool.join()
							self.dashboard_socket.close()
							for s in broadcast_sockets:
								s.close()
								
							# self.sock.close()
							PathEmulation.tearDown()
							print_identified(self.graph, "Shutting down")
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
						print_message("Starting Experiment!")
						self.scheduler.start()
						
			except OSError as e:
				continue  # Connection timed out (most likely)
