from need.NEEDlib.NetGraph import NetGraph
from need.NEEDlib.XMLGraphParser import XMLGraphParser

import docker
from docker.types import Mount
from time import sleep
from sys import argv
from subprocess import Popen
from shutil import copy


def main():
    DOCKER_SOCK = "/var/run/docker.sock"
    TOPOLOGY_SRC = "/topology.xml"
    TOPOLOGY = "/opt/NEED/topology.xml"

    if len(argv) < 3:
        print("If you are calling " + argv[0] + " from your workstation stop.")
        print("This should only be used inside containers")
        return

    mode = argv[1]
    label = argv[2]


    #Connect to the local docker daemon
    client = docker.DockerClient(base_url='unix:/' + DOCKER_SOCK)
    LowLevelClient = docker.APIClient(base_url='unix:/' + DOCKER_SOCK)

    #If we are bootstrapper:
    if mode == "-s":
        copy(TOPOLOGY_SRC, TOPOLOGY)
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
        client.containers.run(image=boot_image,
                              entrypoint="/usr/bin/python3",
                              command=["/usr/bin/NEEDbootstrapper", "-g", label, str(us.id)],
                              privileged=True,
                              pid_mode="host",
                              remove=True,
                              environment=env,
                              volumes_from=[us.id],
                              labels=["god"],
                              detach=False,
                              stderr=True,
                              stdout=True)
        return



    # Next is GOD container code

    bootstrapper_id = argv[3]
    #figure out who we are
    us = None
    for container in client.containers.list():
        if "god" in container.labels:
            us = container
            break


    print("Bootstrapping all local containers with label " + label)

    already_bootstrapped = {}
    emucore_instances = []
    instance_count = 0
    bootstrapper = None

    while True:
        #check if containers need bootstrapping
        bootstrapper = None
        containers = client.containers.list()
        for container in containers:
            if label in container.labels and container.id not in already_bootstrapped and container.status == "running":
                try:
                    id = container.id
                    inspect_result = LowLevelClient.inspect_container(id)
                    pid = inspect_result["State"]["Pid"]
                    print("Bootstrapping " + container.name + " ...")
                    emucore_instances.append(Popen(
                        ["nsenter", "-t", str(pid), "-n", "/usr/bin/python3", "/usr/bin/NEEDemucore", TOPOLOGY, str(id)])
                    )
                    instance_count += 1
                    print("Done bootstrapping " + container.name)
                    already_bootstrapped[container.id] = True
                except:
                    print("Bootstrapping failed... will try again.")
            #Check for termination
            if container.id == bootstrapper_id and container.status == "running":
                bootstrapper = container
        if bootstrapper is None:
            us.stop()
        sleep(5)


if __name__ == '__main__':
    main()
