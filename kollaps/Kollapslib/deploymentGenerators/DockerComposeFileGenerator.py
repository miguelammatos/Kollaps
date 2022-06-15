#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import docker
import os

from uuid import uuid4

from kollaps.Kollapslib.NetGraph import NetGraph
from kollaps.Kollapslib.utils import DOCKER_SOCK, print_error_named, print_and_fail
from kollaps.Kollapslib.XMLGraphParser import XMLGraphParser

large_xml_file = True


class DockerComposeFileGenerator:
	
	def __init__(self, topology_file, graph):
		self.graph = graph  # type: NetGraph
		self.topology_file = topology_file
		self.experiment_UUID = str(uuid4())

	def print_header(self):
		print("version: \"3.3\"")
		print("services:")
		
		
	def print_bootstrapper(self, number_of_gods, pool_period, max_flow_age, threading_mode, shm_size, aeron_lib_path, aeron_term_buffer_length, aeron_ipc_term_buffer_length, bw_emulation):
		print("  bootstrapper:")
		print("    image: " + self.graph.bootstrapper)
		print("    command: [\"-s\", \"" + self.experiment_UUID + "\"]")
		print("    deploy:")
		print("      mode: global")
		print("    environment:")
		print("      KOLLAPS_UUID: '" + self.experiment_UUID + "'")
		print("      KOLLAPS_ORCHESTRATOR: swarm")
		print("      NUMBER_OF_GODS: " + str(number_of_gods))
		if bw_emulation is False:
			print("      RUNTIME_EMULATION: 'false'")
		print("      POOL_PERIOD: " + str(pool_period))
		print("      MAX_FLOW_AGE: " + str(max_flow_age))
		print("    labels:")
		print("      " + "boot"+self.experiment_UUID + ": \"true\"")
		print("    volumes:")
		print("      - '" + "/lib/modules:/lib/modules/'")
		print("      - '" + "/usr/src:/usr/src/'")
		print("      - '" + "/sys/:/sys/'")
		if large_xml_file:
			print("      - '" + os.path.abspath(self.topology_file) + ":/topology.xml'")
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
		print("      - KollapsNet")
		print("")

	def print_service(self, service_list):
		print("  " + service_list[0].name + "-" + self.experiment_UUID + ":")
		print("    image: " + service_list[0].image)
		if not service_list[0].supervisor:
			print('    entrypoint: ["/bin/sh", "-c", "mkfifo /tmp/Kollaps_hang; exec /bin/sh <> /tmp/Kollaps_hang #"]')
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
		print("      KOLLAPS_UUID: '" + self.experiment_UUID + "'")
		print("      KOLLAPS_ORCHESTRATOR: swarm")
			
		if service_list[0].supervisor and not large_xml_file:
			print("    configs:")
			print("      - source: topology")
			print("        target: /topology.xml")
			print("        uid: '0'")
			print("        gid: '0'")
			print("        mode: 0555")
			
		print("    networks:")
		print("      - KollapsNet")
		if service_list[0].supervisor:
			print("      - outside")

		print("")
		
	def print_configs(self):
		if not large_xml_file:
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
		print("  KollapsNet:")
		print("    external:")
		print("      name: " + network)
		print("  outside:")
		print("    driver: overlay")
		print("")


	def generate(self, pool_period, max_flow_age, threading_mode, shm_size, aeron_lib_path, aeron_term_buffer_length, aeron_ipc_term_buffer_length, bw_emulation=True):
		number_of_gods = 0
		XMLGraphParser(self.topology_file, self.graph,"container")
		
		try:
			number_of_gods = len(docker.APIClient(base_url='unix:/' + DOCKER_SOCK).nodes())
			
		except Exception as e:
			msg = "DockerComposeFileGenerator.py requires special permissions in order to view cluster state.\n"
			msg += "please, generate the .yaml file on a manager node."
			print_error_named("compose_generator", msg)
			print_and_fail(e)
		
		self.print_header()
		self.print_bootstrapper(number_of_gods, pool_period, max_flow_age, threading_mode, shm_size, aeron_lib_path, aeron_term_buffer_length, aeron_ipc_term_buffer_length, bw_emulation)
		for service in self.graph.services:
			self.print_service(self.graph.services[service])
		self.print_configs()
		self.print_networks()
