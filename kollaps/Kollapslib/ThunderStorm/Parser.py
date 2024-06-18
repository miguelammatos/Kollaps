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
import re
import ply.lex as lex #pip install ply
import ply.yacc as yacc

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List, Tuple

reserved = {
    'bootstrapper': 'BOOTSTRAPPER',
    'service': 'SERVICE',
    'image': 'IMAGE',
    'command': 'COMMAND',
    'replicas': 'REPLICAS',
    'supervisor': 'SUPERVISOR',
    'port': 'PORT',
    'share': 'SHARE',
    'reuse': 'REUSE',
    'tags': 'TAGS',
    'bridge': 'BRIDGE',
    'bridges': 'BRIDGES',
    'link': 'LINK',
    'speed': 'SPEED',
    'latency': 'LATENCY',
    'up': 'UP',
    'down': 'DOWN',
    'symmetric': 'SYMMETRIC',
    'jitter': 'JITTER',
    'drop': 'DROP',
    'network': 'NETWORK',
    'at': 'AT',
    'from': 'FROM',
    'to': 'TO',
    'join': 'JOIN',
    'crash': 'CRASH',
    'leave': 'LEAVE',
    'set': 'SET',
    'disconnect': 'DISCONNECT',
    'reconnect': 'RECONNECT',
    'quit': 'QUIT',
    'churn': 'CHURN',
    'replace': 'REPLACE',
    'flap': 'FLAP',
    'percentage': 'PERCENTAGE',
    'ip' : 'IP'
}
tokens = ['ID', 'INSTANT', 'INTEGER', 'FLOAT', 'LINKINSTANCE', 'COMMANDS', 'EQ'] + list(reserved.values())

# Tokens
t_BOOTSTRAPPER = r'bootstrapper'
t_SERVICE = r'service'
t_IMAGE = r'image'
t_COMMAND = r'command'
t_COMMANDS = r'\[\'.*\'(, \'.*\')*\]' #something like ['server', '0', '0']
t_REPLICAS = r'replicas'
t_SUPERVISOR = r'supervisor'
t_PORT = r'port'
t_SHARE = r'share'
t_REUSE = r'reuse'
t_TAGS = r'tags'
t_BRIDGE = r'bridge'
t_BRIDGES = r'bridges'
t_LINK = r'link'
t_LATENCY = r'latency'
t_UP = r'up'
t_DOWN =r'down'
t_SYMMETRIC = r'symmetric'
t_JITTER = r'jitter'
t_DROP = r'drop'
t_NETWORK = r'network'
t_AT = r'at'
t_FROM = r'from'
t_TO = r'to'
t_EQ = r'='
t_JOIN = r'join'
t_CRASH = r'crash'
t_LEAVE = r'leave'
t_SET = r'set'
t_DISCONNECT = r'disconnect'
t_RECONNECT = r'reconnect'
t_QUIT = r'quit'
t_CHURN = r'churn'
t_REPLACE = r'replace'
t_FLAP = r'flap'
t_IP = r'ip'

def t_INSTANT(t):
    r'([0-9]*d)?([0-9]*h)?([0-9]*m)?([0-9]+(\.[0-9]+)?s)?(?<=[0-9](d|h|m|s))' #positive lookbehind
    args = list(filter(None, re.split(r'(\d+\.\d+|\d+)', t.value)))
    time_in_seconds = 0
    amounts = args[::2]
    units = args[1::2]
    for i in range(len(amounts)):
        if units[i] == 'd':
            time_in_seconds += 86400*int(amounts[i])
        elif units[i] == 'h':
            time_in_seconds += 3600*int(amounts[i])
        elif units[i] == 'm':
            time_in_seconds += 60*int(amounts[i])
        elif units[i] == 's':
            time_in_seconds = float(time_in_seconds)
            time_in_seconds += float(amounts[i])
        else:
            return False
        time_in_seconds = float(time_in_seconds)
    t.value = time_in_seconds
    return t

def t_SPEED(t):
    r'[0-9]+(G|M|K)bps'
    return t

def t_PERCENTAGE(t):
    r'[0-9]+%'
    return t

def t_FLOAT(t):
    r'[0-9]+\.[0-9]+' #technically an int that *may* also be a float, eg. for latency etc.
    t.value = float(t.value)
    return t

def t_INTEGER(t):
    r'[0-9]+'
    t.value = int(t.value)
    return t

def t_LINKINSTANCE(t):
    r'[a-zA-Z0-9\.:/\-_]+--[a-zA-Z0-9\.:/\-_]+'
    t.type = reserved.get(t.value, 'LINKINSTANCE')
    return t

def t_ID(t):
    r'[a-zA-Z0-9\.:/\-_]+' # r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value, 'ID')
    return t

def t_ALL(t):
    r'^(?!\s*$).+'
    t.type = reserved.get(t.value,'ALL')


t_ignore = " \t"

def t_error(t):
#    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

#Build the lexer
lex.lex()

class ThunderstormDeclaration:
    pass

class BootstrapperDeclaration(ThunderstormDeclaration):
    pass

class NodeDeclaration(ThunderstormDeclaration):
    pass

class BridgeDeclaration(ThunderstormDeclaration):
    pass

class LinkDeclaration(ThunderstormDeclaration):
    pass

class EventDeclaration(ThunderstormDeclaration):
    pass

class BaremetalNodeAuxDeclaration(ThunderstormDeclaration):
    pass

class Time:
    def __init__(self, start, end):
        self.start = start
        self.end = end

def p_declaration(p):
    '''p_declaration : bootstrapper_declaration
                     | node_declaration
                     | multi_bridge_declaration
                     | bridge_declaration
                     | link_declaration
                     | event_declaration
                     | ip_declaration'''
    p[0] = p[1]

def p_bootstrapper_declaration(p):
    '''bootstrapper_declaration : BOOTSTRAPPER ID'''

    boot = BootstrapperDeclaration()
    setattr(boot, "image", p[2])
    p[0] = boot

def p_node_declaration(p):
    '''node_declaration : node_declaration_list'''

    node = NodeDeclaration()
    for elem in p[1]:
        setattr(node, elem[0], elem[1:])
    p[0] = node

def p_node_declaration_list(p):
    '''node_declaration_list : image_declaration
                             | node_declaration_list node_declaration_element'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]

def p_node_declaration_element(p):
    '''node_declaration_element : supervisor_declaration
                               | share_reuse_declaration
                               | command_declaration
                               | tags'''
    p[0] = p[1]


def p_image_declaration(p):
    '''image_declaration : SERVICE ID IMAGE EQ ID 
                         | image_declaration replica_declaration'''
    if len(p) == 6:
        p[0] = ["image"] + [p[2], p[5]]
    else:
        p[0] = p[1] + [p[2]]

def p_ip_declaration(p):
    '''ip_declaration : SERVICE ID IP EQ INipTEGER ID ID ID ID
                      | ip_declaration'''
    node = BaremetalNodeAuxDeclaration()
    setattr(node,"name",p[2])
    setattr(node,"ip",p[5])
    setattr(node,"machinename",p[6])
    setattr(node,"folder",p[7])
    setattr(node,"topologyfile",p[8])
    setattr(node,"script",p[9])

    p[0] = node


def p_supervisor_declaration(p):
    '''supervisor_declaration : SUPERVISOR
                              | SUPERVISOR port_declaration'''
    if len(p) == 2:
        p[0] = ["supervisor", "true"]
    else:
        p[0] = [p[1], p[2]]

def p_share_reuse_declaration(p):
    '''share_reuse_declaration : SHARE
                               | REUSE
                               | share_reuse_declaration share_reuse_declaration'''
    if(len(p) == 2):
        p[0] = ["share_reuse", p[1]]
    else:
        p[0] = ["share_reuse", p[1], p[2]]

def p_command_declaration(p):
    '''command_declaration : COMMAND EQ COMMANDS'''
    p[0] = ["command", p[3]]


def p_replica_declaration(p):
    '''replica_declaration : REPLICAS EQ INTEGER'''
    p[0] = int(p[3])


def p_port_declaration(p):
    '''port_declaration : PORT EQ INTEGER'''
    p[0] = p[3]

def p_bridge_names(p):
    '''bridge_names : BRIDGES ID
                    | bridge_names ID'''

    if p[1] == "bridges":
        p[0] = ["bridges", p[2]]
    else:
        p[1].append(p[2])
        p[0] = p[1]

def p_multi_bridge_declaration(p):
    '''multi_bridge_declaration : bridge_names'''
    b = BridgeDeclaration()
    setattr(b, "names", p[1][1:])
    p[0] = b

def p_bridge_declaration(p):
    '''bridge_declaration : BRIDGE ID taglist'''
    b = BridgeDeclaration()
    setattr(b, "name", p[2])
    setattr(b, "tags", p[3][1:])
    p[0] = b

def p_link_declaration(p):
    '''link_declaration : LINK LINKINSTANCE link_declaration_list'''
    l = LinkDeclaration()
    setattr(l, "origin", p[2].split('--')[0])
    setattr(l, "destination", p[2].split('--')[1])
    for dec in p[3]:
        setattr(l, dec[0], dec[1:])
    p[0] = l

def p_link_declaration_list(p):
    '''link_declaration_list : link_declaration_element
                             | link_declaration_list link_declaration_element'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]

def p_link_declaration_element(p):
    '''link_declaration_element : latency_declaration
                                | bw_declaration
                                | jitter_declaration
                                | drop_declaration
                                | network_declaration
                                | tags'''
    p[0] = p[1]

def p_latency_declaration(p):
    '''latency_declaration : LATENCY EQ FLOAT'''
    p[0] = ["latency", p[3]]

def p_bw_declaration(p):
    '''bw_declaration : UP EQ SPEED
                      | bw_declaration bw_download_declaration'''
    if len(p) == 4:
        p[0] = ["bw", p[3]]
    else:
        if "symmetric" in p[2]:
            p[1].append(p[1][1])
        else:
            p[1].append(p[2][1])
        p[0] = p[1]

def p_download_declaration(p):
    '''bw_download_declaration : DOWN EQ SPEED
                            | SYMMETRIC'''
    if len(p) == 2:
        p[0] = ["symmetric"]
    else:
        p[0] = ["down", p[3]]

def p_jitter_declaration(p):
    '''jitter_declaration : JITTER EQ FLOAT'''
    p[0] = ["jitter", p[3]]

def p_drop_declaration(p):
    '''drop_declaration : DROP EQ FLOAT'''
    p[0] = ["drop", p[3]]

def p_network_declaration(p):
    '''network_declaration : NETWORK EQ ID'''
    p[0] = ["network", p[3]]

def p_taglist(p):
    '''taglist : TAGS EQ ID
               | taglist ID'''
    if p[1] == "tags":
        p[0] = ["tags", p[3]]
    else:
        p[1].append(p[2])
        p[0] = p[1]

def p_tags(p):
    '''tags : taglist'''
    p[0] = p[1]

def p_event_declaration(p):
    '''event_declaration : instant_event
                         | continuous_event'''
    p[0] = p[1]

def p_instant_event(p):
    '''instant_event : time quit_event
                     | time selector moment_event'''
    e = EventDeclaration()
    setattr(e, "type", "instant")
    setattr(e, "time", p[1])
    if len(p) > 3:
        setattr(e, "selector", p[2])
        setattr(e, "event", p[3])
    else:
        setattr(e, "event", p[2])
    p[0] = e

def p_continuous_event(p):
    '''continuous_event : churn_event
                        | timespan churn_event
                        | timespan selector period_event'''
    #churn is the only type of continuous event that doesn't need a
    #timespan and also not a selector
    e = EventDeclaration()
    setattr(e, "type", "continuous")
    if len(p) > 3:
        setattr(e, "time", p[1])
        setattr(e, "selector", p[2])
        setattr(e, "event", p[3])
    elif len(p) > 2:
        setattr(e, "time", p[1])
        setattr(e, "event", p[2])
    elif len(p) == 2:
        setattr(e, "event", p[1])
    p[0] = e

def p_moment_event(p):
    '''moment_event : join_event
                      | leave_event
                      | crash_event
                      | set_event
                      | disconnect_event
                      | reconnect_event'''
    p[0] = p[1]

def p_period_event(p):
    '''period_event : churn_event
                    | flap_event
                    | disconnect_event
                    | join_event
                    | leave_event
                    | crash_event'''
    p[0] = p[1]

def p_join_event(p):
    '''join_event : JOIN
                  | JOIN INTEGER
                  | JOIN PERCENTAGE'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1], p[2]]

def p_leave_event(p):
    '''leave_event : LEAVE
                   | LEAVE INTEGER
                   | LEAVE PERCENTAGE'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1], p[2]]

def p_crash_event(p):
    '''crash_event : CRASH
                   | CRASH INTEGER
                   | CRASH PERCENTAGE'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1], p[2]]

def p_disconnect_event(p):
    '''disconnect_event : DISCONNECT
                        | DISCONNECT INTEGER
                        | DISCONNECT PERCENTAGE'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1], p[2]]

def p_reconnect_event(p):
    '''reconnect_event : RECONNECT
                       | RECONNECT INTEGER'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1], p[2]]

def p_quit_event(p):
    '''quit_event : QUIT'''
    p[0] = ["quit"]

def p_set_event(p):
    '''set_event : SET link_declaration_list'''
    p[0] = ["set", p[2]]

def p_churn_event(p):
    '''churn_event : CHURN INTEGER
                   | CHURN PERCENTAGE
                   | CHURN INTEGER replace_rate
                   | CHURN PERCENTAGE replace_rate'''
    if len(p) == 3:
        p[0] = ["churn", p[2]]
    elif len(p) > 3:
        p[0] = ["churn", p[2], p[3]]

def p_replace_rate(p):
    '''replace_rate : REPLACE PERCENTAGE'''
    p[0] = p[2]

def p_flap_event(p):
    '''flap_event : FLAP INSTANT'''
    p[0] = ["flap", p[2]]

def p_time(p):
    '''time : AT INSTANT'''
    p[0] = ["time", p[2]]

def p_timespan(p):
    '''timespan : FROM INSTANT TO INSTANT'''
    p[0] = ["time", p[2], p[4]]

def p_selector(p):
    '''selector : ID
                | LINKINSTANCE
                | tags'''
    if isinstance(p[1], list):
        p[0] = ["tag_selector"] + p[1][1:]
    elif "--" in p[1] :
        p[0] = ["link_selector"] + [p[1]]
    else:
        p[0] = ["id_selector"] + [p[1]] #can be a node or a bridge

def p_error(p):
    pass #print("Syntax error at '%s'" % p.value)

#compile
yacc.yacc()

def ndl_parse(input):
    result = yacc.parse(input, debug=False)
    return result
