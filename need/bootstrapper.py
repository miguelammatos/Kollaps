#! /usr/bin/python3

import os
import sys

from time import sleep

from need.NEEDlib.utils import print_named, print_error, print_and_fail
from need.NEEDlib.bootstrapping.SwarmBootstrapper import SwarmBootstrapper
from need.NEEDlib.bootstrapping.KubernetesBootstrapper import KubernetesBootstrapper


def main():
    try:
        if len(sys.argv) < 3:
            msg = "If you are calling " + sys.argv[0] + " from your workstation stop."
            msg += "This should only be used inside containers."
    
            sleep(20)
    
            print_and_fail(msg)
        
        mode = sys.argv[1]
        label = sys.argv[2]
        bootstrapper_id = sys.argv[3] if len(sys.argv) > 3 else None
    
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
    
    except Exception as e:
        sys.stdout.flush()
        print_error(e)
        sleep(20)
        
        
if __name__ == '__main__':
    main()
    