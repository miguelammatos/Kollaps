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
import subprocess
import sys
import struct
import string
import random
import socket
import docker
import os
from subprocess import Popen
from time import sleep

BYTE_LIMIT = 255
SHORT_LIMIT = 65535
# INT_LIMIT = 4294967296

DOCKER_SOCK = "/var/run/docker.sock"

TOPOLOGY = "/topology.xml"
LOCAL_IPS_FILE = "/local_ips.txt"
REMOTE_IPS_FILE = "/remote_ips.txt"

# PG this path is because aeron is compiled with cmake and it uses relative paths
AERON_LIB_PATH = "/home/daedalus/Documents/aeron4need/cppbuild/Release/lib/libaeronlib.so"

GOD_IPS_SHARE_PORT = 55555


class ENVIRONMENT:
	NETWORK_INTERFACE = 'NETWORK_INTERFACE'
	BROADCAST = 'BROADCAST_ADDRESS'
	POOL_PERIOD = 'KOLLAPS_POOL_PERIOD'
	ITERATION_COUNT = 'KOLLAPS_ITERATION_COUNT'


class CONTAINER:
	id = None
	pid = ""
	client = None  # type: docker.DockerClient
	ll = None  # type: docker.APIClient
	container = None
	process = None
	startscript = ""
	stopscript = ""
	handlerpid = 0
	rustcomms = None
	core = None
	links_index = None

def start_experiment():
	if CONTAINER.startscript != "":
		start_experiment_baremetal()
	else:
		inspect = CONTAINER.ll.inspect_container(CONTAINER.id)
		cmd = inspect['Config']['Cmd']
		image = inspect['Image']
		image_inspect = CONTAINER.ll.inspect_image(image)
		entrypoint = image_inspect['Config']['Entrypoint']
		if entrypoint is None:
			entrypoint = [""]
		if cmd is None:
			cmd = image_inspect['Config']['Cmd']
		elif len(cmd) == 0:
			cmd = image_inspect['Config']['Cmd']
		if cmd is None:
			command = ' '.join(entrypoint)
		else:
			command = ' '.join(entrypoint + cmd)
		command.replace('"', '\\"')
		command.replace("'", "\\'")
		arg = ['echo ' + command + ' > /tmp/Kollaps_hang']
		print_message("['/bin/sh']" + "['-c']" + str(arg))
		#CONTAINER.container.exec_run(['/bin/sh'] + ['-c'] + arg, detach=True)

def start_experiment_baremetal():
	print_message("Starting script with name " + CONTAINER.startscript)
	cmd = [CONTAINER.startscript]
	Popen(cmd)

def setup_rustcomms(rustcomms):
	CONTAINER.rustcomms = rustcomms

def stop_experiment():
	if CONTAINER.handlerpid != 0:
		try:
			# if user inserted stop script
			if CONTAINER.stopscript != "":
				print_message("stopping script with pid " + str(CONTAINER.scriptpid))
				cmd = [CONTAINER.stopscript]
				Popen(cmd)
			print_message("stopping handler with pid " + str(CONTAINER.handlerpid))
			Popen(
				["sudo" ,"kill",str(CONTAINER.handlerpid)]
			).wait()
			print_message("stopped handler with pid " + str(CONTAINER.handlerpid))
		except Exception as e:
			print_error("[Py (god)] failed to stop experiment.")
			print_and_fail(e)
	# kill all but pid 1 (this might create zombies)
	else:
		Popen(
		["nsenter", "-t", str(CONTAINER.pid), "-p", "-m", "/bin/sh", "-c", "kill -2 -1"]
		).wait()
		return


def crash_experiment():
	#if CONTAINER.handlerpid != 0:
		#kill all but pid 1 (this might create zombies)
	if CONTAINER.handlerpid == 0:
		CONTAINER.rustcomms.mark_shutdown()
		print_message("SENDING CRASH MESSAGE TO RUST")
		CONTAINER.rustcomms.flush_shutdown()
		# Popen(
		# 	["nsenter", "-t", str(CONTAINER.pid), "-p", "-m", "/bin/sh", "-c", "kill -9 -1"]
		# ).wait()
		return


def setup_container(id,pid):
	CONTAINER.id = id
	#for baremetal pid is rustmanager
	CONTAINER.client = docker.DockerClient(base_url='unix:/' + DOCKER_SOCK)
	CONTAINER.ll = docker.APIClient(base_url='unix:/' + DOCKER_SOCK)
	CONTAINER.container = CONTAINER.client.containers.get(id)
	CONTAINER.pid = pid

def setup_baremetal(handlerpid,startscript,stopscript):
	CONTAINER.handlerpid = handlerpid
	CONTAINER.startscript = startscript
	CONTAINER.stopscript = stopscript


def setup_script(script):
	CONTAINER.script = script

def setup_pid(pid):
	CONTAINER.pid = pid


def ip2int(addr):
	return struct.unpack("!I", socket.inet_aton(addr))[0]


def int2ip(addr):
	return socket.inet_ntoa(struct.pack("!I", addr))


def ip2intbig(addr):
	return struct.unpack("<I", socket.inet_aton(addr))[0]


def int2ipbig(addr):
	return socket.inet_ntoa(struct.pack("<I", addr))


def get_short_id(size=4, chars=string.ascii_uppercase + string.digits):
	return ''.join(random.choice(chars) for _ in range(size))


def list_compare(list1, list2):
	return (list1 > list2) - (list1 < list2)


def get_own_ip(graph):
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	last_ip = None
	# Connect to at least 2 to avoid using our loopback ip
	for int_ip in graph.hosts_by_ip:
		s.connect((int2ip(int_ip), 1))
		new_ip = s.getsockname()[0]
		if new_ip == last_ip:
			break
		last_ip = new_ip
	return last_ip

def add_ip(ip):
    print_named("god","writing ip " + str(ip))
    file = open("/tmp/topoinfo", "a")
    file.write(str(ip)+"\n")
    file.close()

def write_ips(graph):
	file = open("/remote_ips.txt", "a")
	own_ip = get_own_ip(graph)
	for int_ip in graph.hosts_by_ip:
		if int_ip != ip2int(own_ip):
			file.write(str(int_ip)+"\n")
	file.close()

def print_error(message):
	print("ERROR: " + str(message), file=sys.stderr)
	sys.stderr.flush()


def print_error_named(who, message):
	print("[Py (" + str(who) + ")] " + "ERROR: " + str(message), file=sys.stderr)
	sys.stderr.flush()


def print_message(message):
	print(str(message), file=sys.stdout)
	sys.stdout.flush()


def print_named(who, msg):
	print("[Py (" + str(who) + ")] " + str(msg), file=sys.stdout)
	sys.stdout.flush()


def print_identified(graph, msg):
	print("[Py (" + graph.root.name + ") " + str(get_own_ip(graph)) + "] " + str(msg), file=sys.stdout)
	sys.stdout.flush()


def print_and_fail(msg):
	message = msg.message if hasattr(msg, 'message') else msg
	print("An error occured, terminating!", file=sys.stderr)
	print("Error Message: " + str(message), file=sys.stderr)
	sys.stdout.flush()
	sys.stderr.flush()
	sleep(1)
	exit(-1)
