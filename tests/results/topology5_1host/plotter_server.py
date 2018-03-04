import numpy
import Gnuplot
import re
from glob import glob

timestamp_re = re.compile(r"^\d+$")
throughput_re = re.compile(r"\[.*\]\s*(\d+)\.\d+-\d+\.\d+\s+sec\s+[0-9\.]+\s+\w+\s+([0-9\.]+)\s+(\w+)/sec\s+(\d+)\s+[0-9\.]+\s+\w+")
throughput_server_re = re.compile(r"^\[.*\]\s*(\d+)\.\d+-\d+\.\d+\s+sec\s+[0-9\.]+\s+\w+\s+([0-9\.]+)\s+(\w+)/sec\s*$")
throughput_server_udp_re = re.compile(r"^\[.*\]\s*(\d+)\.\d+-\d+\.\d+\s+sec\s+[0-9\.]+\s+\w+\s+([0-9\.]+)\s+(\w+)\/sec\s+[0-9\.]+\s+ms\s+\d+\/\d+\s+\(\d+\%\)\s+$")
Kbps_re = re.compile(r"^Kbits")
Mbps_re = re.compile(r"^Mbits")
bps_re = re.compile(r"^bits")
server_re = re.compile(r"^Server listening on 5201\s*$")
client_connection_re = re.compile(r"^\[\s+\d+\] local (\d+\.\d+\.\d+\.\d+).+5201\s*$")
server_connection_re = re.compile(r"^Accepted connection from (\d+\.\d+\.\d+\.\d+), port \d+\s*$")

def parse_iperf(client, server, udp):
    start_timestamp = 0
    Kbps = []
    lines = client.readlines()
    for line in lines:
        if timestamp_re.match(line):
            start_timestamp = int(line.strip())  # get the last timestamp

    lines = server.readlines()

    if udp:
        thput_re = throughput_server_udp_re
    else:
        thput_re = throughput_server_re

    for line in lines:
        if thput_re.match(line):
            matches = thput_re.findall(line)[0]
            if Kbps_re.match(matches[2]):
                multiplier = 1
            elif Mbps_re.match(matches[2]):
                multiplier = 1000
            elif bps_re.match(matches[2]):
                multiplier = 1.0/1000.0
            else:
                raise Exception("Throughput not in Kbps or Mbps or bps")
            Kbps.append((int(matches[0])+start_timestamp, float(matches[1])*multiplier))

    return Kbps

def tag_file(path):
    file = open(path)
    lines = file.readlines()
    server = False
    client = False
    ip = ""
    for line in lines:
        if server_re.match(line):
            server = True
        if timestamp_re.match(line):
            client = True
        if server_connection_re.match(line):
            ip = server_connection_re.findall(line)[0]
        if client_connection_re.match(line):
            ip = client_connection_re.findall(line)[0]
    file.close()

    if (not (client or server)) or not ip:
        return None

    return (server, ip, path)

def overlap(*d):
    lower_bound = 0
    upper_bound = d[0][-1][0]
    for dataset in d:
        if dataset[0][0] > lower_bound:
            lower_bound = dataset[0][0]
        if dataset[-1][0] < upper_bound:
            upper_bound = dataset[-1][0]


    for dataset in d:
        while True:
            if dataset[0][0] < lower_bound:
                dataset.pop(0)
            elif dataset[-1][0] > upper_bound:
                dataset.pop(-1)
            else:
                break

def trim(start, end, *d):
    for dataset in d:
        del dataset[:start]
        del dataset[-end:]

def pad(*d):
    lower_bound = d[0][-1][0]
    upper_bound = 0
    for dataset in d:
        if dataset[0][0] < lower_bound:
            lower_bound = dataset[0][0]
        if dataset[-1][0] > upper_bound:
            upper_bound = dataset[-1][0]


    for dataset in d:
        while True:
            if dataset[0][0] > lower_bound:
                dataset.insert(0,(dataset[0][0]-1, 0))
            elif dataset[-1][0] < upper_bound:
                dataset.append((dataset[-1][0]+1, 0))
            else:
                break


def main():

    ### CONFIGURATION #####
    #folder = "run6_server/"
    #folder = "run7_EWMA/"
    #folder = "run8/"
    folder = "run9_sync_buffers/"
    interesting_files = "*.log"
    udp = False
    #######################

    files = glob(folder+interesting_files)
    data_files = []
    for name in files:
        tag = tag_file(name)
        if tag is not None:
            data_files.append(tag)
    pairing = []
    for tag1 in data_files:
        for tag2 in data_files:
            if tag1[0] and not tag2[0]:  # tag1 is a server and tag2 is a client
                if tag1[1] == tag2[1]:  # ips match
                    pairing.append((tag1, tag2))

    data_sets = []
    for pairs in pairing:
        fs = open(pairs[0][2])
        fc = open(pairs[1][2])
        d = parse_iperf(fc, fs, udp)
        fs.close()
        fc.close()
        data_sets.append(d)

    print("Got " + str(len(data_sets)) + " data sets")

    #trim(0, 650, *data_sets)
    #pad(*data_sets)

    overlap(*data_sets)
    trim(60, 60, *data_sets)

    g = Gnuplot.Gnuplot()

    numpy_arrays = []
    gnuplot_data = []
    total = None
    for i, data in enumerate(data_sets):
        name = "Client"+str(i+1)
        c = numpy.array([x[1] for x in data])
        if total is None:
            total = c.copy()
        else:
            total += c
        numpy_arrays.append(c)
        gd = Gnuplot.Data(c, title=name, with_="lines")
        gnuplot_data.append(gd)

    numpy_arrays.append(total)
    gdsum = Gnuplot.Data(total, title="Total", with_="lines")
    gnuplot_data.append(gdsum)


    g.plot(*gnuplot_data)

    for i, gd in enumerate(gnuplot_data):
        print(gd.get_option("title"))
        print(" mean:     " + str(numpy_arrays[i].mean()))
        print(" max:      " + str(numpy_arrays[i].max()))
        print(" min:      " + str(numpy_arrays[i].min()))
        print(" dev:      " + str(numpy_arrays[i].std()))

if __name__ == '__main__':
    main()