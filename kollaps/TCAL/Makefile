OBJS= TCAL.o Destination.o TCAL_utils.o TC.o
LIBNETLINK=./libutc/lib/libnetlink.a
LIBUTIL=./libutc/lib/libutil.a
LIBUTC=./libutc/tc/libutc.a


CC=gcc
#CC=gcc
#We compile without optimizations because we have observed a bug even with -O2. In the function
#destination_create(), with -O2 or -O3, the compiled code assumes we are passing 3 ints and 2 floats,
#even though we of course pass 2 ints and 3 floats.
#LL based on comments + analysis by JN
CFLAGS = -O0 -fPIC -I./libutc/include -I ./libutc/ip/  -I./libutc/include/uapi -I./libutc/tc/
LDFLAGS= -shared -ldl -lm
LDLIBS = $(LIBUTC) $(LIBNETLINK) $(LIBUTIL)

all: libTCAL.so

.PHONY: libutc
libutc: 
	cd ./libutc && ./configure
	cd ..
	make -C ./libutc

libTCAL.so: libutc $(OBJS)
	$(CC) -o $@ -shared $(OBJS) $(LDLIBS) -lm
	#objcopy --strip-all --keep-symbols=exported.sym $@ $@

test: test.c
	gcc -g -o $@ $^ -ldl


#######################################
# 	CLEAN
#######################################
clean:
	-rm $(OBJS)
	-rm ./*.so
	-rm ./*.o
	-rm ./*.a
	-rm ./test
	-make -C ./libutc distclean
