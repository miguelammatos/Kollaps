from __future__ import print_function
import subprocess
import sys


BYTE_LIMIT = 255
SHORT_LIMIT = 65535
# INT_LIMIT = 4294967296


class ENVIRONMENT:
    NETWORK_INTERFACE = 'NETWORK_INTERFACE'
    BROADCAST = 'BROADCAST_ADDRESS'
    POOL_PERIOD = 'NEED_POOL_PERIOD'
    ITERATION_COUNT = 'NEED_ITERATION_COUNT'


def fail(message):
    print("An error occured, terminating!", file=sys.stderr)
    print("Error Message: " + message, file=sys.stderr)
    exit(-1)

def error(message):
    print("ERROR: " + message, file=sys.stderr)

def start_experiment():
    # Temporary hack to start the experiment
    subprocess.run('echo "done" > /tmp/readypipe', shell=True)

def stop_experiment():
    # Temporary hack to stop the experiment
    subprocess.run('echo "done" > /tmp/donepipe', shell=True)

