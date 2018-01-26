from __future__ import print_function
import sys


def fail(message):
    print("An error occured, terminating!", file=sys.stderr)
    print("Error Message: " + message, file=sys.stderr)
    exit(-1)
