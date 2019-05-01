
from kubernetes import client, config
from uuid import uuid4

from need.NEEDlib.NetGraph import NetGraph
from need.NEEDlib.utils import print_and_fail, print_error_named


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
        print("    app: NEED")
        print("  name: need-listpods")
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
        print("  name: need-listpods")
        print("  namespace: default")
        print("roleRef:")
        print("  kind: ClusterRole")
        print("  name: listpods")
        print("  apiGroup: rbac.authorization.k8s.io")
        
    def print_bootstrapper(self, number_of_gods, pool_period, max_flow_age, threading_mode, shm_size, aeron_lib_path, aeron_term_buffer_length, aeron_ipc_term_buffer_length):
        print("apiVersion: extensions/v1beta1")
        print("kind: DaemonSet")
        print("metadata:")
        print("  name: bootstrapper")
        print("  labels:")
        print("    boot"+self.experiment_UUID + ": \"true\"")
        print("spec:")
        print("  template:")
        print("    metadata:")
        print("      labels:")
        print("        app: NEED-bootstrapper")
        print("        boot"+self.experiment_UUID + ": \"true\"")
        print("    spec:")
        print("      containers:")
        print("      - name: bootstrapper")
        print("        image: " + self.graph.bootstrapper)
        print("        env:")
        print("        - name: NEED_UUID")
        print("          value: "+self.experiment_UUID)
        print("        - name: NEED_ORCHESTRATOR")
        print("          value: 'kubernetes'")
        print("        - name: NUMBER_OF_GODS")
        print("          value: '" + str(number_of_gods) + "'")
        print("        - name: POOL_PERIOD")
        print("          value: '" + str(pool_period) + "'")
        print("        - name: MAX_FLOW_AGE")
        print("          value: '" + str(max_flow_age) + "'")
        print("        - name: SHM_SIZE")                      # on kubernetes we don't need to create a God container
        print("          value: '" + str(shm_size) + "'")      # so this is not being used
        print("        - name: AERON_LIB_PATH")
        print("          value: '" + str(aeron_lib_path) + "'")
        print("        - name: AERON_THREADING_MODE")
        print("          value: '" + str(threading_mode) + "'")
        print("        - name: AERON_TERM_BUFFER_LENGTH")
        print("          value: '" + str(aeron_term_buffer_length) + "'")
        print("        - name: AERON_IPC_TERM_BUFFER_LENGTH")
        print("          value: '" + str(aeron_ipc_term_buffer_length) + "'")
        print("        args:")
        print("        - -g")
        print("        - "+self.experiment_UUID)
        print("        securityContext:")
        print("          capabilities:")
        print("            add: [\"NET_ADMIN\", \"SYS_ADMIN\"]")
        print("        volumeMounts:")
        print("        - name: docker-socket")
        print("          mountPath: /var/run/docker.sock")
        print("          subPath: docker.sock")
        print("        - name: topology")
        print("          mountPath: /topology.xml")
        print("          subPath: topology.xml")
        print("        - name: dshm")
        print("          mountPath: /dev/shm")
        print("      serviceAccountName: need-listpods")
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
            print("    app: NEED"+service_list[0].name)
            print("spec:")
            print("  clusterIP: None")
            print("  selector:")
            print("    app: NEED"+service_list[0].name)
            print("---")

        if(len(service_list) == 1):
            print("apiVersion: v1")
            print("kind: Pod")
            print("metadata:")
            print("  name: "+service_list[0].name + "-" + self.experiment_UUID)
            print("  labels:")
            print("    app: NEED"+service_list[0].name)
            if not service_list[0].supervisor:
                print("    "+self.experiment_UUID+": 'true'")
            print("spec:")
            print("  containers:")
            print("  - name: "+service_list[0].name + "-" + self.experiment_UUID)
            print("    image: "+service_list[0].image)
            print("    env:")
            print("      - name: NEED_UUID")
            print("        value: "+self.experiment_UUID)
            print("      - name: NEED_ORCHESTRATOR")
            print("        value: 'kubernetes'")

            if not service_list[0].supervisor:
                print("    command: [\"/bin/sh\", \"-c\", \"mkfifo /tmp/NEED_hang; exec /bin/sh <> /tmp/NEED_hang #\"]")
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
                print("  serviceAccountName: need-listpods")
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
            print("    app: NEED"+service_list[0].name)
            print("spec:")
            print("  selector:")
            print("    matchLabels:")
            print("      app: NEED"+service_list[0].name)
            print("  replicas: "+str(len(service_list)))
            print("  template:")
            print("    metadata:")
            print("      labels:")
            print("        app: NEED"+service_list[0].name)
            print("        "+self.experiment_UUID+": 'true'")
            print("    spec:")
            print("      containers:")
            print("      - name: "+service_list[0].name + "-" + self.experiment_UUID)
            print("        image: "+service_list[0].image)
            print("        env:")
            print("        - name: NEED_UUID")
            print("          value: "+self.experiment_UUID)
            print("        - name: NEED_ORCHESTRATOR")
            print("          value: 'kubernetes'")
            print("        command: [\"/bin/sh\", \"-c\", \"mkfifo /tmp/NEED_hang; exec /bin/sh <> /tmp/NEED_hang #\"]")
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

    def generate(self, pool_period, max_flow_age, threading_mode, shm_size, aeron_lib_path, aeron_term_buffer_length, aeron_ipc_term_buffer_length):
        number_of_gods = 0
        try:
            number_of_gods = len(client.CoreV1Api().list_node().to_dict()["items"])
            
        except Exception as e:
            msg = "DockerComposeFileGenerator.py requires special permissions in order to view cluster state.\n"
            msg += "please, generate the .yaml file on a manager node."
            print_error_named("compose_generator", msg)
            print_and_fail(e)
        
        self.print_roles()
        print("---")
        self.print_bootstrapper(number_of_gods, pool_period, max_flow_age, threading_mode, shm_size, aeron_lib_path, aeron_term_buffer_length, aeron_ipc_term_buffer_length)
        print("---")
        for service in self.graph.services:
            self.print_service(self.graph.services[service])
            print("---")
        self.print_topology()
