OBJS= TCAL.o Destination.o TC.o utils.o

PYTHON_WRAPPER=TCAL_python_wrap.o

CXX=g++
CC=gcc
CXXFLAGS = -O3 -fPIC -c
CFLAGS = -O3 -fPIC -c
PYTHON_CXXFLAGS = $(shell pkg-config --cflags python3) 
LDFLAGS=-shared 
PYTHON_LDFLAGS = $(shell pkg-config --libs python3) 

all: cpp python

cpp: $(OBJS)
	$(CXX) $(OBJS) $(LDFLAGS) -o TCAL.so 
#######################################
# 	PYTHON
#######################################
swig:
	swig -c++ -python -o TCAL_python_wrap.cxx pyTCAL.i
	
python: $(OBJS) $(PYTHON_WRAPPER)
	$(CXX) $(OBJS) $(LOW_OBJS) $(PYTHON_WRAPPER) $(LDFLAGS) -o _pyTCAL.so 

TCAL_python_wrap.o : TCAL_python_wrap.cxx
	$(CXX) $(CXXFLAGS) $(PYTHON_CXXFLAGS) $^ -o $@ $(PYTHON_LDFLAGS)

#######################################
# 	CLEAN
#######################################
clean:
	-rm $(OBJS)
	-rm ./*.o	
	-rm TCAL_python_wrap.cxx
	-rm pyTCAL.py 
	-rm *.so
