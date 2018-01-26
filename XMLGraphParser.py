import xml.etree.ElementTree as ET
from utils import fail
from NetGraph import NetGraph


class XMLGraphParser:
    def __init__(self, file, graph):
        self.file = file
        self.graph = graph  # type: NetGraph

    def parse_services(self, root):
        for service in root:
            if service.tag != 'service':
                fail('Invalid tag inside <services>: ' + service.tag)
            if 'name' not in service.attrib or 'image' not in service.attrib:
                fail('A service needs a name and an image attribute.')
            if not service.attrib['name'] or not service.attrib['image']:
                fail('A service needs a name and an image attribute.')

            replicas = 1
            if 'replicas' in service.attrib:
                try:
                    replicas = int(service.attrib['replicas'])
                except:
                    fail('replicas attribute must be a valid integer.')

            for i in range(replicas):
                    self.graph.new_service(service.attrib['name'], service.attrib['image'])

    def parse_bridges(self, root):
        for bridge in root:
            if bridge.tag != 'bridge':
                fail('Invalid tag inside <bridges>: ' + bridge.tag)
            if 'name' not in bridge.attrib:
                fail('A bridge needs to have a name.')
            if not bridge.attrib['name']:
                fail('A bridge needs to have a name.')
            self.graph.new_bridge(bridge.attrib['name'])

    def parse_links(self, root):
        for link in root:
            if link.tag != 'link':
                fail('Invalid tag inside <links>: ' + link.tag)
            if 'origin' not in link.attrib or 'dest' not in link.attrib or 'latency' not in link.attrib or \
                    'drop' not in link.attrib or 'upload' not in link.attrib or 'download' not in link.attrib or \
                    'network' not in link.attrib:
                fail("Incomplete link description.")
            self.graph.new_link(link.attrib['origin'], link.attrib['dest'], link.attrib['latency'],
                                link.attrib['drop'], link.attrib['upload'], link.attrib['network'])
            self.graph.new_link(link.attrib['dest'], link.attrib['origin'], link.attrib['latency'],
                                link.attrib['drop'], link.attrib['download'], link.attrib['network'])

    def fill_graph(self):
        XMLtree = ET.parse(self.file)
        root = XMLtree.getroot()
        if root.tag != 'experiment':
            fail('Not a valid NEED topology file, root is not <experiment>')

        services = None
        bridges = None
        links = None
        for child in root:
            if child.tag == 'services':
                if services is not None:
                    fail("Only one <services> block is allowed.")
                services = child
            elif child.tag == 'bridges':
                if bridges is not None:
                    fail("Only one <bridges> block is allowed.")
                bridges = child
            elif child.tag == 'links':
                if links is not None:
                    fail("Only one <links> block is allowed.")
                links = child
            else:
                fail('Unknown tag: ' + child.tag)

        # Links must be parsed last
        self.parse_services(services)
        self.parse_bridges(bridges)
        self.parse_links(links)
