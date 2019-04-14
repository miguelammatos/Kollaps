import sys
import ast
from xml.etree import ElementTree as ET
from xml.dom import minidom
from need.NEEDlib.NDLParser import BootstrapperDeclaration, NodeDeclaration, BridgeDeclaration, LinkDeclaration, EventDeclaration

if sys.version_info >= (3, 0):
    from typing import Dict, List, Tuple

bootstrapper = []
nodes = []
bridges = []
links = []
events = []

topology = ET.Element("experiment")

def order(declarations):
    for dec in declarations:
        if isinstance(dec, BootstrapperDeclaration):
            if len(bootstrapper) == 0:
                bootstrapper.append(dec)
            else:
                print("You must only specify exactly one bootstrapper. Exiting.")
                sys.exit(-1)
        elif isinstance(dec, NodeDeclaration):
            nodes.append(dec)
        elif isinstance(dec, BridgeDeclaration):
            bridges.append(dec)
        elif isinstance(dec, LinkDeclaration):
            links.append(dec)
        elif isinstance(dec, EventDeclaration):
            events.append(dec)
        else:
            pass

def checkValidity():
    if len(bootstrapper) != 1:
        print("You must specify a bootstrapper. Exiting.")
        sys.exit(-1)
    if len(nodes) < 2:
        print("You must specify at least two nodes. Exiting.")
        sys.exit(-1)

def addBootstrapper():
    topology.attrib["boot"] = getattr(bootstrapper[0], "image")

def addNodes():
    nodes_element = ET.SubElement(topology, "services")
    for node in nodes:
        n = ET.SubElement(nodes_element, getattr(node, "image")[0])
        image = getattr(node, "image")
        n.attrib["name"] = image[0]
        n.attrib["image"] = image[1]
        if len(image) == 3:
            n.attrib["replicas"] = str(image[2])
        attrs = dir(node)
        if "command" in attrs:
            n.attrib["command"] = getattr(node, "command")[0]
        if "supervisor" in attrs:
            sup = getattr(node, "supervisor")
            if not sup is None:
                n.attrib["supervisor"] = "true"
                if not sup[0] == "true":
                    n.attrib["port"] = str(sup[0])
        if "share_reuse" in attrs:
            for attrib in getattr(node, "share_reuse"):
                n.attrib[attrib[1]] = "true"
        ### for testing only, can be removed in the end ###
        if "tags" in dir(node):
            n.attrib["tags"] = getattr(node, "tags")

def addBridges():
    bridges_element = ET.SubElement(topology, "bridges")

    for bridge in bridges:
        if "names" in dir(bridge): #multi-bridge declaration
            for br in getattr(bridge, "names"):
                b = ET.SubElement(bridges_element, "bridge")
                b.attrib["name"] = br
        elif "name" in dir(bridge):
            b = ET.SubElement(bridges_element, "bridge")
            b.attrib["name"] = getattr(bridge, "name")
            b.attrib["tags"] = getattr(bridge, "tags")

def addLinks():
    links_element = ET.SubElement(topology, "links")
    for link in links:
        l = ET.SubElement(links_element, "link")
        l.attrib["origin"] = getattr(link, "origin")
        l.attrib["dest"] = getattr(link, "destination")
        if "latency" in dir(link):
            l.attrib["latency"] = str(getattr(link, "latency")[0])
        if "bw" in dir(link):
            bw = getattr(link, "bw")
            l.attrib["upload"] = bw[0]
            if len(bw) == 2:
                l.attrib["download"] = bw[1]
        if "jitter" in dir(link):
            l.attrib["jitter"] = str(getattr(link, "jitter")[0])
        if "drop" in dir(link):
            l.attrib["drop"] = str(getattr(link, "drop")[0])
        if "network" in dir(link):
            l.attrib["network"] = getattr(link, "network")[0]
        ### for testing only, can be removed in the end ###
        if "tags" in dir(link):
            l.attrib["tags"] = getattr(link, "tags")

def addEvents():
    events_element = ET.SubElement(topology, "dynamic")

def makeXML():
    addBootstrapper()
    addNodes()
    if len(bridges) > 0:
        addBridges()
    if len(links) > 0:
        addLinks()
    if len(events) > 0:
        addEvents()

def ndl_generate(declarations):
    order(declarations)
    checkValidity()
    makeXML()

    ugly_xml = ET.tostring(topology, encoding='utf-8', method='xml')
    reparsed = minidom.parseString(ugly_xml)
    return reparsed.toprettyxml(indent="    ")
