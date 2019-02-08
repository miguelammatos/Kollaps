#! /usr/bin/python3

import docker
# from docker.types import Mount
from time import sleep
from signal import pause
from sys import argv, stdout, stderr
from subprocess import Popen
# from shutil import copy


def main():
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
									  shm_size=4000000000,
									  remove=True,
									  environment=env,
									  # volumes={DOCKER_SOCK: {'bind': DOCKER_SOCK, 'mode': 'rw'}},
									  volumes_from=[us.id],
									  # network_mode="container:"+us.id,  # share the network stack with this container
									  labels=["god"+label],
									  detach=True)
				# stderr=True,
				# stdout=True)
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
				
				if (aeron_media_driver):
					aeron_media_driver.terminate()
					print("aeron_media_driver terminating.")
					aeron_media_driver.wait()
				
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
	
	