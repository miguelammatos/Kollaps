from need.NEEDlib.NetGraph import NetGraph
from need.NEEDlib.XMLGraphParser import XMLGraphParser

import docker
from docker.types import Mount
from time import sleep
from sys import argv
from subprocess import call


def main():
    CHROOT_PATH = "/opt/NEED/chroot"
    DOCKER_SOCK = "/var/run/docker.sock"
    if len(argv) < 4:
        print("If you are calling " + argv[0] + " from your workstation stop.")
        print("This should only be used inside containers")
        return

    mode = argv[1]
    label = argv[2]
    command = argv[3]


    #Connect to the local docker daemon
    client = docker.DockerClient(base_url='unix:/' + DOCKER_SOCK)
    if mode == "-s":
        topology_file = "/topology.xml"

        graph = NetGraph()

        XMLGraphParser(topology_file, graph).fill_graph()

        instance_count = len(graph.hosts_by_ip)
        #create the chroot
        call(["mkdir", "-p" , CHROOT_PATH])
        call(["rm", "-rf", CHROOT_PATH+"/*"])
        call(["rsync", "-aAHX", "--exclude-from=/exclude.txt", "/", CHROOT_PATH])
        m = Mount(target=DOCKER_SOCK, source=DOCKER_SOCK, type='bind')
        client.containers.run(image=graph.bootstrapper, entrypoint="/usr/bin/python3",
                   command=["/usr/bin/NEEDbootstrapper", "-g", label, command, str(instance_count)],
                   privileged=True, pid_mode="host", remove=False,
                   mounts=[m])

        while True:
            sleep(500)


    instance_count = int(argv[4])
    LowLevelClient = docker.APIClient(base_url='unix:/' + DOCKER_SOCK)
    print("Bootstrapping all local containers with label " + label + " with the command " + command)

    already_bootstrapped = {}

    while len(already_bootstrapped) < instance_count:
        containers = client.containers.list()
        for container in containers:
            if label in container.labels and container.id not in already_bootstrapped and container.status == "running":
                try:
                    id = container.id
                    inspect_result = LowLevelClient.inspect_container(id)
                    pid = inspect_result["State"]["Pid"]
                    print("Bootstrapping " + container.name + " ...")
                    #nsenter is broken on busybox....
                    #none of this works
                    call(["nsenter", "-t", str(pid), "-m", "mount -o bind /var " + CHROOT_PATH+"/var"])
                    call(["nsenter", "-t", str(pid), "-m", "mount -o bind /run " + CHROOT_PATH+"/run"])
                    call(["nsenter", "-t", str(pid), "-m", "mount -o bind /tmp " + CHROOT_PATH+"/tmp"])
                    call(["nsenter", "-t", str(pid), "-m", "mount -o bind /sys " + CHROOT_PATH+"/sys"])
                    call(["nsenter", "-t", str(pid), "-m", "mount -o bind /dev " + CHROOT_PATH+"/dev"])
                    call(["nsenter", "-t", str(pid), "-m", "mount -t proc none " + CHROOT_PATH+"/proc"])
                    container.exec_run(command, privileged=True, detach=True)
                    print("Done bootstrapping " + container.name)
                    already_bootstrapped[container.id] = True
                except:
                    print("Bootstrapping failed... will try again.")
        sleep(5)

if __name__ == '__main__':
    main()
