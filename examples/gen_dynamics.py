
############################################
# 
# this takes a .xml topology from NEED 1.0
# and creates the <dynamic> section
# required for NEED 1.1 and upward
# 
############################################

import re
import sys

top_file = sys.argv[1]


#pattern = r".(\w+)"
pattern = r'[<]service[ ]name[=]"([A-Za-z0-9]+)"'
pattern = r'"([A-Za-z0-9]+)"'

with open(top_file, 'r') as f:
	data = f.readlines()
	
data = [x.strip() for x in data] 

names = []

out = []
out.append('	<dynamic>')

for line in data:
	if line.startswith('<service name="n'):
		stripped = line.split('"')		
		out.append(f'		<schedule name="{stripped[1]}" time="0.0" action="join"/>')
		out.append(f'		<schedule name="{stripped[1]}" time="666.0" action="leave"/>')

out.append('	</dynamic>')

for line in out:
	print(line)

#with open("out.txt", 'w') as f:
	#for line in out:
		#f.write(line + "\n")
