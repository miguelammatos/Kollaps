from ctypes import CDLL, c_float, CFUNCTYPE, c_voidp, c_int, c_ulong, c_uint, byref
import struct
import socket
from time import sleep


def ip2int(addr):
    return struct.unpack("!I", socket.inet_aton(addr))[0]

def int2ip(addr):
    return socket.inet_ntoa(struct.pack("!I", addr))

def callback(ip, data, backlog):
    print(f'{ip} {data} {backlog}')

if __name__ == '__main__':
    CALLBACKTYPE = CFUNCTYPE(c_voidp, c_uint, c_ulong, c_uint)
    c_callback = CALLBACKTYPE(callback)

    TCAL = CDLL("./libTCAL.so")
    
    TCAL.init(55, 1000)
    TCAL.registerUsageCallback(c_callback)
    TCAL.initDestination(ip2int("10.0.0.8"),50000, 0, c_float(0.0), c_float(0.0))
    TCAL.initDestination(ip2int("10.0.0.1"),10000, 5, c_float(0.0), c_float(0.0))
    TCAL.initDestination(ip2int("10.0.0.6"),10000, 5, c_float(0.0), c_float(0.0))
    for i in range(1000):
        TCAL.updateUsage()
        sleep(0.1)
    #TCAL.changeBandwidth(ip2int("10.0.0.8"), 5000)
    #for i in range(20):
    #    TCAL.updateUsage()
    #    sleep(1)
    TCAL.tearDown(0)
