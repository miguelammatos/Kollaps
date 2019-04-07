
from time import time, sleep
from threading import Lock
from os import environ

from need.NEEDlib.NetGraph import NetGraph
from need.NEEDlib.EventScheduler import EventScheduler
import need.NEEDlib.PathEmulation as PathEmulation
from need.NEEDlib.CommunicationsManager import CommunicationsManager
from need.NEEDlib.utils import ENVIRONMENT
from need.NEEDlib.utils import print_error, print_message

import sys
if sys.version_info >= (3, 0):
	from typing import Dict, List, Tuple
	

# Global variable used within the callback to TCAL
emuManager = None  # type: EmulationManager


def collect_usage(ip, sent_bytes, qlen):  # qlen: number of packets in the qdisc, max is txqueuelen
	emuManager.collect_own_flow(ip, sent_bytes)


class EmulationManager:

	# Generic loop tuning
	ERROR_MARGIN = 0.01  # in percent
	POOL_PERIOD = 0.05	# in seconds
	ITERATIONS_TO_INTEGRATE = 2

	# Exponential weighted moving average tuning
	ALPHA = 0.25
	ONE_MINUS_ALPHA = 1-ALPHA
	
	
	def __init__(self, net_graph, event_scheduler):
		self.graph = net_graph  # type: NetGraph
		self.scheduler = event_scheduler  # type: EventScheduler
		self.active_paths = []  # type: List[NetGraph.Path]
		self.active_paths_ids = []  # type: List[int]
		self.flow_accumulator = {}  # type: Dict[str, List[List[int], int]]
		self.state_lock = Lock()
		self.last_time = 0
		EmulationManager.POOL_PERIOD = float(environ.get(ENVIRONMENT.POOL_PERIOD, str(EmulationManager.POOL_PERIOD)))
		EmulationManager.ITERATIONS_TO_INTEGRATE = int(environ.get(ENVIRONMENT.ITERATION_COUNT,
																   str(EmulationManager.ITERATIONS_TO_INTEGRATE)))
		
		print_message("Pool Period: " + str(EmulationManager.POOL_PERIOD))
		print_message("Iteration Count: " + str(EmulationManager.ITERATIONS_TO_INTEGRATE))
		
		self.check_flows_time_delta = 0
		# We need to give the callback a reference to ourselves (kind of hackish...)
		global emuManager
		emuManager = self
		
		self.comms = CommunicationsManager(self.collect_flow, self.graph, self.scheduler)


	def initialize(self):
		PathEmulation.init(CommunicationsManager.UDP_PORT)
		
		for service in self.graph.paths:
			if isinstance(service, NetGraph.Service):
				path = self.graph.paths[service]
				PathEmulation.initialize_path(path)
				
		# LL: also drop everything that goes towards a host we don't see
		for service in self.graph.services.values():
			for serviceinstance in service:
				if not serviceinstance in self.graph.paths and not serviceinstance.supervisor:
					PathEmulation.disablePath(serviceinstance)
					
		PathEmulation.register_usage_callback(collect_usage)


	# What check_active_flows does is call PathEmulation.update_usage(), which calls TCAL.update_usage(), which calls TC_updateUsage().
	# This function requests a dump of the statistics kept by tc, which is done by calling update_class() once for each tc class.
	# Since there is a 1:1 relationship between HTC classes to hosts, this is performed once for each host.
	# If there was a flow (>0B sent), it calls the registered usageCallback(), which is this class' collect_usage() method.
	# Therefore, check_active_flows() basically calls collect_own_flow() once for each host.
	# LL based on information from JN
	def emulation_loop(self):
		self.last_time = time()
		self.check_active_flows()  # to prevent bug where data has already passed through the filters before
		last_time = time()


		while True:
			for i in range(EmulationManager.ITERATIONS_TO_INTEGRATE):
				sleep_time = EmulationManager.POOL_PERIOD - (time() - last_time)
				
				if sleep_time > 0.0:
					sleep(sleep_time)
					
				last_time = time()
				
				with self.state_lock:
					self.active_paths.clear()
					self.active_paths_ids.clear()
					self.check_active_flows()
					
				self.comms.broadcast_flows(self.active_paths)
				
			with self.state_lock:
				self.apply_bandwidth()
				self.flow_accumulator.clear()
	
	
	def apply_flow(self, flow):
		INDICES = 0
		BW = 1
		link_indices = flow[INDICES]
		bandwidth = flow[BW]
		
		# Calculate RTT of this flow
		rtt = 0
		for index in link_indices:
			for link in self.graph.links:
				if link.index == index:
					with link.lock:
						rtt += (link.latency * 2)
						
		# Add it to the link's flows
		for index in link_indices:
			for link in self.graph.links:
				if link.index == index:
					link.flows.append((rtt, bandwidth))


	def apply_bandwidth(self):
		INDICES = 0
		RTT = 0
		BW = 1
		
		# First update the graph with the information of the flows
		active_links = []
		
		# Add the info about our flows
		for path in self.active_paths:
			for link in path.links:
				active_links.append(link)
				link.flows.append((path.RTT, path.used_bandwidth))
		
		# Add the info about others flows
		for key in self.flow_accumulator:
			flow = self.flow_accumulator[key]
			link_indices = flow[INDICES]
			self.apply_flow(flow)
			for index in link_indices:
				for link in self.graph.links:
					if link.index == index:  # graph.links[x] does not necessarily contain the link with index x anymore
						active_links.append(link)
		
		# Now apply the RTT Aware Min-Max to calculate the new BW
		for id in self.active_paths_ids:
			path = self.graph.paths_by_id[id]
			with path.lock:
				max_bandwidth = path.max_bandwidth
				for link in path.links:
					rtt_reverse_sum = 0
					for flow in link.flows:
						rtt_reverse_sum += (1.0 / flow[RTT])
					max_bandwidth_on_link = []
					# calculate our bandwidth
					max_bandwidth_on_link.append(((1.0 / link.flows[0][RTT]) / rtt_reverse_sum) * link.bandwidth_bps)
					
					# Maximize link utilization to 100%
					spare_bw = link.bandwidth_bps - max_bandwidth_on_link[0]
					our_share = max_bandwidth_on_link[0] / link.bandwidth_bps
					hungry_usage_sum = our_share  # We must be before the loop to avoid division by zero
					for i in range(1, len(link.flows)):
						flow = link.flows[i]
						# calculate the bandwidth for everyone
						max_bandwidth_on_link.append(((1.0 / flow[RTT]) / rtt_reverse_sum) * link.bandwidth_bps)
						
						# Check if a flow is "hungry" (wants more than its allocated share)
						if flow[BW] > max_bandwidth_on_link[i]:
							spare_bw -= max_bandwidth_on_link[i]
							hungry_usage_sum += max_bandwidth_on_link[i] / link.bandwidth_bps
						else:
							spare_bw -= flow[BW]
					
					normalized_share = our_share / hungry_usage_sum  # we get a share of the spare proportional to our RTT
					maximized = max_bandwidth_on_link[0] + (normalized_share * spare_bw)
					if maximized > max_bandwidth_on_link[0]:
						max_bandwidth_on_link[0] = maximized
					
					# If this link restricts us more than previously try to assume this bandwidth as the max
					if max_bandwidth_on_link[0] < max_bandwidth:
						max_bandwidth = max_bandwidth_on_link[0]
				
				if max_bandwidth <= path.max_bandwidth and max_bandwidth != path.current_bandwidth:
					if max_bandwidth <= path.current_bandwidth:
						path.current_bandwidth = max_bandwidth  # if its less then we now for sure it is correct
					else:
						#  if it is more then we have to be careful, it might be a spike due to lost metadata
						path.current_bandwidth = EmulationManager.ONE_MINUS_ALPHA * path.current_bandwidth + \
												 EmulationManager.ALPHA * max_bandwidth
					service = path.links[-1].destination
					PathEmulation.change_bandwidth(service, path.current_bandwidth)
		
		# clear the state on the graph
		for link in active_links:
			link.flows.clear()

			
	def check_active_flows(self):
		current_time = time()
		self.check_flows_time_delta = current_time - self.last_time
		self.last_time = current_time
		PathEmulation.update_usage()
		
		
	def collect_own_flow(self, ip, sent_bytes):
		host = self.graph.hosts_by_ip[ip]
		# Calculate current throughput
		if sent_bytes < host.last_bytes:
			bytes_delta = sent_bytes  # in case of overflow ignore the bytes before the overflow
		else:
			bytes_delta = sent_bytes - host.last_bytes
			
		bits = bytes_delta * 8
		throughput = bits / self.check_flows_time_delta
		host.last_bytes = sent_bytes
		
		# Get the network path
		if host in self.graph.paths:  # some services are not reachable, test for that
			path = self.graph.paths[host]
			
			# Check if this is an active flow
			if throughput <= (path.max_bandwidth * EmulationManager.ERROR_MARGIN):
				path.used_bandwidth = 0
				return
			
			# This is an active flow
			# msg = "\n" + self.graph.root.name + "--" + host.name + ":" + str(throughput) + "\n"
			# msg += "going through links: "
			# for link in path.links:
			# 	msg += link.source.name  + "--" + link.destination.name + "--"
			# print_message(msg)
			
			path.used_bandwidth = throughput
			self.active_paths.append(path)
			self.active_paths_ids.append(path.id)
	
			# self.comms.add_flow(throughput, path.links)

		
	def accumulate_flow(self, bandwidth, link_indices):
		"""
		This method adds a flow to the accumulator (Note: it doesnt grab the lock)
		:param bandwidth: int
		:param link_indices: List[int]
		"""
		BW = 1
		key = str(link_indices[0]) + ":" + str(link_indices[-1])
		if key in self.flow_accumulator:
			flow = self.flow_accumulator[key]
			flow[BW] = bandwidth
		else:
			self.flow_accumulator[key] = [link_indices, bandwidth]
	
	
	# link_indices contains the indices of all links on a given path with that bandwidth
	# ie. len(link_indices) = # of links in path
	def collect_flow(self, bandwidth, link_indices):
		"""
		This method collects a flow from other nodes, it checks if it is interesting and if so calls accumulate_flow
		:param bandwidth: int
		:param link_indices: List[int]
		"""
		# TODO the return value is no longer useful
		
		# Check if this flow is interesting to us
		with self.state_lock:
			self.accumulate_flow(bandwidth, link_indices)
		return True


