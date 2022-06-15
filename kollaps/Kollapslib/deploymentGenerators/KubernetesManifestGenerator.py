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

from kubernetes import client, config
from uuid import uuid4

from kollaps.Kollapslib.NetGraph import NetGraph
from kollaps.Kollapslib.utils import print_and_fail, print_error_named, print_message, print_named


class KubernetesManifestGenerator:
    def __init__(self, topology_file, graph):
        self.graph = graph  # type: NetGraph
        self.topology_file = topology_file
        self.experiment_UUID = str(uuid4())

    def print_roles(self):
        print("apiVersion: v1")
        print("kind: ServiceAccount")
        print("metadata:")
        print("  labels:")
        print("    app: Kollaps")
        print("  name: kollaps-listpods")
        print("---")
        print("apiVersion: rbac.authorization.k8s.io/v1")
        print("kind: ClusterRole")
        print("metadata:")
        print("  name: listpods")
        print("rules:")
        print("- apiGroups: [\"\"]")
        print("  resources: [\"pods\", \"nodes\"]")
        print("  verbs: [\"list\"]")
        print("---")
        print("kind: ClusterRoleBinding")
        print("apiVersion: rbac.authorization.k8s.io/v1")
        print("metadata:")
        print("  name: listpods")
        print("subjects:")
        print("- kind: ServiceAccount")
        print("  name: kollaps-listpods")
        print("  namespace: default")
        print("roleRef:")
        print("  kind: ClusterRole")
        print("  name: listpods")
        print("  apiGroup: rbac.authorization.k8s.io")
        
    def print_bootstrapper(self, number_of_gods, pool_period, max_flow_age, threading_mode, shm_size, aeron_lib_path, aeron_term_buffer_length, aeron_ipc_term_buffer_length, bw_emulation):
        print("apiVersion: apps/v1")
        print("kind: DaemonSet")
        print("metadata:")
        print("  name: bootstrapper")
        print("  labels:")
        print("    boot"+self.experiment_UUID + ": \"true\"")
        print("spec:")
        print("  selector:")
        print("    matchLabels:")
        print("      app: bootstrapper")
        print("  template:")
        print("    metadata:")
        print("      labels:")
        print("        app: bootstrapper")
        print("        boot"+self.experiment_UUID + ": \"true\"")
        print("    spec:")
        print("      containers:")
        print("      - name: bootstrapper")
        print("        image: " + self.graph.bootstrapper)
        print("        env:")
        print("        - name: KOLLAPS_UUID")
        print("          value: "+self.experiment_UUID)
        print("        - name: KOLLAPS_ORCHESTRATOR")
        print("          value: 'kubernetes'")
        if bw_emulation is False:
            print("        - name: RUNTIME_EMULATION")
            print("          value: 'false'")
        print("        - name: NUMBER_OF_GODS")
        print("          value: '" + str(number_of_gods) + "'")
        print("        - name: POOL_PERIOD")
        print("          value: '" + str(pool_period) + "'")
        print("        - name: MAX_FLOW_AGE")
        print("          value: '" + str(max_flow_age) + "'")
        print("        args:")
        print("        - -g")
        print("        - "+self.experiment_UUID)
        print("        securityContext:")
        print("          capabilities:")
        print("            add: [\"NET_ADMIN\", \"SYS_ADMIN\"]")
        print("          privileged: true")
        print("        volumeMounts:")
        print("        - name: docker-socket")
        print("          mountPath: /var/run/docker.sock")
        print("          subPath: docker.sock")
        print("        - name: topology")
        print("          mountPath: /topology.xml")
        print("          subPath: topology.xml")
        print("        - name: dshm")
        print("          mountPath: /dev/shm")
        print("      serviceAccountName: kollaps-listpods")
        print("      hostPID: true")
        print("      volumes:")
        print("      - name: dshm")
        print("        emptyDir:")
        print("          medium: Memory")
        print("      - name: docker-socket")
        print("        hostPath:")
        print("          path: /run")
        print("      - name: topology")
        print("        configMap:")
        print("          name: topology")
        print("          defaultMode: 440")
        print("      hostNetwork: true")

    def print_service(self, service_list):
        if not service_list[0].supervisor:
            print("apiVersion: v1")
            print("kind: Service")
            print("metadata:")
            print("  name: "+service_list[0].name + "-" + self.experiment_UUID)
            print("  labels:")
            print("    app: Kollaps"+service_list[0].name)
            print("spec:")
            print("  clusterIP: None")
            print("  selector:")
            print("    app: Kollaps"+service_list[0].name)
            print("---")

        if(len(service_list) == 1):
            print("apiVersion: v1")
            print("kind: Pod")
            print("metadata:")
            print("  name: "+service_list[0].name + "-" + self.experiment_UUID)
            print("  labels:")
            print("    app: Kollaps"+service_list[0].name)
            if not service_list[0].supervisor:
                print("    "+self.experiment_UUID+": 'true'")
            print("spec:")
            print("  containers:")
            print("  - name: "+service_list[0].name + "-" + self.experiment_UUID)
            print("    image: "+service_list[0].image)
            print("    env:")
            print("      - name: KOLLAPS_UUID")
            print("        value: "+self.experiment_UUID)
            print("      - name: KOLLAPS_ORCHESTRATOR")
            print("        value: 'kubernetes'")

            if not service_list[0].supervisor:
                print("    command: [\"/bin/sh\", \"-c\", \"mkfifo /tmp/Kollaps_hang; exec /bin/sh <> /tmp/Kollaps_hang #\"]")
                if service_list[0].command is not None:
                    print("    args: "+service_list[0].command)
            else:
                if service_list[0].supervisor_port > 0:
                    print("    ports:")
                    print("    - containerPort: "+str(service_list[0].supervisor_port))
                print("    volumeMounts:")
                print("    - name: topology")
                print("      mountPath: /topology.xml")
                print("      subPath: topology.xml")
                print("  serviceAccountName: kollaps-listpods")
                print("  volumes:")
                print("  - name: topology")
                print("    configMap:")
                print("      name: topology")
                print("      defaultMode: 440")

        else:
            print("apiVersion: apps/v1")
            print("kind: Deployment")
            print("metadata:")
            print("  name: "+service_list[0].name + "-" + self.experiment_UUID)
            print("  labels:")
            print("    app: Kollaps"+service_list[0].name)
            print("spec:")
            print("  selector:")
            print("    matchLabels:")
            print("      app: Kollaps"+service_list[0].name)
            print("  replicas: "+str(len(service_list)))
            print("  template:")
            print("    metadata:")
            print("      labels:")
            print("        app: Kollaps"+service_list[0].name)
            print("        "+self.experiment_UUID+": 'true'")
            print("    spec:")
            print("      containers:")
            print("      - name: "+service_list[0].name + "-" + self.experiment_UUID)
            print("        image: "+service_list[0].image)
            print("        env:")
            print("        - name: KOLLAPS_UUID")
            print("          value: "+self.experiment_UUID)
            print("        - name: KOLLAPS_ORCHESTRATOR")
            print("          value: 'kubernetes'")
            print("        command: [\"/bin/sh\", \"-c\", \"mkfifo /tmp/Kollaps_hang; exec /bin/sh <> /tmp/Kollaps_hang #\"]")
            if service_list[0].command is not None:
                print("        args: "+service_list[0].command)


    def print_topology(self):
        try:
            topology = open(self.topology_file, mode='r')
            topo = topology.read()
            topology.close()
        except:
            print(self.topology_file+": bad file path")
            exit(1)
        print("apiVersion: v1")
        print("kind: ConfigMap")
        print("metadata:")
        print("  name: topology")
        print("data:")
        print("  topology.xml: \"" + topo.replace("\n", "\\n").replace("\t", "\\t").replace("\"", "\\\"") + "\"")

    def generate(self, pool_period, max_flow_age, threading_mode, shm_size, aeron_lib_path, aeron_term_buffer_length, aeron_ipc_term_buffer_length, bw_emulation=True):
        number_of_gods = 0
        try:
            if os.getenv('KUBERNETES_SERVICE_HOST'):
                config.load_incluster_config()
            else:
                config.load_kube_config()
            
            number_of_gods = len(client.CoreV1Api().list_node().to_dict()["items"])
            
            
        except Exception as e:
            print_and_fail(e)
        
        self.print_roles()
        print("---")
        self.print_bootstrapper(number_of_gods, pool_period, max_flow_age, threading_mode, shm_size, aeron_lib_path, aeron_term_buffer_length, aeron_ipc_term_buffer_length, bw_emulation)
        print("---")
        for service in self.graph.services:
            self.print_service(self.graph.services[service])
            print("---")
        self.print_topology()
