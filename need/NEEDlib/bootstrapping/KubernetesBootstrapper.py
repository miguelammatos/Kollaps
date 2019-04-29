#! /usr/bin/python3

import docker
from kubernetes import client, config

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


class KubernetesBootstrapper(Bootstrapper):
    
    def __init__(self):
        # Connect to the local docker daemon
        config.load_incluster_config()
        high_level_client = client.CoreV1Api()
        low_level_client = docker.APIClient(base_url='unix:/' + DOCKER_SOCK)
        
        Bootstrapper.__init__(self, high_level_client, low_level_client)
    
    
    def bootstrap_dashboard(self, pod, container_id):
        try:
            container_id = pod.status.container_statuses[0].container_id[9:]
            container_pid = self.low_level_client.inspect_container(container_id)["State"]["Pid"]
        
            cmd = ["nsenter", "-t", str(container_pid), "-n", "/usr/bin/python3", "/usr/bin/NEEDDashboard", TOPOLOGY]
            dashboard_instance = Popen(cmd)
        
            self.instance_count += 1
            print_named("god", "Done bootstrapping dashboard.")
            self.already_bootstrapped[container_id] = dashboard_instance
    
        except:
            print_error_named("god", "! failed to bootstrap dashboard.")
            sys.stdout.flush()
            
            
    def bootstrap_logger(self, pod, container_id):
        try:
            container_id = pod.status.container_statuses[0].container_id[9:]
            container_pid = self.low_level_client.inspect_container(container_id)["State"]["Pid"]
        
            cmd = ["nsenter", "-t", str(container_pid), "-n", "/usr/bin/python3", "/usr/bin/NEEDLogger", TOPOLOGY]
            logger_instance = Popen(cmd)
        
            self.instance_count += 1
            print_named("god", "Done bootstrapping logger.")
            self.already_bootstrapped[container_id] = logger_instance
    
        except:
            print_error_named("god", "! failed to bootstrap dashboard.")
            sys.stdout.flush()
    
    
    def bootstrap_app_container(self, pod, container_id):
        try:
            container_pid = self.low_level_client.inspect_container(container_id)["State"]["Pid"]
        
            cmd = ["nsenter", "-t", str(container_pid), "-n", "/usr/bin/python3", "/usr/bin/NEEDemucore",
                   TOPOLOGY, str(container_id), str(container_pid)]
            emucore_instance = Popen(cmd)
        
            self.instance_count += 1
            self.already_bootstrapped[container_id] = emucore_instance
    
        except Exception as e:
            print_error_named("god", "Bootstrapping failed:\n" + str(e) + "\n... will try again.")
            sys.stdout.flush()
    
    
    def bootstrap(self, mode, label, bootstrapper_id):
        print_named("Bootstrapper", "Kubernetes bootstrapping started...")
        
        god_id = None  # get this, it will be argv[3]
        while not god_id:
            need_pods = self.high_level_client.list_namespaced_pod('default')
            try:
                for pod in need_pods.items:
                    if "boot" + label in pod.metadata.labels:
                        god_id = pod.status.container_statuses[0].container_id[9:]
    
            except Exception as e:
                print_error_named("god", e)
                sys.stdout.flush()
                sleep(1)  # wait for the Kubernetes API

        print_named("god", "found god_id.")
        
        self.start_aeron_media_driver()
        
        # find IPs of all God containers in the cluster
        self.resolve_ips(int(os.getenv('NUMBER_OF_GODS', 0)))
        print_named("god", "resolved all IPs")
        
        need_pods = self.high_level_client.list_namespaced_pod('default')
        local_containers = []
            
        while True:
            try:
                # running container counter, we stop the god if there are 0 same experiment containers running
                running = 0
        
                # check if containers need bootstrapping
                need_pods = self.high_level_client.list_namespaced_pod('default')
                local_containers.clear()
                for container in self.low_level_client.containers():
                    local_containers.append(container["Id"])
        
                for pod in need_pods.items:
                    container_id = pod.status.container_statuses[0].container_id[9:]
            
                    if label in pod.metadata.labels:
                        running += 1
            
                    if container_id in local_containers and container_id not in self.already_bootstrapped \
                            and pod.status.container_statuses[0].state.running is not None:
                
                        try:
                            # inject the Dashboard into the dashboard container
                            if "dashboard" in pod.metadata.name:
                                self.bootstrap_dashboard(pod, container_id)
                            
                            # inject the Logger into the logger container
                            elif "logger" in pod.metadata.name:
                                self.bootstrap_logger(pod, container_id)
                            
                            # if not a supervisor container, inject emucore into application containers
                            elif label in pod.metadata.labels:
                                self.bootstrap_app_container(pod, container_id)
                        
                        except:
                            pass  # container is probably not fully set up

                    # Check for bootstrapper termination
                    if container_id == god_id and pod.status.container_statuses[0].state.running is not None:
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
