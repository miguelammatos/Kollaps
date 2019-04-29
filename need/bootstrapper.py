#! /usr/bin/python3

import os
import sys

from need.NEEDlib.utils import print_named, print_error_named, print_and_fail
from need.NEEDlib.bootstrapping.SwarmBootstrapper import SwarmBootstrapper
from need.NEEDlib.bootstrapping.KubernetesBootstrapper import KubernetesBootstrapper


if __name__ == '__main__':
    
    if len(sys.argv) < 3:
        msg = "If you are calling " + sys.argv[0] + " from your workstation stop."
        msg += "This should only be used inside containers."
        print_and_fail(msg)
    
    mode = sys.argv[1]
    label = sys.argv[2]
    bootstrapper_id = sys.argv[3]

    bootstrapper = None
    orchestrator = os.getenv('NEED_ORCHESTRATOR', 'swarm')
    
    if orchestrator == 'kubernetes':
        bootstrapper = KubernetesBootstrapper()
        
    elif orchestrator == 'swarm':
        bootstrapper = SwarmBootstrapper()
        
    # insert here any other bootstrappping class required by new orchestrators
    else:
        print_named("bootstrapper", "Unrecognized orchestrator. Using default: Docker Swarm.")
        bootstrapper = SwarmBootstrapper()
        
    bootstrapper.bootstrap(mode, label, bootstrapper_id)
    