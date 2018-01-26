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
            self.graph.new_service(service.attrib['name'], service.attrib['image'])

    def parse_bridges(self, root):
        pass

    def parse_links(self, root):
        pass

    def fill_graph(self):
        XMLtree = ET.parse(self.file)
        root = XMLtree.getroot()
        if root.tag != 'experiment':
            fail('Not a valid NEED topology file, root is not <experiment>')
        for child in root:
            if child.tag == 'services':
                self.parse_services(child)
            elif child.tag == 'bridges':
                self.parse_bridges(child)
            elif child.tag == 'links':
                self.parse_links(child)
            else:
                fail('Unknown tag: ' + child.tag)
