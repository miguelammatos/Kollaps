#! /usr/bin/python 

import struct

from ctypes import CDLL, CFUNCTYPE, POINTER, c_voidp, c_int, cast
from array import array


class Comms:
	shared_obj = None
	callback = None


def python_callback(bandwidth, link_count, link_list):
	print("Python: throughput: " + str(bandwidth) + " links: " + str(link_count), end=" [")
	for i in range(link_count):
		print(" " + str(link_list[i]), end="")

	print("]")


def register_callback(callback):
	CALLBACKTYPE = CFUNCTYPE(c_voidp, c_int, c_int, POINTER(c_int))
	c_callback = CALLBACKTYPE(callback)
	Comms.callback = c_callback
	Comms.shared_obj.registerCallback(c_callback)


def init(stream_id, ids_list, lib_path):
	Comms.shared_obj = CDLL(lib_path)
	Comms.shared_obj.init(stream_id, len(ids_list), (c_int * len(ids_list))(*ids_list))
	register_callback(python_callback)


def add_flow(throughput, link_list):
	Comms.shared_obj.addFlow(throughput, len(link_list), (c_int * len(link_list))(*link_list))


def broadcast_flows():
	Comms.shared_obj.flush()


def shutdown():
	Comms.shared_obj.shutdown();




def add_stuff_list():
	# calling with a list:
	py_list = [1, 2, 3, 4]

	Comms.shared_obj.addStuff(2000, 4, (c_int * len(py_list))(*py_list))
	py_list.append(5)
	Comms.shared_obj.addStuff(3000, 5, (c_int * len(py_list))(*py_list))

	# using a c_int list (usefull if the list has a fixed size):
	c_list = (c_int * 3)(1, 2, 3)  # You can define it here
	for i in range(3):  # or fill it in dynamically
		c_list[i] = c_int(i)

	Comms.shared_obj.addStuff(4000, 3, c_list)


def add_stuff_array():
	# using array.array
	py_array = array('i', [1, 2, 3, 4, 5, 6])
	Comms.shared_obj.addStuff(5000, len(py_array), cast(py_array.buffer_info()[0], POINTER(c_int)))
	py_array.append(7)
	Comms.shared_obj.addStuff(6000, len(py_array), cast(py_array.buffer_info()[0], POINTER(c_int)))

