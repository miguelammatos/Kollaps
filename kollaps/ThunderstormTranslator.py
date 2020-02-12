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
from kollaps.Kollapslib.Thunderstorm.Parser import ndl_parse
from kollaps.Kollapslib.Thunderstorm.Generator import ndl_generate

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
