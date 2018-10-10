OBJS= TCAL.o Destination.o TC.o
LIBNETLINK=./libutc/lib/libnetlink.a
LIBUTIL=./libutc/lib/libutil.a
LIBUTC=./libutc/tc/libutc.a


CC=musl-gcc
#CC=gcc
CFLAGS = -g -fPIC -I./libutc/include -I./libutc/tc/
LDFLAGS= -shared -ldl -lm
LDLIBS = ./libutc.a $(LIBNETLINK) $(LIBUTIL)

TCALOBJS= libutc.a libTCAL.so test

all: $(TCALOBJS)

.PHONY: libutc.a
libutc.a: 
	cd ./libutc && ./configure
	cd -
	make -C ./libutc
	cp $(LIBUTC) $@
	#objcopy --localize-symbol=main --localize-symbol=get_qdisc_kind --localize-symbol=get_filter_kind $(LIBUTC) $@

libTCAL.so: $(OBJS)
	$(CC) -o $@ -shared -static $(OBJS) $(LDLIBS) -lc
test: test.c
	$(CC) -o $@ $^ -L. -lTCAL


#######################################
# 	CLEAN
#######################################
clean:
	-rm $(OBJS)
	-rm ./*.o
	-rm ./*.a
	-rm *.so
	-rm ./test
	#-make -C ./libutc distclean
