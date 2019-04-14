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
    'to': 'TO'
}

tokens = ['ID', 'INSTANT', 'INTEGER', 'FLOAT', 'LINKINSTANCE', 'COMMANDS', 'EQ'] + list(reserved.values())

#literals = "="

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

t_ignore = " \t"

def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

#Build the lexer

lex.lex()

class NDLDeclaration:
    pass

class BootstrapperDeclaration(NDLDeclaration):
    pass

class NodeDeclaration(NDLDeclaration):
    pass

class BridgeDeclaration(NDLDeclaration):
    pass

class LinkDeclaration(NDLDeclaration):
    pass

class EventDeclaration(NDLDeclaration):
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
                     | link_declaration'''
#                     | event_declaration'''
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
        print("one-sided. p[0] = " + str(p[0]))
    else:
        if "symmetric" in p[2]:
            p[1].append(p[1][1])
            print("symmetric. p[1] = " + str(p[1]))
        else:
            p[1].append(p[2][1])
            print("asymmetric. p[1] = " + str(p[1]))
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

#def p_time(p):
#    '''time : AT INSTANT
#            | FROM INSTANT TO INSTANT'''
#    if p[1] == 'at':
#        p[0] = Time(start=p[2], end=-1)
#    elif p[1] == 'from' and p[3] == 'to':
#        p[0] = Time(start=p[2], end=p[4])

def p_error(p):
    print("Syntax error at '%s'" % p.value)

#compile

yacc.yacc()

declarations = [] #add one parsed object per input line

def ndl_parse(input):
    result = yacc.parse(input, debug=False)
    return result
