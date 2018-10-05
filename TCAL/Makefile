OBJS= TCAL.o Destination.o TC.o utils.o

CXX=g++
CC=gcc
CXXFLAGS = -O3 -fPIC -c
CFLAGS = -O3 -fPIC -c
LDFLAGS=-shared 

all: cpp

cpp: $(OBJS)
	$(CXX) $(OBJS) $(LDFLAGS) -o TCAL.so 

#######################################
# 	CLEAN
#######################################
clean:
	-rm $(OBJS)
	-rm ./*.o	
	-rm *.so
