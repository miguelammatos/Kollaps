#! /usr/bin/python3

from docker import APIClient
from kubernetes import client, config
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
    god_id = None #get this, it will be argv[3]

    #Connect to the local docker daemon
    config.load_incluster_config()
    kubeAPIInstance = client.CoreV1Api()
    LowLevelClient = APIClient(base_url='unix:/' + DOCKER_SOCK)
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
            sleep(1) #wait for the Kubernetes API

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

if __name__ == '__main__':
    main()
