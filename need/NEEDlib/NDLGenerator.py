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
churn_event_types = ["join", "leave", "crash", "churn"]
churn_events = []
other_events = []
quit_events = []

tags = {}
tags["nodes"] = {}
tags["bridges"] = {}
tags["links"] = {}

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
            if getattr(dec, "event")[0] in churn_event_types:
                churn_events.append(dec)
            elif getattr(dec, "event")[0] == "quit":
                quit_events.append(dec)
            else:
                other_events.append(dec)
        else:
            continue

def checkValidity():
    if len(bootstrapper) != 1:
        print("You must specify a bootstrapper. Exiting.")
        sys.exit(-1)
    if len(nodes) < 2:
        print("You must specify at least two nodes. Exiting.")
        sys.exit(-1)
    if len(quit_events) > 1:
        print("You can only specify one quit action. Exiting.")
        sys.exit(-1)
    if len(quit_events) == 0:
        illegal_churns = []
        for c in churn_events:
            if not "time" in dir(c):
                illegal_churns.append(c)
                print("You cannot set a global churn rate without specifying a quit event. Removing churn event.")
        for c in illegal_churns:
            churn_events.remove(c)

def process_tags():
    for node in nodes:
        nodename = getattr(node, "image")[0]
        if "tags" in dir(node):
            node_tags = getattr(node, "tags")
            for tag in node_tags:
                if not tag in tags["nodes"]:
                    tags["nodes"][tag] = [nodename]
                else:
                    tags["nodes"][tag].append(nodename)
    for bridge in bridges:
        if "names" in dir(bridge): #multi-bridge declaration
            bridgenames = getattr(bridge, "names")
        elif "name" in dir(bridge):
            bridgenames = [getattr(bridge, "name")]
        if "tags" in dir(node):
            bridge_tags = getattr(bridge, "tags")
            for tag in bridge_tags:
                if not tag in tags["bridges"]:
                    tags["bridges"][tag] = [bridgenames]
                else:
                    tags["bridges"][tag].append(bridgenames)
    for link in links:
        linkname = getattr(link, "origin") + "--" + getattr(link, "destination")
        if "tags" in dir(link):
            link_tags = getattr(link, "tags")
            for tag in link_tags:
                if not tag in tags["links"]:
                    tags["links"][tag] = [linkname]
                else:
                    tags["links"][tag].append(linkname)

def addBootstrapper():
    topology.attrib["boot"] = getattr(bootstrapper[0], "image")

def addNodes():
    nodes_element = ET.SubElement(topology, "services")
    for node in nodes:
        n = ET.SubElement(nodes_element, "service")
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

def get_tagged_elements(element_type, selected_tags):
    result = []
    for tag in selected_tags:
        if len(result) == 0:
            result = tags[element_type][tag]
        else:
            result.append(tags[element_type][tag])
    return result

def addEvents():
    events_element = ET.SubElement(topology, "dynamic")
    for event in other_events: #set, disconnect, reconnect, flap events
        type = getattr(event, "event")
        time = getattr(event, "time")
        selector = getattr(event, "selector")
        if type == "disconnect" or type == "reconnect":
            scope = [] #list of nodes which to disconnect
            if selector[0] == "id_selector":
                scope.append(selector[1])
            elif selector[0] == "tag_selector":
                scope = get_tagged_elements("nodes", selector[1:])
            for targeted_node in scope:
                e = ET.SubElement(events_element, "schedule")
                e.attrib["name"] = targeted_node
                e.attrib["time"] = str(time[1])
                #disconnect events
                if type == "disconnect":
                    e.attrib["action"] = "disconnect"
                    if len(time) == 3:
                        e2 = ET.SubElement(events_element, "schedule")
                        e2.attrib["name"] = targeted_node
                        e2.attrib["time"] = str(time[2])
                        e2.attrib["action"] = "reconnect"
                #reconnect events
                elif type == "reconnect":
                    e.attrib["action"] = "reconnect"
        elif isinstance(type, list):
            scope = []
            if selector[0] == "link_selector":
                scope.append(selector[1])
            elif selector[0] == "tag_selector":
                scope = get_tagged_elements("links", selector[1:])
            #(link property) set events
            if type[0] == "set":
                for targeted_link in scope:
                    e = ET.SubElement(events_element, "schedule")
                    e.attrib["origin"] = targeted_link.split("--")[0]
                    e.attrib["dest"] = targeted_link.split("--")[1]
                    e.attrib["time"] = str(time[1])
                    for property in type[1]:
                        if property[0] == "latency" or property[0] == "drop" \
                                    or property[0] == "upload" or property[0] == "jitter":
                                e.attrib[property[0]] = str(property[1])
                        else:
                            print("You can't change link attribute " + property[0] + " at runtime. Skippping.")
            #flap events
            elif type[0] == "flap":
                for targeted_link in scope:
                    orig = targeted_link.split("--")[0]
                    dest = targeted_link.split("--")[1]
                    current_time = time[1]
                    down = True
                    while current_time < time[2]:
                        e = ET.SubElement(events_element, "schedule")
                        e.attrib["origin"] = orig
                        e.attrib["dest"] = dest
                        e.attrib["time"] = str(float("%.3f" % current_time)) #hack due to rounding errors
                        if down:
                            e.attrib["loss"] = str(1.0)
                        else:
                            e.attrib["loss"] = str(0.0)
                        down = not down
                        current_time += type[1]
                    #by default bring the link up again in the end
                    if not down:
                        e = ET.SubElement(events_element, "schedule")
                        e.attrib["origin"] = orig
                        e.attrib["dest"] = dest
                        e.attrib["time"] = str(float("%.3f" % current_time)) #hack due to rounding errors
                        e.attrib["loss"] = str(0.0)

    for event in churn_events: #set, disconnect, reconnect, flap events
        pass #TODO

def makeXML():
    addBootstrapper()
    addNodes()
    addBridges()
    addLinks()
    process_tags()
    addEvents()

def ndl_generate(declarations):
    order(declarations)
    checkValidity()
    makeXML()

    ugly_xml = ET.tostring(topology, encoding='utf-8', method='xml')
    reparsed = minidom.parseString(ugly_xml)
    return reparsed.toprettyxml(indent="    ")
