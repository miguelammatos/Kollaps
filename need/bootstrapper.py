#! /usr/bin/python3

import docker
# from docker.types import Mount
import socket
import json, pprint
from multiprocessing import Process
from time import sleep
from signal import pause
from sys import argv, stdout, stderr
from subprocess import Popen
# from shutil import copy
from need.NEEDlib.utils import int2ip, ip2int

UDP_PORT = 55555
BUFFER_LEN = 512


def broadcast_ips(local_ips_list):
	
	sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sender.bind(('', UDP_PORT+1))
	
	# msg = "JOIN " + str(socket.gethostbyname(socket.gethostname()))
	msg = ' '.join(local_ips_list)
	
	tries = 0
	while tries < 4:
		for i in range(1, 254):
			sender.sendto(bytes(msg, encoding='utf8'), ('10.1.0.'+str(i), UDP_PORT))
			# sender.sendto(bytes(msg, encoding='utf8'), ('172.12.42.'+str(i), UDP_PORT))

		sleep(0.5)
		tries += 1


def resolve_ips(docker_client, low_level_client):
	LOCAL_IPS_FILE = "/local_ips.txt"
	REMOTE_IPS_FILE = "/remote_ips.txt"

	try:
		gods = {}
		number_of_gods = len(low_level_client.nodes())
		local_ips_list = []
		own_ip = socket.gethostbyname(socket.gethostname())
		
		print("[Py (god)] ip: " + str(own_ip))
		print("[Py (god)] number of gods: " + str(number_of_gods))
		stdout.flush()
	
		containers = docker_client.containers.list()
		for container in containers:
			test_net_config = low_level_client.inspect_container(container.id)['NetworkSettings']['Networks'].get('test_overlay')
			
			if (test_net_config is not None):
				container_ip = test_net_config["IPAddress"]
				if container_ip not in local_ips_list:
					local_ips_list.append(container_ip)
		
		local_ips_list.remove(own_ip)
					
		ip_broadcast = Process(target=broadcast_ips, args=(local_ips_list,))
		ip_broadcast.start()
		
		receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		receiver.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		receiver.bind(('', UDP_PORT))
		
		while len(gods) < number_of_gods:
			data, addr = receiver.recvfrom(BUFFER_LEN)
			
			if (addr not in gods):
				gods[int(ip2int(addr[0]))] = [ip2int(ip) for ip in data.decode("utf-8").split()]
				# ips_as_ints = map(ip2int, data.decode("utf-8").split())
				
				
		
		ip_broadcast.join()
		
		
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
			stdout.flush()
		
		with open(REMOTE_IPS_FILE, 'r') as file:
			new_dict = json.load(file)
			print("\n[Py (god)] remote:")
			pprint.pprint(new_dict)
			stdout.flush()
	
		return gods
	

	except Exception as e:
		print("[Py] " + str(e))
		stdout.flush()
		stderr.flush()
		sleep(5)
	


def main():
	UDP_PORT = 55555
	DOCKER_SOCK = "/var/run/docker.sock"
	TOPOLOGY = "/topology.xml"
	
	if len(argv) < 3:
		print("If you are calling " + argv[0] + " from your workstation stop.")
		print("This should only be used inside containers")
		return
	
	mode = argv[1]
	label = argv[2]
	
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
				
				print("[Py (bootstrapper)] ip: " + str(socket.gethostbyname(socket.gethostname())))
				
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
									  labels=["god"+label],
									  detach=True)
				# stderr=True,
				# stdout=True)
				pause()
				
				return
			
			except Exception as e:
				print(e)
				stdout.flush()
				stderr.flush()
				sleep(5)
				continue  # If we get any exceptions try again
	
	
	# We are the god container
	
	# First thing to do is copy over the topology
	while True:
		try:
			bootstrapper_id = argv[3]
			bootstrapper_pid = lowLevelClient.inspect_container(bootstrapper_id)["State"]["Pid"]
			cmd = ["/bin/sh", "-c", "nsenter -t " + str(bootstrapper_pid) + " -m cat " + TOPOLOGY + " | cat > " + TOPOLOGY]
			Popen(cmd).wait()
			break
		
		except Exception as e:
			print(e)
			stdout.flush()
			stderr.flush()
			sleep(5)
			continue
	
	# We are finally ready to proceed
	
	# start Aeron Media Driver
	aeron_media_driver = None
	try:
		aeron_media_driver = Popen('/usr/bin/Aeron/aeronmd')
		print("started aeron_media_driver.")
	
	except Exception as e:
		print(e)
	
	print("Bootstrapping all local containers with label " + label)
	stdout.flush()
	
	already_bootstrapped = {}
	instance_count = 0
	
	ips_dict = resolve_ips(client, lowLevelClient)
	
	while True:
		try:
			running = 0  # running container counter, we stop the god if there are 0 same experiment containers running
			
			# check if containers need bootstrapping
			containers = client.containers.list()
			for container in containers:
				if label in container.labels:
					running += 1
				
				if label in container.labels and container.id not in already_bootstrapped and container.status == "running":
					try:
						id = container.id
						inspect_result = lowLevelClient.inspect_container(id)
						pid = inspect_result["State"]["Pid"]
						print("Bootstrapping " + container.name + " ...")
						stdout.flush()
						
						cmd = ["nsenter", "-t", str(pid), "-n", "/usr/bin/python3", "/usr/bin/NEEDemucore", TOPOLOGY, str(id), str(pid)]
						emucore_instance = Popen(cmd)
						
						instance_count += 1
						print("Done bootstrapping " + container.name)
						stdout.flush()
						already_bootstrapped[container.id] = emucore_instance
					
					except:
						print("Bootstrapping failed... will try again.")
						stdout.flush()
						stderr.flush()
				
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
				
				print("God terminating.")
				
				if aeron_media_driver:
					aeron_media_driver.terminate()
					print("aeron_media_driver terminating.")
					aeron_media_driver.wait()
				
				stdout.flush()
				return
			
			sleep(5)
		
		except Exception as e:
			print(e)
			stdout.flush()
			stderr.flush()
			sleep(5)
			continue


if __name__ == '__main__':
	main()
	
	