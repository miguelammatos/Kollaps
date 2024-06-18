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
from kollaps.Kollapslib.ThunderStorm.Generator import ndl_generate
from kollaps.Kollapslib.ThunderStorm.Parser import ndl_parse

import sys
import argparse
if sys.version_info >= (3, 0):
    from typing import Dict, List, Tuple

inputs = []
parsed_declarations = []

def main():
    try:

        parser = argparse.ArgumentParser()
        parser.add_argument("input",help="input")
        parser.add_argument("-s","--seed",default=12345,type=int,help="seed")
        parser.add_argument("-f","--filename",default=None,type=str,help="baremetal ips,machinename,foldername,script")
        opt=parser.parse_args()
        with open(opt.input, 'r') as file:
            declarations = file.readlines()
    except IOError:
        print("Error reading file. Exiting.")
        sys.exit(-1)
    for line in declarations:
        if len(line.strip()) > 0 and not line.strip()[0] == '#':
            try:
                parsed_declarations.append(ndl_parse(line.strip()))
                continue
            except:
                print("Could not parse line: \"" + line.strip() + "\". Skipping.")
                continue
    if opt.filename !=None:
        auxiliarylines = open(opt.filename).readlines()
        for line in auxiliarylines:
            if len(line.strip()) > 0 and not line.strip()[0] == '#':
                try:
                    parsed_declarations.append(ndl_parse(line.strip()))

                except:
                    print("Could not parse line: \"" + line.strip() + "\". Skipping.")
                    continue
    

    print(ndl_generate(parsed_declarations,opt.seed ))


if __name__ == "__main__":
    main()
