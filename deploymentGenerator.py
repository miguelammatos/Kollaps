import sys

from NetGraph import NetGraph





def main():
   topology_file = sys.argv[1]
   graph = NetGraph()

   parseXML(topology_file, graph)

if __name__ == '__main__':
    main()