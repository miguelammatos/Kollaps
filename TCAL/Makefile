OBJS= TCAL.o Destination.o TC.o utils.o

CXX=g++
CC=gcc
CXXFLAGS = -O3 -fPIC -c
CFLAGS = -O3 -fPIC -c
LDFLAGS=-shared 

all: cpp test

cpp: $(OBJS)
	$(CXX) $(OBJS) $(LDFLAGS) -o libTCAL.so 

test: test.c
	$(CC) test.c -o test -L ./ -lTCAL

#######################################
# 	CLEAN
#######################################
clean:
	-rm $(OBJS)
	-rm ./*.o	
	-rm *.so
