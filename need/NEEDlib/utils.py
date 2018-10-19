import subprocess
import sys
import struct
import socket
import docker
from subprocess import Popen


BYTE_LIMIT = 255
SHORT_LIMIT = 65535
# INT_LIMIT = 4294967296
DOCKER_SOCK = "/var/run/docker.sock"


class ENVIRONMENT:
    NETWORK_INTERFACE = 'NETWORK_INTERFACE'
    BROADCAST = 'BROADCAST_ADDRESS'
    POOL_PERIOD = 'NEED_POOL_PERIOD'
    ITERATION_COUNT = 'NEED_ITERATION_COUNT'

class CONTAINER:
    id = None
    pid = ""
    client = None  # type: docker.DockerClient
    ll = None  # type: docker.APIClient
    container = None
    process = None

def fail(message):
    print("An error occured, terminating!", file=sys.stderr)
    print("Error Message: " + message, file=sys.stderr)
    exit(-1)

def error(message):
    print("ERROR: " + message, file=sys.stderr)

def start_experiment():
    # Temporary hack to start the experiment
    #subprocess.run('echo "done" > /tmp/readypipe', shell=True)
    inspect = CONTAINER.ll.inspect_container(CONTAINER.id)
    cmd = inspect['Config']['Cmd']
    image = inspect['Image']
    image_inspect = CONTAINER.ll.inspect_image(image)
    entrypoint = image_inspect['Config']['Entrypoint']
    if cmd is None:
        cmd = image_inspect['Config']['Cmd']
    elif len(cmd) == 0:
        cmd = image_inspect['Config']['Cmd']
    if cmd is None:
        command = ' '.join(entrypoint)
    else:
        command = ' '.join(entrypoint + cmd)
    arg = ['/bin/sh'] + ['-c'] + [command]
    CONTAINER.container.exec_run(arg, detach=True)



def stop_experiment():
    # Temporary hack to stop the experiment
    #subprocess.run('echo "done" > /tmp/donepipe', shell=True)
    #CONTAINER.container.exec_run(["/bin/sh", "-c", "kill -15 -1"], detach=True)
    #CONTAINER.container.kill(signal=15)
    #Popen(
    #    ["nsenter", "-t", CONTAINER.pid, "-p", "/usr/bin/kill -15 -1"]
    #)
    #TODO Still trying to figure out a good way of doing this....
    #TODO see https://www.fpcomplete.com/blog/2016/10/docker-demons-pid1-orphans-zombies-signals
    return

def setup_container(id, pid):
    CONTAINER.id = id
    CONTAINER.pid = pid
    CONTAINER.client = docker.DockerClient(base_url='unix:/' + DOCKER_SOCK)
    CONTAINER.ll = docker.APIClient(base_url='unix:/' + DOCKER_SOCK)
    CONTAINER.container = CONTAINER.client.containers.get(id)

def ip2int(addr):
    return struct.unpack("!I", socket.inet_aton(addr))[0]

def int2ip(addr):
    return socket.inet_ntoa(struct.pack("!I", addr))

