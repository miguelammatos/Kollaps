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
import sys
import ast
import random
import datetime
from xml.etree import ElementTree as ET
from xml.dom import minidom
from kollaps.Kollapslib.Thunderstorm.Parser import BootstrapperDeclaration, NodeDeclaration, BridgeDeclaration, LinkDeclaration, EventDeclaration

if sys.version_info >= (3, 0):
    from typing import Dict, List, Tuple

bootstrapper = []
nodes = []
bridges = []
links = []
nodenames = []
bridgenames = []

churn_event_types = ["join", "leave", "crash", "churn", "disconnect", "reconnect"]
churn_events = []
other_events = []
quit_events = []

tags = {}
tags["nodes"] = {}
tags["bridges"] = {}
tags["links"] = {}

#data structures to keep track of how many instances have joined
#and how many are not disconnected
up = {}
connected = {}

topology = ET.Element("experiment")

def getRandomMoments(start, end, quantity):
    moments = []
    for i in range(quantity):
        moments.append(float("%.3f" % random.uniform(start, end)))
    return moments

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
        nodenames.append(image[0])
        up[image[0]] = [] #initialize bookkeeping for dynamic states
        connected[image[0]] = []
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
#        if "tags" in dir(node):
#            n.attrib["tags"] = getattr(node, "tags")

def addBridges():
    bridges_element = ET.SubElement(topology, "bridges")

    for bridge in bridges:
        if "names" in dir(bridge): #multi-bridge declaration
            for br in getattr(bridge, "names"):
                b = ET.SubElement(bridges_element, "bridge")
                b.attrib["name"] = br
                bridgenames.append(br)
        elif "name" in dir(bridge):
            b = ET.SubElement(bridges_element, "bridge")
            bridgenames.append(getattr(bridge, "name"))
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
#        if "tags" in dir(link):
#            l.attrib["tags"] = getattr(link, "tags")

#finds all entities of a certain type with at least one of any number of defined tags
def get_tagged_elements(element_type, selected_tags):
    result = []
    for tag in selected_tags:
        if len(result) == 0:
            result = tags[element_type][tag]
        else:
            result.append(tags[element_type][tag])
    return result

#finds all entities for a certain (ID/link/tag) selector for any entity type.
def getScope(selector, node=False, link=False, bridge=False):
    scope = [] #list of nodes
    if selector[0] == "id_selector" or selector[0] == "link_selector":
        scope.append(selector[1])
    elif selector[0] == "tag_selector":
        if node:
            scope += get_tagged_elements("nodes", selector[1:])
        if link:
            scope += get_tagged_elements("links", selector[1:])
        if bridge:
            scope += get_tagged_elements("bridges", selector[1:])
    return scope

def addOtherEvents():
    events_element = ET.SubElement(topology, "dynamic")
    for event in other_events: #set, disconnect, reconnect, flap events
        evt = getattr(event, "event")
        type = evt[0]
        time = getattr(event, "time")
        selector = getattr(event, "selector")
        scope = getScope(selector, link=True)
        #(link property) set events
        if type == "set":
            for targeted_link in scope:
                e = ET.SubElement(events_element, "schedule")
                e.attrib["origin"] = targeted_link.split("--")[0]
                e.attrib["dest"] = targeted_link.split("--")[1]
                e.attrib["time"] = str(time[1])
                for property in evt[1]:
                    if property[0] == "latency" or property[0] == "drop" \
                                or property[0] == "upload" or property[0] == "jitter":
                            e.attrib[property[0]] = str(property[1])
                    else:
                        print("You can't change link attribute " + property[0] + " at runtime. Skippping.")
        #flap events
        elif type == "flap":
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
                    current_time += evt[1]
                #by default bring the link up again in the end
                if not down:
                    e = ET.SubElement(events_element, "schedule")
                    e.attrib["origin"] = orig
                    e.attrib["dest"] = dest
                    e.attrib["time"] = str(float("%.3f" % current_time)) #hack due to rounding errors
                    e.attrib["loss"] = str(0.0)

def join_leave(type, quantity, selector, time):
    scope = getScope(selector, node=True, link=True, bridge=True)
    events_element = topology.find('dynamic')
    for targeted_entity in scope:
        if targeted_entity in bridgenames: #it's a bridge
            e = ET.SubElement(events_element, "schedule")
            e.attrib["name"] = targeted_entity
            e.attrib["time"] = str(time[1])
            e.attrib["action"] = type
        elif "--" in targeted_entity: #it's a link
            e = ET.SubElement(events_element, "schedule")
            e.attrib["origin"] = targeted_entity.split("--")[0]
            e.attrib["dest"] = targeted_entity.split("--")[1]
            e.attrib["time"] = str(time[1])
            e.attrib["action"] = type
        elif targeted_entity in nodenames: #it's a node
            coeff = 1 if type == "join" else -1
            if len(time) == 2:
                e = ET.SubElement(events_element, "schedule")
                e.attrib["name"] = targeted_entity
                e.attrib["time"] = str(time[1])
                e.attrib["action"] = type
                if quantity > 1:
                    e.attrib["amount"] = str(quantity)
                up[targeted_entity].append((time[1], coeff*quantity))
            else: #join/leave over a period of time
                mom = getRandomMoments(time[1], time[2], quantity)
                for m in mom:
                    e = ET.SubElement(events_element, "schedule")
                    e.attrib["name"] = targeted_entity
                    e.attrib["time"] = str(m)
                    e.attrib["action"] = type
                    up[targeted_entity].append((m, coeff))

def crash_churn(type, quantity, selector, time, percentage=0.0):
    scope = getScope(node=True, selector=selector)
    events_element = topology.find('dynamic')
    for targeted_node in scope:
        if len(time) == 2:
            e = ET.SubElement(events_element, "schedule")
            e.attrib["name"] = targeted_node
            e.attrib["time"] = str(time[1])
            e.attrib["action"] = "crash"
            if quantity > 1:
                e.attrib["amount"] = str(quantity)
            up[targeted_entity].append((time[1], -1*quantity))
        else: #crash/churn over a period of time
            mom = getRandomMoments(time[1], time[2], quantity)
            for m in mom:
                e = ET.SubElement(events_element, "schedule")
                e.attrib["name"] = targeted_node
                e.attrib["time"] = str(m)
                e.attrib["action"] = "crash"
                up[targeted_node].append((m, -1))
                if type == "churn" and random.uniform(0, 1) < percentage:
                    e = ET.SubElement(events_element, "schedule")
                    e.attrib["name"] = targeted_node
                    e.attrib["time"] = str(m)
                    e.attrib["action"] = "join"
                    up[targeted_node].append((m, 1))

def disconnect_reconnect(type, quantity, selector, time):
    scope = getScope(node=True, selector=selector)
    events_element = topology.find('dynamic')
    for targeted_node in scope:
        e = ET.SubElement(events_element, "schedule")
        e.attrib["name"] = targeted_node
        e.attrib["time"] = str(time[1])
        if quantity > 1:
            e.attrib["amount"] = str(quantity)
        #disconnect events
        if type == "disconnect":
            e.attrib["action"] = "disconnect"
            up[targeted_node].append((time[1], -1*quantity))
            connected[targeted_node].append((time[1], -1*quantity))
            if len(time) == 3:
                e2 = ET.SubElement(events_element, "schedule")
                e2.attrib["name"] = targeted_node
                e2.attrib["time"] = str(time[2])
                e2.attrib["action"] = "reconnect"
                if quantity > 1:
                    e2.attrib["amount"] = str(quantity)
                up[targeted_node].append((time[2], quantity))
                connected[targeted_node].append((time[2], quantity))
        #reconnect events
        elif type == "reconnect":
            e.attrib["action"] = "reconnect"
            up[targeted_node].append((time[1], -1*quantity))
            connected[targeted_node].append((time[1], quantity))

#We do this first to know the respective number of online services
#for events that have a percentage as quantity.
def addAbsoluteNumberEvents():
    absolute_events = [e for e in churn_events if (len(getattr(e, "event")) == 1) \
                or (len(getattr(e, "event")) > 1 and isinstance(getattr(e, "event")[1], int))]
    for event in absolute_events:
        evt = getattr(event, "event")
        type = evt[0]
        quantity = 1 if len(getattr(event, "event")) == 1 else getattr(event, "event")[1]
        time = getattr(event, "time")
        selector = getattr(event, "selector")

        #it is not impossible to think that these could be merged even more
        if type == "join" or type == "leave":
            join_leave(type, quantity, selector, time)

        elif type == "crash" or type == "churn":
            replacement = 0.0
            if len(evt) == 3:
                replacement = float(evt[2].replace("%", ""))/100.0
            crash_churn(type, quantity, selector, time, replacement)

        elif type == "disconnect" or type == "reconnect":
            disconnect_reconnect(type, quantity, selector, time)

def sort_bookkeeping_lists():
    for key in up:
        up[key].sort(key=lambda change: change[0])
    for key in connected:
        connected[key].sort(key=lambda change: change[0])

def calculate_active_nodes(nodename, time):
    node_events = up[nodename]
    up_nodes = 0
    index = 0
    while node_events[index][0] < time:
        up_nodes += node_events[index][1]
        if index < len(node_events)-1:
            index += 1
        else:
            break
    return up_nodes

def calculate_disconnected_nodes(nodename, time):
    node_events = connected[nodename]
    connected_nodes = 0
    index = 0
    while node_events[index][0] < time:
        connected_nodes += node_events[index][1]
        if index < len(node_events)-1:
            index += 1
        else:
            break
    return connected_nodes

#we calculate these after those with absolute numbers, because only then
#can we know what to take the percentage of.
#we always round down.
def addPercentageEvents():
    percentage_events = [e for e in churn_events if len(getattr(e, "event")) > 1 \
                and not isinstance(getattr(e, "event")[1], int)]
    percentage_events.sort(key=lambda event: getattr(event, "type")) #continuous first, then instant
    percentage_events.sort(key=lambda event: getattr(event, "time")[1]) #then sort by start time. the above sorting breaks ties
    for event in percentage_events:
        sort_bookkeeping_lists()
        type = getattr(event, "event")[0]
        percentage = float(getattr(event, "event")[1].replace("%", ""))/100.0
        time = getattr(event, "time")
        selector = getattr(event, "selector")
        scope = getScope(selector, node=True) #here it's the same for all types of event
        if type == "join" or type == "leave":
            for nodename in scope:
                active_nodes = calculate_active_nodes(nodename, time[1])
                to_target = int(percentage*float(active_nodes))
                if to_target > 0:
                    join_leave(type, to_target, ["id_selector", nodename], time)
        elif type == "crash" or type == "churn":
            replacement = 0.0
            if len(getattr(event, "event")) == 3:
                replacement = float(getattr(event, "event")[2].replace("%", ""))/100.0
            for nodename in scope:
                active_nodes = calculate_active_nodes(nodename, time[1])
                to_target = int(percentage*float(active_nodes))
                if to_target > 0:
                    crash_churn(type, to_target, ["id_selector", nodename], time, replacement)
        elif type == "disconnect" or type == "reconnect":
            for nodename in scope:
                if type == "disconnect":
                    active_nodes = calculate_active_nodes(nodename, time[1])
                    to_target = int(percentage*float(active_nodes))
                    if to_target > 0:
                        disconnect_reconnect("disconnect", to_target, ["id_selector", nodename], time)
                elif type == "reconnect":
                    active_ndoes = calculate_disconnected_nodes(nodename, time[1])
                    to_target = int(percentage*float(active_nodes))
                    if to_target > 0:
                        disconnect_reconnect("reconnect", to_target, ["id_selector", nodename], time)

def makeXML():
    addBootstrapper()
    addNodes()
    addBridges()
    addLinks()
    process_tags()
    addOtherEvents()
    addAbsoluteNumberEvents()
    addPercentageEvents()

def addInfo(seed):
    now = datetime.datetime.now()
    e = ET.SubElement(topology, "informations")
    e.attrib["source"] = "Topology compiled with ThunderstormTranslator on " + now.strftime("%d.%m.%Y %H:%M")
    e.attrib["seed"] = str(seed)

def ndl_generate(declarations, seed=12345):
    random.seed(seed)
    order(declarations)
    checkValidity()
    makeXML()
    addInfo(seed)

    ugly_xml = ET.tostring(topology, encoding='utf-8', method='xml')
    reparsed = minidom.parseString(ugly_xml)
    return reparsed.toprettyxml(indent="    ")
