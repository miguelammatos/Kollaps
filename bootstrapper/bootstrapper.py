import docker
from time import sleep
from sys import argv
from subprocess import call

label = argv[1]
command = argv[2]

#create the chroot
call(["mkdir", "-p" , "/opt/NEED/chroot"])
call(["rm", "-rf", "/opt/NEED/*"])
call(["rsync", "-aAHX", "--exclude-from=/exclude.txt", "/", "/opt/NEED/chroot/"])
call(["chmod", "555", "/need_chroot.sh"])
call(["rsync", "-aAX", "/need_chroot.sh", "/opt/NEED/"])
#copyfile("/opt/NEED_build/NEED.pex", "/opt/NEED/NEED.pex")


#Connect to the local docker daemon
client = docker.DockerClient(base_url='unix://var/run/docker.sock')

print("Bootstrapping all local containers with label " + label + " with the command " + command)

already_bootstrapped = {}

while True:
    containers = client.containers.list()
    for container in containers:
        if label in container.labels and container.id not in already_bootstrapped and container.status == "running":
            try:
                print("Bootstrapping " + container.name + " ...")
                container.exec_run(command, privileged=True, detach=True)
                print("Done bootstrapping " + container.name)
                already_bootstrapped[container.id] = True
            except:
                print("Bootstrapping failed... will try again.")
    sleep(5)
