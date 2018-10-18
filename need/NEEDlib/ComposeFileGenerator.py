from need.NEEDlib.NetGraph import NetGraph
from need.NEEDlib.utils import fail
from uuid import uuid4


class ComposeFileGenerator:
    def __init__(self, topology_file, graph):
        self.graph = graph  # type: NetGraph
        self.topology_file = topology_file
        self.experiment_UUID = str(uuid4())

    def print_header(self):
        print("version: \"3.3\"")
        print("services:")

    def print_bootstrapper(self):
        print("  bootstrapper:")
        print("    image: " + self.graph.bootstrapper)
        print("    command: [\"-s\", \"" + self.experiment_UUID + "\"]")
        print("    deploy:")
        print("      mode: global")
        print("    environment:")
        print("      NEED_UUID: '" + self.experiment_UUID + "'")
        print("    labels:")
        print("      " + "boot"+self.experiment_UUID + ": \"true\"")
        print("    volumes:")
        print("      - type: bind")
        print("        source: /var/run/docker.sock")
        print("        target: /var/run/docker.sock")
        print('      - "NEEDtopo:/opt/NEED"')
        print("    configs:")
        print("      - source: topology")
        print("        target: /topology.xml")
        print("        uid: '0'")
        print("        gid: '0'")
        print("        mode: 0555")
        print("    networks:")
        print("      - NEEDnet")
        print("")

    def print_service(self, service_list):
        print("  " + service_list[0].name + "-" + self.experiment_UUID + ":")
        print("    image: " + service_list[0].image)
        if not service_list[0].supervisor:
            print('    entrypoint: ["/bin/sh", "-c", "mkfifo /tmp/NEED_hang; /bin/sh -s < /tmp/NEED_hang; #"]')
        if service_list[0].command is not None:
            print("    command: " + service_list[0].command)
        if service_list[0].supervisor_port > 0:
            print("    ports:")
            print('      - "' + str(service_list[0].supervisor_port) + ':' + str(service_list[0].supervisor_port) + '"')
        print("    hostname: " + service_list[0].name)  # + "-" + self.experiment_UUID) This might be the potential cause for the broadcast regression
        if not service_list[0].supervisor:
            print("    labels:")
            print("      " + self.experiment_UUID + ": \"true\"")
        print("    deploy:")
        print("      replicas: " + str(len(service_list)))
        if not service_list[0].supervisor:
            print("      endpoint_mode: dnsrr")
        print("    environment:")
        print("      NEED_UUID: '" + self.experiment_UUID + "'")
        if service_list[0].supervisor:
            print("    configs:")
            print("      - source: topology")
            print("        target: /topology.xml")
            print("        uid: '0'")
            print("        gid: '0'")
            print("        mode: 0555")
        print("    networks:")
        print("      - NEEDnet")
        if service_list[0].supervisor:
            print("      - outside")

        print("")

    def print_configs(self):
        print("configs:")
        print("  topology:")
        print("    file: " + self.topology_file)
        print("")

    def print_networks(self):
        network = self.graph.links[0].network
        for link in self.graph.links:
            if link.network != network:
                fail("Multiple network support is not yet implemented!")

        print("networks:")
        print("  NEEDnet:")
        print("    external:")
        print("      name: " + network)
        print("  outside:")
        print("    driver: overlay")
        print("")

    def print_volumes(self):
        print("volumes:")
        print("  NEEDtopo:")
        print("    external:")
        print("      name: need_topo")
        print("")

    def generate(self):
        self.print_header()
        self.print_bootstrapper()
        for service in self.graph.services:
            self.print_service(self.graph.services[service])
        self.print_volumes()
        self.print_configs()
        self.print_networks()
