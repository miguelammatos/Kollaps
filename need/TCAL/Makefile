OBJS= TCAL.o Destination.o TCAL_utils.o TC.o
LIBNETLINK=./libutc/lib/libnetlink.a
LIBUTIL=./libutc/lib/libutil.a
LIBUTC=./libutc/tc/libutc.a


CC=musl-gcc
#CC=gcc
CFLAGS = -O3 -fPIC -I./libutc/include -I ./libutc/ip/  -I./libutc/include/uapi -I./libutc/tc/
LDFLAGS= -shared -ldl -lm
LDLIBS = $(LIBUTC) $(LIBNETLINK) $(LIBUTIL)

all: libTCAL.so

libTCAL.so: $(OBJS)
	cd ./libutc && ./configure
	cd -
	make -C ./libutc
	$(CC) -o $@ -shared -static $(OBJS) $(LDLIBS) -lc
	objcopy --strip-all --keep-symbols=exported.sym $@ $@

test: test.c
	gcc -g -o $@ $^ -ldl


#######################################
# 	CLEAN
#######################################
clean:
	-rm $(OBJS)
	-rm ./*.o
	-rm ./*.a
	-rm ./test
	-make -C ./libutc distclean
