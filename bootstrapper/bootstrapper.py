import docker
from time import sleep
from sys import argv
from shutil import copyfile

label = argv[1]
command = argv[2]

#Make sure the volume version is up-to-date
copyfile("/opt/NEED_build/NEED.pex", "/opt/NEED/NEED.pex")

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
