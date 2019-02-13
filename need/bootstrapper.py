#! /usr/bin/python3

import docker
from kubernetes import client, config
from time import sleep
from signal import pause
from sys import argv, stdout, stderr
import os
from subprocess import Popen
# from shutil import copy


def kubernetes_bootstrapper():
	DOCKER_SOCK = "/var/run/docker.sock"
	TOPOLOGY = "/topology.xml"

	mode = argv[1]
	label = argv[2]
	god_id = None  # get this, it will be argv[3]

	# Connect to the local docker daemon
	config.load_incluster_config()
	kubeAPIInstance = client.CoreV1Api()
	LowLevelClient = docker.APIClient(base_url='unix:/' + DOCKER_SOCK)
	need_pods = kubeAPIInstance.list_namespaced_pod('default')

	while not god_id:
		need_pods = kubeAPIInstance.list_namespaced_pod('default')
		try:
			for pod in need_pods.items:
				if "boot"+label in pod.metadata.labels:
					god_id = pod.status.container_statuses[0].container_id[9:]
					
		except Exception as e:
			print (e)
			stdout.flush()
			sleep(1)  # wait for the Kubernetes API

	# We are finally ready to proceed
	print("Bootstrapping all local containers with label " + label)
	stdout.flush()

	already_bootstrapped = {}
	instance_count = 0

	while True:
		try:
			need_pods = kubeAPIInstance.list_namespaced_pod('default')
			running = 0  # running container counter, we stop the god if there are 0 same experiment containers running

			# check if containers need bootstrapping
			for pod in need_pods.items:
				container_id = pod.status.container_statuses[0].container_id[9:]
				if label in pod.metadata.labels:
					running += 1
				if label in pod.metadata.labels and container_id not in already_bootstrapped and pod.status.container_statuses[0].state.running != None:
					try:
						container_pid = LowLevelClient.inspect_container(container_id)["State"]["Pid"]
						emucore_instance = Popen(
							["nsenter", "-t", str(container_pid), "-n",
							"/usr/bin/python3", "/usr/bin/NEEDemucore", TOPOLOGY, str(container_id), str(container_pid)]
						)
						instance_count += 1
						already_bootstrapped[container_id] = emucore_instance
						
					except:
						print("Bootstrapping failed... will try again.")
						stdout.flush()
						stderr.flush()

				# Check for bootstrapper termination
				if container_id == god_id and pod.status.container_statuses[0].state.running != None:
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
				print("God terminating")
				return
			
			sleep(5)
			
		except Exception as e:
			print (e)
			stdout.flush()
			sleep(1)
			
			
def docker_bootstrapper():
	DOCKER_SOCK = "/var/run/docker.sock"
	TOPOLOGY = "/topology.xml"

	mode = argv[1]
	label = argv[2]

	# Connect to the local docker daemon
	client = docker.DockerClient(base_url='unix:/' + DOCKER_SOCK)
	LowLevelClient = docker.APIClient(base_url='unix:/' + DOCKER_SOCK)

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

				inspect_result = LowLevelClient.inspect_container(us.id)
				env = inspect_result["Config"]["Env"]

				# create a "God" container that is in the host's Pid namespace
				client.containers.run(image=boot_image,
									command=["-g", label, str(us.id)],
									privileged=True,
									pid_mode="host",
									remove=True,
									environment=env,
									# volumes={DOCKER_SOCK: {'bind': DOCKER_SOCK, 'mode': 'rw'}},
									volumes_from=[us.id],
									# network_mode="container:"+us.id,  # share the network stack with this container
									labels=["god"+label],
									detach=True)
									#stderr=True,
									#stdout=True)
				pause()
				return
			
			except Exception as e:
				print(e)
				sleep(5)
				continue  # If we get any exceptions try again

	# We are the god container
	# First thing to do is copy over the topology
	while True:
		try:
			bootstrapper_id = argv[3]
			bootstrapper_pid = LowLevelClient.inspect_container(bootstrapper_id)["State"]["Pid"]
			Popen(["/bin/sh", "-c",
				"nsenter -t " + str(bootstrapper_pid) + " -m cat " + TOPOLOGY + " | cat > " + TOPOLOGY]
				).wait()
			break
			
		except Exception as e:
			print(e)
			stdout.flush()
			stderr.flush()
			sleep(5)
			continue

	# We are finally ready to proceed
	print("Bootstrapping all local containers with label " + label)
	stdout.flush()

	already_bootstrapped = {}
	instance_count = 0

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
						inspect_result = LowLevelClient.inspect_container(id)
						pid = inspect_result["State"]["Pid"]
						print("Bootstrapping " + container.name + " ...")
						stdout.flush()

						emucore_instance = Popen(
							["nsenter", "-t", str(pid), "-n",
							"/usr/bin/python3", "/usr/bin/NEEDemucore", TOPOLOGY, str(id), str(pid)]
						)
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
				print("God terminating")
				return
			sleep(5)
			
		except Exception as e:
			print(e)
			stdout.flush()
			stderr.flush()
			sleep(5)
			continue


if __name__ == '__main__':
	
	if len(argv) < 3:
		print("If you are calling " + argv[0] + " from your workstation stop.")
		print("This should only be used inside containers")
		exit(-1)
	
	orchestrator = os.getenv('NEED_ORCHESTRATOR', 'swarm')
	print("orchestrator: " + orchestrator)
	
	if orchestrator == 'kubernetes':
		kubernetes_bootstrapper()
		
	else:
		if orchestrator != 'swarm':
			print("Unrecognized orchestrator. Using default docker swarm.")
		
		docker_bootstrapper()






