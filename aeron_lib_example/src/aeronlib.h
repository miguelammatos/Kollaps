#ifndef __AERONLIB_H__
#define __AERONLIB_H__

//#include <cstdint>
//#include <cstdio>
//#include <signal.h>
//#include <thread>
//#include "Configuration.h"
//#include <Aeron.h>

// used only within the c++ lib
//fragment_handler_t printStringMessage();
//void printEndOfStream(Image &image);

void init(int stream_id, int processesCount, int *ids_list);
void registerCallback(void(*callback)(int a, int count, int* list));
void addFlow(int throughput, int linkCount, int* linkList);
void flush();
void shutdown();

// deprecated
void addStuff(int singleValue, int count, int* list);



#endif // __AERONLIB_H__
