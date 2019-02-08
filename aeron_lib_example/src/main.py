#! /usr/bin/python 

import sys, signal, time, struct, socket

from argparse import ArgumentParser, ArgumentError

import Communicator as comm



lib_path = "/home/daedalus/Documents/aeron4need/cppbuild/Release/lib/libaeronlib.so"


running = True

def signal_handler(sig, frame):
		global running
		running = False
		print(' Ctrl+C pressed.')
		comm.shutdown()
		
		exit(0)


def ip2int(addr):
	return struct.unpack("!I", socket.inet_aton(addr))[0]


def int2ip(addr):
	return socket.inet_ntoa(struct.pack("!I", addr))




def main(args):

	ids_list = [167772165, 167772166, 167772167, 167772168]

	try:
		
		self_id = ip2int(str(sys.argv[1]))
		ids_list.remove(self_id)
		comm.init(self_id, ids_list, lib_path)
		
		while running:
			
			input()
			
			if self_id == 167772165:
				comm.add_flow(111, [12, 13, 14, 15, 16])
				comm.add_flow(222, [29, 28, 27])
			
			
			if self_id == 167772166:
				comm.add_flow(333, [31, 35])
				comm.add_flow(444, [44, 46, 48, 484])
			
			
			if self_id == 167772167:
				comm.add_flow(555, [52])
				comm.add_flow(666, [62, 63, 61, 69])
			
			
			comm.broadcast_flows()
		
		
	except ArgumentError as e:
		print(e, file=sys.stderr)
		return -1

	except Exception as e:
		print(e, file=sys.stderr)
		return -2


	#comm.shutdown()


if __name__ == '__main__':
	signal.signal(signal.SIGINT, signal_handler)
	exit(main(sys.argv))


