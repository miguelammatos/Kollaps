from need.NEEDlib.NDLParser import ndl_parse
from need.NEEDlib.NDLGenerator import ndl_generate

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List, Tuple

inputs = []
parsed_declarations = []

def main():
    try:
        with open(sys.argv[1], 'r') as file:
            declarations = file.readlines()
    except IOError:
        print("Error reading file. Exiting.")
        sys.exit(-1)
    for line in declarations:
        if len(line.strip()) > 0 and not line.strip()[0] == '#':
            try:
                parsed_declarations.append(ndl_parse(line.strip()))
            except:
                print("Could not parse line: \"" + line.strip() + "\". Skipping.")
                continue

    s=12345
    if len(sys.argv) > 3 and sys.argv[2] == "-s":
        try:
            s = int(sys.argv[3])
        except:
            print("Illegal seed, not an int. Using standard seed of 12345.")
    print(ndl_generate(parsed_declarations, seed=s))

if __name__ == "__main__":
    main()
