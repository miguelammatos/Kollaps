#! /usr/bin/python3

# from docker.types import Mount
import docker
from kubernetes import client, config

import os
import sys
import socket
import json, pprint

from subprocess import Popen
from multiprocessing import Process
from time import sleep
from signal import pause
# from shutil import copy

from need.NEEDlib.utils import int2ip, ip2int
from need.NEEDlib.utils import print_message, print_error, print_and_fail, print_named, print_error_named
from need.NEEDlib.utils import DOCKER_SOCK, TOPOLOGY, LOCAL_IPS_FILE, REMOTE_IPS_FILE, GOD_IPS_SHARE_PORT


BUFFER_LEN = 1024

gods = {}
ready_gods = {}


def broadcast_ips(local_ips_list, number_of_gods):
	global ready_gods
	
	sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sender.bind(('', GOD_IPS_SHARE_PORT + 1))
	
	ip_prefix = socket.gethostbyname(socket.gethostname()).rsplit('.', 1)[0] + "."
	
	msg = ' '.join(local_ips_list)
	
	while True:
		for i in range(1, 254):
			sender.sendto(bytes(msg, encoding='utf8'), (ip_prefix + str(i), GOD_IPS_SHARE_PORT))
			
		sleep(0.5)
		#tries += 1
		
		
def broadcast_ready(number_of_gods):
	global ready_gods
	
	sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sender.bind(('', GOD_IPS_SHARE_PORT + 2))
	
	ip_prefix = socket.gethostbyname(socket.gethostname()).rsplit('.', 1)[0] + "."
	
	while True:
		for i in range(1, 254):
			sender.sendto(bytes("READY", encoding='utf8'), (ip_prefix + str(i), GOD_IPS_SHARE_PORT))
		
		sleep(0.5)


def resolve_ips(client, low_level_client):
	global gods
	global ready_gods

	try:
		number_of_gods = len(low_level_client.nodes())
		local_ips_list = []
		own_ip = socket.gethostbyname(socket.gethostname())
		
		print_named("god", "ip: " + str(own_ip))
		print_named("god", "number of gods: " + str(number_of_gods))
		
		orchestrator = os.getenv('NEED_ORCHESTRATOR', 'swarm')
		if orchestrator == 'kubernetes':
			
			while len(local_ips_list) <= 0:
				need_pods = client.list_namespaced_pod('default')
				for pod in need_pods.items:
					local_ips_list.append(pod.status.pod_ip)
					
				if None in local_ips_list:
					local_ips_list.clear()
				
				#if pod.status.pod_ip is None:
					#local_ips_list.append("111.111.111.111")
				#else:
					#local_ips_list.append(pod.status.pod_ip)
			#need_pods = client.list_namespaced_pod('default')
			#tries = 100
			#for pod in need_pods.items:
				#while pod.status.pod_ip is None and tries > 0:
					#sleep(1)
					#tries -= 1
					##print_named("god", "pod.status.pod_ip is None")
				#local_ips_list.append(pod.status.pod_ip)
				
				##if pod.status.pod_ip is None:
					##local_ips_list.append("111.111.111.111")
				##else:
					##local_ips_list.append(pod.status.pod_ip)
			
		else:
			if orchestrator != 'swarm':
				print_named("bootstrapper", "Unrecognized orchestrator. Using default docker swarm.")
			
			containers = client.containers.list()
			for container in containers:
				test_net_config = low_level_client.inspect_container(container.id)['NetworkSettings']['Networks'].get('test_overlay')
				
				if test_net_config is not None:
					container_ip = test_net_config["IPAddress"]
					if container_ip not in local_ips_list:
						local_ips_list.append(container_ip)
		
		local_ips_list.remove(own_ip)

		ip_broadcast = Process(target=broadcast_ips, args=(local_ips_list, number_of_gods, ))
		ip_broadcast.start()
		
		receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		# receiver.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		# receiver.bind(('0.0.0.0', GOD_IPS_SHARE_PORT))
		receiver.bind(('', GOD_IPS_SHARE_PORT))

		while len(gods) < number_of_gods:
			data, addr = receiver.recvfrom(BUFFER_LEN)
			god_ip = int(ip2int(addr[0]))
			
			if not data.startswith(b"READY"):
				list_of_ips = [ip2int(ip) for ip in data.decode("utf-8").split()]
	
				if god_ip not in gods:
					gods[god_ip] = list_of_ips
					print_named("god", f"{addr[0]} :: {data}")
					
			else:
				ready_gods[god_ip] = "READY"
				print_named("god", f"{addr[0]} :: READY")

		
		ready_broadcast = Process(target=broadcast_ready, args=(number_of_gods,))
		ready_broadcast.start()

		while len(ready_gods) < number_of_gods:
			data, addr = receiver.recvfrom(BUFFER_LEN)
			god_ip = int(ip2int(addr[0]))
			
			# if data.split()[0] == "READY":
			if data.startswith(b"READY"):
				ready_gods[god_ip] = "READY"
				print_named("god", f"{addr[0]} :: READY")
				

		ip_broadcast.terminate()
		ready_broadcast.terminate()
		ip_broadcast.join()
		ready_broadcast.join()
		
		
		own_ip = ip2int(own_ip)
		
		local_god = {}
		local_god[own_ip] = gods[own_ip]
		with open(LOCAL_IPS_FILE, 'w') as l_file:
			l_file.write(json.dumps(local_god))
		
		del gods[own_ip]
		with open(REMOTE_IPS_FILE, 'w') as r_file:
			r_file.write(json.dumps(gods))
		
		
		with open(LOCAL_IPS_FILE, 'r') as file:
			new_dict = json.load(file)
			print("\n[Py (god)] local:")
			pprint.pprint(new_dict)
			sys.stdout.flush()
		
		with open(REMOTE_IPS_FILE, 'r') as file:
			new_dict = json.load(file)
			print("\n[Py (god)] remote:")
			pprint.pprint(new_dict)
			sys.stdout.flush()
	
		return gods
	
	except Exception as e:
		print_error_named("god", e)
		sys.stdout.flush()
		sys.exit(-1)


def kubernetes_bootstrapper():
	mode = sys.argv[1]
	label = sys.argv[2]
	god_id = None  # get this, it will be argv[3]
	
	# Connect to the local docker daemon
	config.load_incluster_config()
	kubeAPIInstance = client.CoreV1Api()
	lowLevelClient = docker.APIClient(base_url='unix:/' + DOCKER_SOCK)
	# need_pods = kubeAPIInstance.list_namespaced_pod('default')
	
	while not god_id:
		need_pods = kubeAPIInstance.list_namespaced_pod('default')
		try:
			for pod in need_pods.items:
				if "boot" + label in pod.metadata.labels:
					god_id = pod.status.container_statuses[0].container_id[9:]
		
		except Exception as e:
			print_error_named("god", e)
			sys.stdout.flush()
			sleep(1)  # wait for the Kubernetes API


	# next we start the Aeron Media Driver
	aeron_media_driver = None
	try:
		aeron_media_driver = Popen('/usr/bin/Aeron/aeronmd')
		print_named("god", "started aeron_media_driver.")
	
	except Exception as e:
		print_error_named("bootstrapper", "failed to start aeron media driver.")
		print_and_fail(e)

	
	# We are finally ready to proceed
	print("Bootstrapping all local containers with label " + label)
	sys.stdout.flush()
	
	already_bootstrapped = {}
	instance_count = 0
	
	resolve_ips(kubeAPIInstance, lowLevelClient)
	
	need_pods = kubeAPIInstance.list_namespaced_pod('default')
	for pod in need_pods.items:
		try:
			# inject the Dashboard into the dashboard container
			for key, value in pod.metadata.labels.items():
				if "dashboard" in value:
					container_id = pod.status.container_statuses[0].container_id[9:]
					container_pid = lowLevelClient.inspect_container(container_id)["State"]["Pid"]
					
					cmd = ["nsenter", "-t", str(container_pid), "-n", "/usr/bin/python3", "/usr/bin/NEEDDashboard", TOPOLOGY]
					dashboard_instance = Popen(cmd)
					
					instance_count += 1
					print_named("god", "Done bootstrapping dashboard.")
					already_bootstrapped[container_id] = dashboard_instance
					
				if "logger" in value:
					container_id = pod.status.container_statuses[0].container_id[9:]
					container_pid = lowLevelClient.inspect_container(container_id)["State"]["Pid"]
					
					cmd = ["nsenter", "-t", str(pid), "-n", "/usr/bin/python3", "/usr/bin/NEEDLogger", TOPOLOGY]
					dashboard_instance = Popen(cmd)
					
					instance_count += 1
					print_named("god", "Done bootstrapping logger.")
					already_bootstrapped[container_id] = dashboard_instance

					break
		
		except Exception as e:
			print_error_named("god", "supervisor bootstrapping failed:\n" + str(e) + "\n... will try again.")
			continue

	
	while True:
		try:
			need_pods = kubeAPIInstance.list_namespaced_pod('default')
			running = 0  # running container counter, we stop the god if there are 0 same experiment containers running
			
			# check if containers need bootstrapping
			for pod in need_pods.items:
				container_id = pod.status.container_statuses[0].container_id[9:]
				
				if label in pod.metadata.labels:
					running += 1
					
				if label in pod.metadata.labels \
						and container_id not in already_bootstrapped \
						and pod.status.container_statuses[0].state.running is not None:
					
					try:
						container_pid = lowLevelClient.inspect_container(container_id)["State"]["Pid"]
						emucore_instance = Popen(
							["nsenter", "-t", str(container_pid), "-n",
							"/usr/bin/python3", "/usr/bin/NEEDemucore", TOPOLOGY, str(container_id),
							str(container_pid)]
						)
						instance_count += 1
						already_bootstrapped[container_id] = emucore_instance
					
					except:
						print("Bootstrapping failed... will try again.")
						sys.stdout.flush()
						sys.stderr.flush()
				
				# Check for bootstrapper termination
				if container_id == god_id and pod.status.container_statuses[0].state.running is not None:
					running += 1
					
			# Do some reaping
			for key in already_bootstrapped:
				already_bootstrapped[key].poll()
			
			# Clean up and stop
			if running == 0:
				for key in already_bootstrapped:
					if already_bootstrapped[key].poll() is not None:
						already_bootstrapped[key].kill()
						already_bootstrapped[key].wait()
						
				print_named("god", "God terminating.")
				
				if aeron_media_driver:
					aeron_media_driver.terminate()
					print_named("god", "aeron_media_driver terminating.")
					aeron_media_driver.wait()
				
				sys.stdout.flush()
				return
			
			sleep(5)
		
		except Exception as e:
			sys.stdout.flush()
			print_error(e)
			sleep(1)



def docker_bootstrapper():
	
	mode = sys.argv[1]
	label = sys.argv[2]
	
	# Connect to the local docker daemon
	client = docker.DockerClient(base_url='unix:/' + DOCKER_SOCK)
	lowLevelClient = docker.APIClient(base_url='unix:/' + DOCKER_SOCK)


	if mode == "-s":
		while True:
			try:
				# If we are bootstrapper:
				us = None
				while not us:
					containers = client.containers.list()
					for container in containers:
						if "boot"+label in container.labels:
							us = container
					
					sleep(1)
				
				boot_image = us.image
				
				inspect_result = lowLevelClient.inspect_container(us.id)
				env = inspect_result["Config"]["Env"]
				
				print_message("[Py (bootstrapper)] ip: " + str(socket.gethostbyname(socket.gethostname())))
				
				# create a "God" container that is in the host's Pid namespace
				client.containers.run(image=boot_image,
									command=["-g", label, str(us.id)],
									privileged=True,
									pid_mode="host",
									shm_size=4000000000,
									remove=True,
									environment=env,
									# ports={"55555/udp":55555, "55556/udp":55556},
									# volumes={DOCKER_SOCK: {'bind': DOCKER_SOCK, 'mode': 'rw'}},
									volumes_from=[us.id],
									# network_mode="container:"+us.id,  # share the network stack with this container
									# network='olympus_overlay',
									network='test_overlay',
									labels=["god" + label],
									detach=True)
									# stderr=True,
									# stdout=True)
				pause()
				
				return
			
			except Exception as e:
				print_error(e)
				sleep(5)
				continue  # If we get any exceptions try again
	
	
	# We are the god container
	# first thing to do is copy over the topology
	while True:
		try:
			bootstrapper_id = sys.argv[3]
			bootstrapper_pid = lowLevelClient.inspect_container(bootstrapper_id)["State"]["Pid"]
			cmd = ["/bin/sh", "-c",
				"nsenter -t " + str(bootstrapper_pid) + " -m cat " + TOPOLOGY + " | cat > " + TOPOLOGY]
			Popen(cmd).wait()
			break
		
		except Exception as e:
			print_error(e)
			sleep(5)
			continue
			
	
	# next we start the Aeron Media Driver
	aeron_media_driver = None
	try:
		aeron_media_driver = Popen('/usr/bin/Aeron/aeronmd')
		print_named("god", "started aeron_media_driver.")
	
	except Exception as e:
		print_error("[Py (bootstrapper)] failed to start aeron media driver.")
		print_and_fail(e)
	
	
	# we are finally ready to proceed
	print_named("bootstrapper", "Bootstrapping all local containers with label " + label)
	already_bootstrapped = {}
	instance_count = 0
	
	resolve_ips(client, lowLevelClient)
	
	bootstrapped_dashboard = False
	bootstrapped_logger = False

	containers = client.containers.list()
	for container in containers:
		try:
			# inject the Dashboard into the dashboard container
			for key, value in container.labels.items():
				if not bootstrapped_dashboard and "dashboard" in value:
					id = container.id
					inspect_result = lowLevelClient.inspect_container(id)
					pid = inspect_result["State"]["Pid"]
					print("[Py (god)] Bootstrapping dashboard ...")
					sys.stdout.flush()
					
					cmd = ["nsenter", "-t", str(pid), "-n", "/usr/bin/python3", "/usr/bin/NEEDDashboard", TOPOLOGY]
					dashboard_instance = Popen(cmd)
					
					instance_count += 1
					print("[Py (god)] Done bootstrapping dashboard.")
					sys.stdout.flush()
					already_bootstrapped[container.id] = dashboard_instance
					
					bootstrapped_dashboard = True
					
					
				elif not bootstrapped_logger and "logger" in value:
					id = container.id
					inspect_result = lowLevelClient.inspect_container(id)
					pid = inspect_result["State"]["Pid"]
					print_named("god", "Bootstrapping logger ...")
					sys.stdout.flush()
					
					cmd = ["nsenter", "-t", str(pid), "-n", "/usr/bin/python3", "/usr/bin/NEEDLogger", TOPOLOGY]
					dashboard_instance = Popen(cmd)
					
					instance_count += 1
					print("[Py (god)] Done bootstrapping logger.")
					sys.stdout.flush()
					already_bootstrapped[container.id] = dashboard_instance
					bootstrapped_logger = True
		
		except Exception as e:
			print_error("[Py (god)] supervisor bootstrapping failed:\n" + str(e) + "\n... will try again.")
			continue
			
			
	while True:
		try:
			running = 0  # running container counter, we stop the god if there are 0 same experiment containers running
			
			# check if containers need bootstrapping
			containers = client.containers.list()
			for container in containers:
				
				if label in container.labels:
					running += 1
		
				if label in container.labels \
						and container.id not in already_bootstrapped \
						and container.status == "running":
					# inject emucore into application containers
					try:
						id = container.id
						inspect_result = lowLevelClient.inspect_container(id)
						pid = inspect_result["State"]["Pid"]
						
						print_message("[Py (god)] Bootstrapping " + container.name + " ...")
						
						cmd = ["nsenter", "-t", str(pid), "-n", "/usr/bin/python3", "/usr/bin/NEEDemucore", TOPOLOGY, str(id), str(pid)]
						emucore_instance = Popen(cmd)
						
						instance_count += 1
						print_message("[Py (god)] Done bootstrapping " + container.name)
						already_bootstrapped[container.id] = emucore_instance
					
					except:
						print_error("[Py (god)] Bootstrapping failed... will try again.")
					
				# Check for bootstrapper termination
				if container.id == bootstrapper_id and container.status == "running":
					running += 1
			
			# Do some reaping
			for key in already_bootstrapped:
				already_bootstrapped[key].poll()

			# Clean up and stop
			if running == 0:
				for key in already_bootstrapped:
					if already_bootstrapped[key].poll() is not None:
						already_bootstrapped[key].kill()
						already_bootstrapped[key].wait()
						
				print_named("god", "God terminating.")
				
				if aeron_media_driver:
					aeron_media_driver.terminate()
					print_named("god", "aeron_media_driver terminating.")
					aeron_media_driver.wait()
				
				sys.stdout.flush()
				return
			
			sleep(5)
		
		except Exception as e:
			sys.stdout.flush()
			print_error(e)
			sleep(5)
			continue




if __name__ == '__main__':

	if len(sys.argv) < 3:
		print("If you are calling " + sys.argv[0] + " from your workstation stop.")
		print("This should only be used inside containers")
		exit(-1)
	
	orchestrator = os.getenv('NEED_ORCHESTRATOR', 'swarm')
	print_named("bootstrapper", "orchestrator: " + orchestrator)
	
	if orchestrator == 'kubernetes':
		kubernetes_bootstrapper()
		
	else:
		if orchestrator != 'swarm':
			print_named("bootstrapper", "Unrecognized orchestrator. Using default docker swarm.")
		
		docker_bootstrapper()



# def start_dashboard(client, lowLevelClient, instance_count):
# 	dashboard_bootstrapped = False
# 	while not dashboard_bootstrapped:
#
# 		containers = client.containers.list()
# 		for container in containers:
# 			try:
# 				# inject the Dashboard into the dashboard container
# 				for key, value in container.labels.items():
# 					if "dashboard" in value:
# 						id = container.id
# 						inspect_result = lowLevelClient.inspect_container(id)
# 						pid = inspect_result["State"]["Pid"]
# 						print("[Py (god)] Bootstrapping dashboard " + container.name + " ...")
# 						sys.stdout.flush()
#
# 						cmd = ["nsenter", "-t", str(pid), "-n", "/usr/bin/python3", "/usr/bin/NEEDDashboard", TOPOLOGY]
# 						dashboard_instance = Popen(cmd)
#
# 						instance_count += 1
# 						print("[Py (god)] Done bootstrapping " + container.name)
# 						sys.stdout.flush()
# 						already_bootstrapped[container.id] = dashboard_instance
#
# 						dashboard_bootstrapped = True
# 						break
#
#
# 			except Exception as e:
# 				print("[Py (god)] Dashboard bootstrapping failed:\n" + str(e) + "\n... will try again.")
# 				sys.stdout.flush()
# 				sys.stderr.flush()
# 				sleep(5)
# 				continue

