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
	POOL_PERIOD = 'NEED_POOL_PERIOD'
	ITERATION_COUNT = 'NEED_ITERATION_COUNT'


class CONTAINER:
	id = None
	pid = ""
	client = None  # type: docker.DockerClient
	ll = None  # type: docker.APIClient
	container = None
	process = None


def start_experiment():
	# Temporary hack to start the experiment
	#subprocess.run('echo "done" > /tmp/readypipe', shell=True)
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
	#arg = ['/bin/sh'] + ['-c'] + [command]
	command.replace('"', '\\"')
	command.replace("'", "\\'")
	arg = ['echo ' + command + ' > /tmp/NEED_hang']
	print_message(arg[0])
	CONTAINER.container.exec_run(['/bin/sh'] + ['-c'] + arg, detach=True)


def stop_experiment():
	# kill all but pid 1 (this might create zombies)
	Popen(
		["nsenter", "-t", str(CONTAINER.pid), "-p", "-m", "/bin/sh", "-c", "kill -2 -1"]
	).wait()
	return


def crash_experiment():
	# kill all but pid 1 (this might create zombies)
	Popen(
		["nsenter", "-t", str(CONTAINER.pid), "-p", "-m", "/bin/sh", "-c", "kill -9 -1"]
	).wait()
	return


def setup_container(id, pid):
	CONTAINER.id = id
	CONTAINER.pid = pid
	CONTAINER.client = docker.DockerClient(base_url='unix:/' + DOCKER_SOCK)
	CONTAINER.ll = docker.APIClient(base_url='unix:/' + DOCKER_SOCK)
	CONTAINER.container = CONTAINER.client.containers.get(id)


def ip2int(addr):
	return struct.unpack("!I", socket.inet_aton(addr))[0]


def int2ip(addr):
	return socket.inet_ntoa(struct.pack("!I", addr))


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
	sleep(10)
	exit(-1)
