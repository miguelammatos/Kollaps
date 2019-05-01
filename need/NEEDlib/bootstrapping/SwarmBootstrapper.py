#! /usr/bin/python3

# from docker.types import Mount
import docker

import os
import sys
import socket
import random

from subprocess import Popen
from time import sleep
from signal import pause

from need.NEEDlib.bootstrapping.Bootstrapper import Bootstrapper
from need.NEEDlib.utils import print_message, print_error, print_and_fail, print_named, print_error_named
from need.NEEDlib.utils import DOCKER_SOCK, TOPOLOGY


class SwarmBootstrapper(Bootstrapper):

    def __init__(self):
        # Connect to the local docker daemon
        high_level_client = docker.DockerClient(base_url='unix:/' + DOCKER_SOCK)
        low_level_client = docker.APIClient(base_url='unix:/' + DOCKER_SOCK)
        
        Bootstrapper.__init__(self, high_level_client, low_level_client)
        

    def start_god_container(self, label):
        while True:
            try:
                # If we are bootstrapper:
                us = None
                while not us:
                    containers = self.high_level_client.containers.list()
                    for container in containers:
                        if "boot" + label in container.labels:
                            us = container
                
                    sleep(1)
            
                boot_image = us.image
            
                inspect_result = self.low_level_client.inspect_container(us.id)
                env = inspect_result["Config"]["Env"]
            
                print_message("[Py (bootstrapper)] ip: " + str(socket.gethostbyname(socket.gethostname())))
                
                # create a "God" container that is in the host's Pid namespace
                self.high_level_client.containers.run(image=boot_image,
                                                      command=["-g", label, str(us.id)],
                                                      privileged=True,
                                                      pid_mode="host",
                                                      network="host",
                                                      shm_size=int(os.getenv('SHM_SIZE', '8000000000')),
                                                      remove=True,
                                                      name="god_" + str(random.getrandbits(64)),  # grep friendly
                                                      environment=env,
                                                      volumes_from=[us.id],
                                                      # network_mode="container:"+us.id,  # share the network stack with this container
                                                      # network='test_overlay',
                                                      labels=["god" + label],
                                                      detach=True)
                                                    # stderr=True,
                                                    # stdout=True)
            
                print_named("bootstrapper", "Started God container. Waiting for experiment to finish...")
            
                pause()
                return
        
            except Exception as e:
                print_error(e)
                sleep(5)
                continue  # If we get any exceptions try again
                
    
    def copy_topology(self, bootstrapper_id):
        while True:
            try:
                bootstrapper_pid = self.low_level_client.inspect_container(bootstrapper_id)["State"]["Pid"]
                cmd = ["/bin/sh",
                       "-c",
                       "nsenter -t " + str(bootstrapper_pid) + " -m cat " + TOPOLOGY + " | cat > " + TOPOLOGY]
                Popen(cmd).wait()
                break
        
            except Exception as e:
                print_error(e)
                sleep(5)
                continue
                
                
    def bootstrap_dashboard(self, container):
        try:
            container_id = container.id
            inspect_result = self.low_level_client.inspect_container(container_id)
            pid = inspect_result["State"]["Pid"]
        
            cmd = ["nsenter", "-t", str(pid),
                   "-n", "/usr/bin/python3", "/usr/bin/NEEDDashboard",
                   TOPOLOGY]
            dashboard_instance = Popen(cmd)
        
            self.instance_count += 1
            print_named("god", "Dashboard bootstrapped.")
            self.already_bootstrapped[container_id] = dashboard_instance
    
        except:
            print_error_named("god", "! failed to bootstrap dashboard.")


    def bootstrap_logger(self, container):
        try:
            container_id = container.id
            inspect_result = self.low_level_client.inspect_container(container_id)
            pid = inspect_result["State"]["Pid"]
        
            cmd = ["nsenter", "-t", str(pid),
                   "-n", "/usr/bin/python3", "/usr/bin/NEEDLogger",
                   TOPOLOGY]
            dashboard_instance = Popen(cmd)
        
            self.instance_count += 1
            print("[Py (god)] Logger bootstrapped.")
            sys.stdout.flush()
            self.already_bootstrapped[container_id] = dashboard_instance
    
        except:
            print_error_named("god", "! failed to bootstrap logger.")


    def bootstrap_app_container(self, container):
        try:
            container_id = container.id
            inspect_result = self.low_level_client.inspect_container(container_id)
            pid = inspect_result["State"]["Pid"]
        
            print_named("god", "Bootstrapping " + container.name + " ...")
        
            cmd = ["nsenter",
                   "-t", str(pid),
                   "-n", "/usr/bin/python3", "/usr/bin/NEEDemucore",
                   TOPOLOGY, str(container_id), str(pid)]
            emucore_instance = Popen(cmd)
        
            self.instance_count += 1
            print_named("god", "Done bootstrapping " + container.name)
            self.already_bootstrapped[container_id] = emucore_instance
    
        except:
            print_error_named("god", "! App container bootstrapping failed... will try again.")


    def bootstrap(self, mode, label, bootstrapper_id):
        
        if mode == "-s":
            # we are the bootstrapper
            print_named("Bootstrapper", "Swarm bootstrapping started...")
            self.start_god_container(label)
            
        else:
            # we are the God container
            print_named("God", "bootstrapping all containers with label " + label + ".")
            
            # first thing to do is copy over the topology
            # FIXME PG check why this was erasing the topology.xml file
            # self.copy_topology(self.low_level_client, bootstrapper_id)
            
            # next we start the Aeron Media Driver
            self.start_aeron_media_driver()
            
            # find IPs of all God containers in the cluster
            self.resolve_ips(int(os.getenv('NUMBER_OF_GODS', 0)))
            
            while True:
                try:
                    # running container counter, we stop the god if there are 0 same experiment containers running
                    running = 0
                    
                    # check if containers need bootstrapping
                    containers = self.high_level_client.containers.list()
                    for container in containers:
        
                        if label in container.labels:
                            running += 1
        
                        if container.id not in self.already_bootstrapped and container.status == "running":
        
                            try:
                                # inject the Dashboard into the dashboard container
                                if "dashboard" in container.labels['com.docker.swarm.service.name']:
                                    self.bootstrap_dashboard(container)
        
                                # inject the Logger into the logger container
                                elif "logger" in container.labels['com.docker.swarm.service.name']:
                                    self.bootstrap_logger(container)
        
                                # if not a supervisor container, inject emucore into application containers
                                elif label in container.labels:
                                    self.bootstrap_app_container(container)
                                   
                            except:
                                pass  # container is probably not fully set up
        
                        # Check for bootstrapper termination
                        if container.id == bootstrapper_id and container.status == "running":
                            running += 1
        
                    # Do some reaping
                    for key in self.already_bootstrapped:
                        self.already_bootstrapped[key].poll()
        
                    # Clean up and stop
                    if running == 0:
                        for key in self.already_bootstrapped:
                            if self.already_bootstrapped[key].poll() is not None:
                                self.already_bootstrapped[key].kill()
                                self.already_bootstrapped[key].wait()

                        self.terminate_aeron_media_driver()

                        sys.stdout.flush()
                        print_named("god", "God terminated.")
                        return
        
                    sleep(5)
        
                except Exception as e:
                    sys.stdout.flush()
                    print_error(e)
                    sleep(5)
                    continue
                