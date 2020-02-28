#! /usr/bin/python3
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import sys

from time import sleep

from kollaps.Kollapslib.utils import print_named, print_error, print_and_fail
from kollaps.Kollapslib.bootstrapping.SwarmBootstrapper import SwarmBootstrapper
from kollaps.Kollapslib.bootstrapping.KubernetesBootstrapper import KubernetesBootstrapper


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
        orchestrator = os.getenv('KOLLAPS_ORCHESTRATOR', 'swarm')
        
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
    
