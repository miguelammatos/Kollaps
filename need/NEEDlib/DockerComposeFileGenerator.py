
from need.NEEDlib.NetGraph import NetGraph
from need.NEEDlib.utils import DOCKER_SOCK, print_error_named, print_and_fail, get_short_id
from uuid import uuid4
import random

import docker


large_xml_file = True


class DockerComposeFileGenerator:
	
	shm_size = 8000000000
	aeron_lib_path = "/home/daedalus/Documents/aeron4need/cppbuild/Release/lib/libaeronlib.so"
	
	threading_mode = 'SHARED'			# aeron uses 1 thread
	# threading_mode = 'SHARED_NETWORK'	# aeron uses 2 thread
	# threading_mode = 'DEDICATED'		# aeron uses 3 thread

	pool_period = 0.05
	iterations = 42			# doesnt matter, its here for legacy
	max_flow_age = 2
	
	
	def __init__(self, topology_file, graph):
		self.graph = graph  # type: NetGraph
		self.topology_file = topology_file
		self.experiment_UUID = str(uuid4())
		
	def print_header(self):
		print("version: \"3.3\"")
		print("services:")

	def print_bootstrapper(self, number_of_gods):
		print("  bootstrapper:")
		print("    image: " + self.graph.bootstrapper)
		print("    command: [\"-s\", \"" + self.experiment_UUID + "\"]")
		print("    deploy:")
		print("      mode: global")
		print("    environment:")
		print("      NEED_UUID: '" + self.experiment_UUID + "'")
		print("      NEED_ORCHESTRATOR: swarm")
		print("      NUMBER_OF_GODS: " + str(number_of_gods))
		print("      SHM_SIZE: " + str(self.shm_size))
		print("      AERON_LIB_PATH: " + self.aeron_lib_path)
		print("      AERON_THREADING_MODE: " + self.threading_mode)
		print("      AERON_TERM_BUFFER_LENGTH: " + str(2*64*1024*1024))		# must be multiple of 64*1024
		print("      AERON_IPC_TERM_BUFFER_LENGTH: " + str(2*64*1024*1024))	# must be multiple of 64*1024
		print("      POOL_PERIOD: " + str(self.pool_period))
		print("      ITERATIONS: " + str(self.iterations))
		print("      MAX_FLOW_AGE: " + str(self.max_flow_age))
		print("    labels:")
		print("      " + "boot"+self.experiment_UUID + ": \"true\"")
		print("    volumes:")
		if large_xml_file:
			print("      - '/home/ubuntu/NEED/" + self.topology_file + ":/topology.xml'")
		print("      - type: bind")
		print("        source: /var/run/docker.sock")
		print("        target: /var/run/docker.sock")
		if not large_xml_file:
			print("    configs:")
			print("      - source: topology")
			print("        target: /topology.xml")
			print("        uid: '0'")
			print("        gid: '0'")
			print("        mode: 0555")
		print("    networks:")
		print("      - NEEDnet")
		print("")

	def print_service(self, service_list):
		print("  " + service_list[0].name + "-" + self.experiment_UUID + ":")
		print("    image: " + service_list[0].image)
		if not service_list[0].supervisor:
			print('    entrypoint: ["/bin/sh", "-c", "mkfifo /tmp/NEED_hang; exec /bin/sh <> /tmp/NEED_hang #"]')
		if service_list[0].command is not None:
			print("    command: " + service_list[0].command)
		if service_list[0].supervisor_port > 0:
			print("    ports:")
			print('      - "' + str(service_list[0].supervisor_port) + ':' + str(service_list[0].supervisor_port) + '"')
		print("    hostname: " + service_list[0].name)  # + "-" + self.experiment_UUID) This might be the potential cause for the broadcast regression
		if not service_list[0].supervisor:
			print("    labels:")
			print("      " + self.experiment_UUID + ": \"true\"")
		print("    deploy:")
		print("      replicas: " + str(len(service_list)))
		if not service_list[0].supervisor:
			print("      endpoint_mode: dnsrr")
		print("    environment:")
		print("      NEED_UUID: '" + self.experiment_UUID + "'")
		print("      NEED_ORCHESTRATOR: swarm")
		
		if large_xml_file:
			print("    volumes:")
			print("      - '/home/ubuntu/NEED/" + self.topology_file + ":/topology.xml'")
			
		if service_list[0].supervisor and not large_xml_file:
			print("    configs:")
			print("      - source: topology")
			print("        target: /topology.xml")
			print("        uid: '0'")
			print("        gid: '0'")
			print("        mode: 0555")
			
		print("    networks:")
		print("      - NEEDnet")
		if service_list[0].supervisor:
			print("      - outside")

		print("")

	def print_configs(self):
		print("configs:")
		print("  topology:")
		print("    file: " + self.topology_file)
		print("")

	def print_networks(self):
		network = self.graph.links[0].network
		for link in self.graph.links:
			if link.network != network:
				print_and_fail("Multiple network support is not yet implemented!")

		print("networks:")
		print("  NEEDnet:")
		print("    external:")
		print("      name: " + network)
		print("  outside:")
		print("    driver: overlay")
		print("")


	def generate(self):
		number_of_gods = 0
		try:
			number_of_gods = len(docker.APIClient(base_url='unix:/' + DOCKER_SOCK).nodes())
			
		except Exception as e:
			msg = "DockerComposeFileGenerator.py requires special permissions in order to view cluster state.\n"
			msg += "please, generate the .yaml file on a manager node."
			print_error_named("compose_generator", msg)
			print_and_fail(e)
		
		self.print_header()
		self.print_bootstrapper(number_of_gods)
		for service in self.graph.services:
			self.print_service(self.graph.services[service])
		if not large_xml_file:
			self.print_configs()
		self.print_networks()
