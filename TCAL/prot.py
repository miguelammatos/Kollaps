from pyTCAL import init, initDestination, queryUsage, updateUsage, changeBandwidth, tearDown
from time import sleep

init(8888)
initDestination("10.0.0.8", 50000, 200, 0, 0.0)

#initDestination("10.0.0.1", 100000, 25, 0.0)

changeBandwidth("10.0.0.8", 10000)

sleep(30)
#print("Changing to 30Mbps")
#changeBandwidth("10.0.0.8", 30000)
#sleep(30)

#for i in range(0, 10):
#    updateUsage()
#    sent_bytes = queryUsage("10.0.0.8")
#    bandwidth = 10000 + 10000*(i%10)
#    changeBandwidth("10.0.0.8",bandwidth)
#    print("10.0.0.8 : " + str(sent_bytes))
#    sleep(1)

tearDown()
