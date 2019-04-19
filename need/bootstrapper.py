#! /usr/bin/python3

# from docker.types import Mount
import docker
from kubernetes import client, config

import os
import sys
import socket
import json, pprint

import netifaces as ni
from subprocess import Popen
from multiprocessing import Process
from time import sleep
from signal import pause
from contextlib import suppress
# from shutil import copy

from need.NEEDlib.utils import int2ip, ip2int, list_compare
from need.NEEDlib.utils import print_message, print_error, print_and_fail, print_named, print_error_named
from need.NEEDlib.utils import DOCKER_SOCK, TOPOLOGY, LOCAL_IPS_FILE, REMOTE_IPS_FILE, GOD_IPS_SHARE_PORT


BUFFER_LEN = 4096

gods = {}
ready_gods = {}


def broadcast_ips(sender_sock, local_ips_list):
    msg = ' '.join(local_ips_list)
    while True:
        sender_sock.sendto(bytes(msg, encoding='utf8'), ('<broadcast>', GOD_IPS_SHARE_PORT))
        sleep(2)

def broadcast_ready(sender_sock):
    msg = "READY "
    while True:
        sender_sock.sendto(bytes(msg, encoding='utf8'), ('<broadcast>', GOD_IPS_SHARE_PORT))
        sleep(2)


def resolve_ips(client, low_level_client):
    global gods
    global ready_gods
    
    sleep(5)
    
    try:
        local_ips_list = []

        orchestrator = os.getenv('NEED_ORCHESTRATOR', 'swarm')
        if orchestrator == 'kubernetes':
            #Since client.list_namespaced_pod() returns *all* pods on all nodes, we have to known
            #which node we're running on and only collect these pods' IPs.
            own_ip = None
            while own_ip is None:
                node_ips = []
                for node in client.list_node().items:
                    for address in node.status.addresses:
                        if address.type == "InternalIP":
                            node_ips.append(address.address)
                if len(node_ips) == 1:
                    own_ip = node_ips[0]
                    break

                own_ips = []# own_ip = socket.gethostbyname(socket.gethostname())
                try:
                    for iface in ni.interfaces():
                        own_ips.append(ni.ifaddresses(iface)[ni.AF_INET][0]['addr'])
                except Exception as e:
                    pass

                intersection = [IP for IP in own_ips if IP in node_ips]
                if not len(intersection) == 0:
                    own_ip = intersection[0]

            number_of_gods = len(client.list_node().to_dict()["items"])  # one god per machine
            print_named("god", "ip: " + str(own_ip) + ", nr. of gods: " + str(number_of_gods))

            # container may start without an IP, so just retry until all are set
            while len(local_ips_list) <= 0:
                need_pods = client.list_namespaced_pod('default')
                for pod in need_pods.items:
                    if pod.status.host_ip == own_ip:
                        local_ips_list.append(pod.status.pod_ip)

                if None in local_ips_list:
                    local_ips_list.clear()

            #own_ip = socket.gethostbyname(socket.gethostname())
            #number_of_gods = len(client.list_node().to_dict()["items"])  # one god per machine

            #print_named("god", "ip: (not yet known)" + ", nr. of gods: " + str(number_of_gods))

            ## container may start without an IP, so just retry until all are set
            #while not len(local_ips_list) > 0:
                #try:
                    #need_pods = client.list_namespaced_pod('default')
                    #local_conatiner_ids = [container["Id"] for container in low_level_client.containers()]

                    #for pod in need_pods.items:
                        #container_id = pod.status.container_statuses[0].container_id[9:]
                        #if container_id is not None and container_id in local_conatiner_ids:
                            ##local_pods.append(pod)
                            #local_ips_list.append(pod.status.pod_ip)

                    #if None in local_ips_list:
                        #local_pods.clear()
                        #local_ips_list.clear()
                #except:
                    #pass

        else:
            if orchestrator != 'swarm':
                print_named("bootstrapper", "Unrecognized orchestrator. Using default docker swarm.")

            number_of_gods = len(low_level_client.nodes())  # one god per machine
            print_named("god", "ip: (not yet known), nr. of gods: " + str(number_of_gods))

            # find IPs of all local containers connected to the test_overlay network
            containers = client.containers.list()
            for container in containers:
                test_net_config = low_level_client.inspect_container(container.id)['NetworkSettings']['Networks'].get('test_overlay')

                if test_net_config is not None:
                    container_ip = test_net_config["IPAddress"]
                    if container_ip not in local_ips_list:
                        local_ips_list.append(container_ip)

        # with suppress(ValueError):          # if god is not on the same network the remove will fail, so just ignore it
        #     local_ips_list.remove(own_ip)   # if god is on the same network remove it from the list of IPs

        # listen for msgs from other gods
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(('', GOD_IPS_SHARE_PORT))

        # setup broadcast
        sender_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sender_sock.bind(('', GOD_IPS_SHARE_PORT+1))
        sender_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sender_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sender_sock.setblocking(False)

        # broadcast local IPs
        ip_broadcast = Process(target=broadcast_ips, args=(sender_sock, local_ips_list, ))
        ip_broadcast.start()

        while len(gods) < number_of_gods:
            data, addr = recv_sock.recvfrom(BUFFER_LEN)
            list_of_ips = data.decode("utf-8").split()

            # print_named("god", f"{list_of_ips[0]} :: {list_of_ips[1:]}")
            print_named("god1", f"{addr[0]} :: {list_of_ips}")

            if list_of_ips[0] == "READY":
                ready_gods[ip2int(addr[0])] = "READY"

            else:
                if ip2int(addr[0]) not in gods:
                    list_of_ips = [ip2int(ip) for ip in list_of_ips]
                    gods[ip2int(addr[0])] = list_of_ips


        # broadcast ready msgs
        ready_broadcast = Process(target=broadcast_ready, args=(sender_sock,))
        ready_broadcast.start()

        while len(ready_gods) < number_of_gods:
            data, addr = recv_sock.recvfrom(BUFFER_LEN)
            list_of_ips = data.decode("utf-8").split()

            print_named("god2", f"{addr[0]} :: {list_of_ips}")

            if list_of_ips[0] == "READY":
                ready_gods[ip2int(addr[0])] = "READY"

        # terminate all broadcasts
        ip_broadcast.terminate()
        ready_broadcast.terminate()
        ip_broadcast.join()
        ready_broadcast.join()

        # find owr own IP by matching the local IPs
        list_of_ips = [ip2int(ip) for ip in local_ips_list]
        for key, value in gods.items():
            if list_compare(list_of_ips, value) == 0:
                own_ip = key
                break

        print_named("god", "ip: " + int2ip(own_ip) + ", nr. of gods: " + str(number_of_gods))
        
        # write all known IPs to a file to be read from c++ lib if necessary
        # this information is not currently being used because everyone publishes to the logs in the god containers
        # own_ip = ip2int(own_ip)
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
        print_and_fail(e)


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
        print_error_named("god", "failed to start aeron media driver.")
        print_and_fail(e)


    # We are finally ready to proceed
    print_named("god", "Bootstrapping all local containers with label " + label)

    already_bootstrapped = {}
    instance_count = 0

    resolve_ips(kubeAPIInstance, lowLevelClient)

    need_pods = kubeAPIInstance.list_namespaced_pod('default')
    local_containers = []
    for container in lowLevelClient.containers():
        local_containers.append(container["Id"])

    while True:
        try:
            running = 0  # running container counter, we stop the god if there are 0 same experiment containers running

            # check if containers need bootstrapping
            need_pods = kubeAPIInstance.list_namespaced_pod('default')
            for pod in need_pods.items:
                container_id = pod.status.container_statuses[0].container_id[9:]

                if label in pod.metadata.labels:
                    running += 1

                if container_id in local_containers and container_id not in already_bootstrapped and pod.status.container_statuses[0].state.running is not None:

                    try:
                        # inject the Dashboard into the dashboard container
                        if "dashboard" in pod.metadata.name:
                            try:
                                container_id = pod.status.container_statuses[0].container_id[9:]
                                container_pid = lowLevelClient.inspect_container(container_id)["State"]["Pid"]

                                cmd = ["nsenter", "-t", str(container_pid), "-n", "/usr/bin/python3", "/usr/bin/NEEDDashboard", TOPOLOGY]
                                dashboard_instance = Popen(cmd)

                                instance_count += 1
                                print_named("god", "Done bootstrapping dashboard.")
                                already_bootstrapped[container_id] = dashboard_instance

                            except:
                                print_error_named("god", "! failed to bootstrap dashboard.")

                        # inject the Logger into the logger container
                        elif "logger" in pod.metadata.name:
                            try:
                                container_id = pod.status.container_statuses[0].container_id[9:]

                                container_pid = lowLevelClient.inspect_container(container_id)["State"]["Pid"]

                                cmd = ["nsenter", "-t", str(container_pid), "-n", "/usr/bin/python3", "/usr/bin/NEEDLogger", TOPOLOGY]
                                logger_instance = Popen(cmd)

                                instance_count += 1
                                print_named("god", "Done bootstrapping logger.")
                                already_bootstrapped[container_id] = logger_instance

                            except:
                                print_error_named("god", "! failed to bootstrap dashboard.")

                        # if not a supervisor container, inject emucore into application containers
                        elif label in pod.metadata.labels:
                            try:
                                container_pid = lowLevelClient.inspect_container(container_id)["State"]["Pid"]

                                cmd = ["nsenter", "-t", str(container_pid), "-n", "/usr/bin/python3", "/usr/bin/NEEDemucore",
                                    TOPOLOGY, str(container_id), str(container_pid)]
                                emucore_instance = Popen(cmd)

                                instance_count += 1
                                already_bootstrapped[container_id] = emucore_instance

                            except Exception as e:
                                print_error_named("god", "Bootstrapping failed:\n" + str(e) + "\n... will try again.")
                                sys.stdout.flush()

                    except:
                        pass  # container is probably not fully set up

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
            sleep(10)
            continue



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
                                    network="host",
                                    shm_size=8000000000,
                                    remove=True,
                                    environment=env,
                                    volumes_from=[us.id],
                                    # network_mode="container:"+us.id,  # share the network stack with this container
                                    # network='test_overlay',
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
        print_error("[Py (god)] failed to start aeron media driver.")
        print_and_fail(e)


    # we are finally ready to proceed
    print_named("god", "Bootstrapping all local containers with label " + label)
    already_bootstrapped = {}
    instance_count = 0

    resolve_ips(client, lowLevelClient)

    while True:
        try:
            running = 0  # running container counter, we stop the god if there are 0 same experiment containers running

            # check if containers need bootstrapping
            containers = client.containers.list()
            for container in containers:

                if label in container.labels:
                    running += 1

                if container.id not in already_bootstrapped and container.status == "running":

                    try:
                        # inject the Dashboard into the dashboard container
                        if "dashboard" in container.labels['com.docker.swarm.service.name']:
                            try:
                                id = container.id
                                inspect_result = lowLevelClient.inspect_container(id)
                                pid = inspect_result["State"]["Pid"]

                                cmd = ["nsenter", "-t", str(pid), "-n", "/usr/bin/python3", "/usr/bin/NEEDDashboard",
                                    TOPOLOGY]
                                dashboard_instance = Popen(cmd)

                                instance_count += 1
                                print_named("god", "Dashboard bootstrapped.")
                                already_bootstrapped[container.id] = dashboard_instance

                            except:
                                print_error_named("god", "! failed to bootstrap dashboard.")

                        # inject the Logger into the logger container
                        elif "logger" in container.labels['com.docker.swarm.service.name']:
                            try:
                                id = container.id
                                inspect_result = lowLevelClient.inspect_container(id)
                                pid = inspect_result["State"]["Pid"]

                                cmd = ["nsenter", "-t", str(pid), "-n", "/usr/bin/python3", "/usr/bin/NEEDLogger",
                                    TOPOLOGY]
                                dashboard_instance = Popen(cmd)

                                instance_count += 1
                                print("[Py (god)] Logger bootstrapped.")
                                sys.stdout.flush()
                                already_bootstrapped[container.id] = dashboard_instance

                            except:
                                print_error_named("god", "! failed to bootstrap logger.")

                        # if not a supervisor container, inject emucore into application containers
                        elif label in container.labels:
                            try:
                                id = container.id
                                inspect_result = lowLevelClient.inspect_container(id)
                                pid = inspect_result["State"]["Pid"]

                                print_named("god", "Bootstrapping " + container.name + " ...")

                                cmd = ["nsenter", "-t", str(pid), "-n", "/usr/bin/python3", "/usr/bin/NEEDemucore",
                                    TOPOLOGY, str(id), str(pid)]
                                emucore_instance = Popen(cmd)

                                instance_count += 1
                                print_named("god", "Done bootstrapping " + container.name)
                                already_bootstrapped[container.id] = emucore_instance

                            except:
                                print_error_named("god", "! App container bootstrapping failed... will try again.")

                    except:
                        pass  # container is probably not fully set up

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
