
from need.NEEDlib.NetGraph import NetGraph
from need.NEEDlib.utils import print_and_fail
from uuid import uuid4


class KubernetesManifestGenerator:
    shm_size = 8000000000
    aeron_lib_path = "/home/daedalus/Documents/aeron4need/cppbuild/Release/lib/libaeronlib.so"

    threading_mode = 'SHARED'			# aeron uses 1 thread
    # threading_mode = 'SHARED_NETWORK'	# aeron uses 2 thread
    # threading_mode = 'DEDICATED'		# aeron uses 3 thread

    pool_period = 0.05
    iterations = 42			# doesnt matter, its here for legacy
    max_flow_age = 2

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

    def print_bootstrapper(self):
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

        print("        - name: SHM_SIZE")
        print("          value: '" + str(self.shm_size) + "'")
        print("        - name: AERON_LIB_PATH")
        print("          value: '" + self.aeron_lib_path + "'")
        print("        - name: AERON_THREADING_MODE")
        print("          value: '" + self.threading_mode + "'")
        print("        - name: AERON_TERM_BUFFER_LENGTH")
        print("          value: '" + str(2*64*1024*1024) + "'")
        print("        - name: AERON_IPC_TERM_BUFFER_LENGTH")
        print("          value: '" + str(2*64*1024*1024) + "'")
        print("        - name: POOL_PERIOD")
        print("          value: '" + str(self.pool_period) + "'")
        print("        - name: ITERATIONS")
        print("          value: '" + str(self.iterations) + "'")
        print("        - name: MAX_FLOW_AGE")
        print("          value: '" + str(self.max_flow_age) + "'")
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

    def generate(self):
        self.print_roles()
        print("---")
        self.print_bootstrapper()
        print("---")
        for service in self.graph.services:
            self.print_service(self.graph.services[service])
            print("---")
        self.print_topology()
