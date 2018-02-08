from __future__ import print_function
import sys


BYTE_LIMIT = 255
SHORT_LIMIT = 65535
INT_LIMIT = 4294967296

def fail(message):
    print("An error occured, terminating!", file=sys.stderr)
    print("Error Message: " + message, file=sys.stderr)
    exit(-1)
