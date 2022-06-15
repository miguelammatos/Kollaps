#! /usr/bin/python3
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
import socket
import random
import os

from os import getenv
from subprocess import Popen
from multiprocessing import Process
from time import sleep

from kollaps.Kollapslib.utils import int2ip, ip2int
from kollaps.Kollapslib.utils import print_error, print_and_fail, print_named, print_error_named
from kollaps.Kollapslib.utils import LOCAL_IPS_FILE, REMOTE_IPS_FILE, GOD_IPS_SHARE_PORT


class Bootstrapper(object):
    
    BUFFER_LEN = 1024
    
    def __init__(self, high_level_client, low_level_client):
        self.high_level_client = high_level_client
        self.low_level_client = low_level_client
        
        self.gods = {}
        self.ready_gods = []
        self.aeron_media_driver = None
        self.already_bootstrapped = {}
        self.instance_count = 0
        self.rust_handler = None
        self.heaptracker = False
        
        
    def init_clients(self, high_level_client, low_level_client):
        self.high_level_client = high_level_client
        self.low_level_client = low_level_client
        

    def start_rust_handler(self,containercount):
        if getenv('RUNTIME_EMULATION', 'true') != 'false':
            try:
                #creates files and start manager
                open("/file.lock","x")
                open("/tmp/topoinfo","x")
                open("/tmp/topoinfodashboard","x")
                cmd = ["/usr/bin/communicationmanager",str(containercount),"0.0.0.0"]
                self.rust_handler = Popen(cmd)
                print_named("god", "started rust handler.")
        
            except Exception as e:
                print_error("[Py (god)] failed to start rust handler.")
                print_and_fail(e)

    #add container id to file
    def add_id_container(self,id):
        print_named("god","writing id" + id)
        file = open("/tmp/topoinfo", "a")
        file.write(id+"\n")
        file.close()

    #add the id of the dashboard
    def add_dashboard_id_container(self,id):
        file= open("/tmp/topoinfodashboard", "a")
        file.write(id+"\n")
        file.close()
            
    
    def broadcast_ips(self, sender_sock, random_number):
        msg = "HELLO " + str(random_number)
        while True:
            sender_sock.sendto(bytes(msg, encoding='utf8'), ('<broadcast>', GOD_IPS_SHARE_PORT))
            sleep(2)
    
    
    def broadcast_ready(self, sender_sock):
        msg = "READY"
        while True:
            sender_sock.sendto(bytes(msg, encoding='utf8'), ('<broadcast>', GOD_IPS_SHARE_PORT))
            sleep(2)

    
    def resolve_ips(self, number_of_gods):
        
        try:
            own_ip = "(not yet known)"
            own_ip_int = ip2int("127.0.0.1")
            
            if number_of_gods > 0:
                print_named("god", "ip: " + str(own_ip) + ", nr. of gods: " + str(number_of_gods))
            else:
                print_and_fail('there are no nodes on this "cluster".')
    
    
            # listen for msgs from other gods
            recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            recv_sock.bind(('', GOD_IPS_SHARE_PORT))
    
            # setup broadcast
            sender_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sender_sock.bind(('', GOD_IPS_SHARE_PORT+1))
            sender_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sender_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sender_sock.setblocking(False)
    
            # broadcast local IPs
            random_number = random.getrandbits(128)
            ip_broadcast = Process(target=self.broadcast_ips, args=(sender_sock, random_number, ))
            ip_broadcast.start()
    
            while len(self.gods) < number_of_gods:
                data, addr = recv_sock.recvfrom(self.BUFFER_LEN)
                msg = data.decode("utf-8").split()
                
                print_named("god1", f"{addr[0]} :: {msg}")
                ip_as_int = ip2int(addr[0])
                
                if msg[0] == "READY" and ip_as_int not in self.ready_gods:
                    self.ready_gods.append(ip_as_int)
    
                elif msg[0] == "HELLO" and ip_as_int not in self.gods:
                    self.gods[ip_as_int] = msg[1]
    
            # broadcast ready msgs
            ready_broadcast = Process(target=self.broadcast_ready, args=(sender_sock,))
            ready_broadcast.start()
    
            while len(self.ready_gods) < number_of_gods:
                data, addr = recv_sock.recvfrom(self.BUFFER_LEN)
                msg = data.decode("utf-8").split()
        
                print_named("god2", f"{addr[0]} :: {msg[0]}")
                ipAsInt = ip2int(addr[0])
        
                if msg[0] == "READY" and ipAsInt not in self.ready_gods:
                    self.ready_gods.append(ipAsInt)
                    
            # terminate all broadcasts
            ip_broadcast.terminate()
            ready_broadcast.terminate()
            ip_broadcast.join()
            ready_broadcast.join()
            
            
            # find owr own IP by matching our random_number
            # and delete ourselves from the list of other gods
            for key, value in self.gods.items():
                if str(random_number) == value:
                    own_ip_int = key
                    own_ip = int2ip(own_ip_int)
                    del self.gods[own_ip_int]
                    break
                    
            print_named("god", "ip: " + own_ip + ", nr. of gods: " + str(number_of_gods))
            
            
            # write all known IPs to a file to be read from c++ lib if necessary
            with open(LOCAL_IPS_FILE, 'a') as locals_file:
                locals_file.write(str(own_ip_int))
    
            with open(REMOTE_IPS_FILE, 'a') as remotes_file:
                for god in self.gods:
                    remotes_file.write(str(god) + "\n")
                    
            known_ips = ""
            with open(LOCAL_IPS_FILE, 'r') as file:
                known_ips += "local IP: "
                for line in file.readlines():
                    known_ips += int2ip(int(line.strip())) + ", "
            
            known_ips += "\n           "
            with open(REMOTE_IPS_FILE, 'r') as file:
                known_ips += "remote IPs: "
                for line in file.readlines():
                    known_ips += int2ip(int(line.strip())) + ", "
                
            print_named("god", known_ips)
    
            return self.gods
    
        except Exception as e:
            print_and_fail(e)
    
    
    def bootstrap(self, mode, label, bootstrapper_id):
        msg = "This is just a super class. I does not know what to do.\n"
        msg += "Please verify that the code is calling one of the appropriate orchestrator bootstrappers."
        print_error_named("Bootstrapper", msg)
    
