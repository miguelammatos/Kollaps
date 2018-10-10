//
// Created by joao on 1/21/18.
//
#include <unistd.h>
#include <stdlib.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
//#include <net/if.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <stdarg.h>

#include "tc_common.h"
#include "tc_core.h"
#include "tc_util.h"
#include "libnetlink.h"

#include "utils.h"
#include "Destination.h"
#include "TC.h"

int set_txqueuelen(const char* ifname, int num_packets) {

    struct ifreq ifr;
    int fd;
    int ret;

    if((fd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
        return -1;
    }

    ifr.ifr_addr.sa_family = AF_INET;
    strncpy(ifr.ifr_name, ifname, IFNAMSIZ);

    ifr.ifr_qlen = num_packets;

    ioctl(fd, SIOCSIFTXQLEN, &ifr);
    if(ret < 0) {
        perror("Error during SIOCSIFTXQLEN ioctl (set txqueuelen)");
        close(fd);
        return -1;
    }

    close(fd);
    return 0;
}


int set_if_flags(const char *ifname, short flags) {
    struct ifreq ifr;
    int res = 0;

    ifr.ifr_flags = flags;
    strncpy(ifr.ifr_name, ifname, IFNAMSIZ);

    int skfd;
    skfd = socket(AF_INET, SOCK_DGRAM, 0);

    res = ioctl(skfd, SIOCSIFFLAGS, &ifr);
    close(skfd);
    return res;
}

int set_if_up(const char *ifname, short flags) {
    return set_if_flags(ifname, flags | IFF_UP);
}

int set_if_down(const char *ifname, short flags) {
    return set_if_flags(ifname, flags & ~IFF_UP);
}

extern int (*usageCallback)(unsigned int, unsigned long);
extern Destination* hostsByHandle;
struct rtnl_handle rth;
int hz = 0;
double ticks_in_usec = 0;

int show_stats = 0;
int show_details = 0;
int show_raw = 0;
int show_graph = 0;
int timestamp = 0;

int batch_mode = 0;
int use_iec = 0;
int force = 0;
bool use_names = 0;
int json = 0;
int color = 0;
int oneline = 0;

struct rtnl_handle rth;

#define ARG(string){ argv[argc++]=string; }
#define ADD_DEV { ARG("add")ARG("dev")ARG(interface) }

extern struct qdisc_util prio_qdisc_util;
extern struct qdisc_util htb_qdisc_util;
extern struct qdisc_util netem_qdisc_util;
extern struct filter_util u32_filter_util;

#define QDISC_COUNT 3
#define FILTER_COUNT 1
static struct qdisc_util* qdisc_list[QDISC_COUNT] = {&prio_qdisc_util, &htb_qdisc_util, &netem_qdisc_util};
static struct filter_util* filter_list[FILTER_COUNT] = {&u32_filter_util};

#define MAX_INT_CHAR_LEN 10

struct qdisc_util *get_qdisc_kind(const char *str){
    for (int i=0; i<QDISC_COUNT; i++)
        if (strcmp(qdisc_list[i]->id, str) == 0)
            return qdisc_list[i];
        fprintf(stderr, "Qdisc %s not available!\n", str);
        exit(1);
        return NULL;
}

struct filter_util *get_filter_kind(const char *str){
    for (int i=0; i<FILTER_COUNT; i++)
        if (strcmp(filter_list[i]->id, str) == 0)
            return filter_list[i];
    fprintf(stderr, "Filter %s not available!\n", str);
    exit(1);
    return NULL;

}
#define PRINT { for(int i=0;i<argc;i++){printf("%s ", argv[i]);}printf("\n");}

void TC_init(char* interface, short controllPort) {
    int argc = 0;
    char* argv[512];

    char controllPort_buf[MAX_INT_CHAR_LEN];
    snprintf(controllPort_buf, MAX_INT_CHAR_LEN, "%hu", controllPort);

    tc_core_init();
    if (rtnl_open(&rth, 0) < 0) {
        fprintf(stderr, "Cannot open rtnetlink\n");
        exit(1);
    }


    /*VERY IMPORTANT docker sets txqueuelen to 0 on virtual interfaces
     * if we attach qdiscs to them, some will rely on txquelen and misbehave
     * this has been fixed in newer kernels, but older kernels dont automatically
     * restore the txqueuelen upon attaching a qdisc
     */
    set_txqueuelen(interface, TXQUEUELEN);

    //TODO: later
    //hz = get_hz();
    //ticks_in_usec = get_tick_in_usec();

    //Create the prio qdisc
    //This automatically creates 3 classes 1:1 1:2 and 1:3 with different priorities
    ADD_DEV ARG("root")ARG("handle")ARG("1:0")ARG("prio")
    PRINT
    do_qdisc(argc, argv);
    argc = 0;

    //Create the htb qdisc
    //Attach it to the lowest priority 1:3
    ADD_DEV ARG("parent")ARG("1:3")ARG("handle")ARG("4")ARG("htb")ARG("default")ARG("1")
    PRINT
    do_qdisc(argc, argv);
    argc = 0;

    //Create the filters
    //Create the first Hashtable e00:
    ADD_DEV
    ARG("parent")ARG("4:0")ARG("prio")ARG("2")ARG("handle")ARG("e00:")ARG("protocol")ARG("ip")
    ARG("u32")ARG("divisor")ARG("256")
    PRINT
    do_filter(argc, argv, NULL, 0);
    argc = 0;

    //The kernel apparently truncates the hashkey to a value <= divisor so we have to use only the last bits
    //Set up the hashtable to match the 3rd octect and link it to hashtable e00:
    ADD_DEV
    ARG("protocol")ARG("ip")ARG("parent")ARG("4:0")ARG("prio")ARG("2")
    ARG("u32")ARG("ht")ARG("800::")ARG("match")ARG("ip")ARG("dst")ARG("any")ARG("hashkey")ARG("mask")
    ARG(FIRST_HASH_MASK)ARG("at")ARG("16")ARG("link")ARG("e00:")
    PRINT
    do_filter(argc, argv, NULL, 0);
    argc = 0;

    //Setup a filter to allow traffic on the controll port to go unrestricted and with maximum priority
    //this filter has prio 1, and it sends to qdisc:class prio 1:1 (max priority)
    ADD_DEV
    ARG("parent")ARG("1:0")ARG("prio")ARG("1")ARG("protocol")ARG("ip")
    ARG("u32")ARG("match")ARG("ip")ARG("dport")ARG(controllPort_buf)ARG("0xffff")ARG("flowid")ARG("1:1")
    PRINT
    do_filter(argc, argv, NULL, 0);
    argc = 0;

    //Force all other traffic to be filtered through the htb filter
    //by pointing it to 1:3 (prio class 3, where htb 4: is)
    ADD_DEV
    ARG("parent")ARG("1:0")ARG("prio")ARG("2")ARG("protocol")ARG("ip")
    ARG("u32")ARG("match")ARG("ip")ARG("src")ARG("any")ARG("flowid")ARG("1:3")
    PRINT
    do_filter(argc, argv, NULL, 0);
    argc = 0;

}

void TC_initDestination(Destination *dest, char* interface) {
    /*std::stringstream args;
    std::stringstream handleStream;
    handleStream << std::hex << dest->handle;

    //Create the htb class for imposing the bandwidth limit
    args << "class add dev " << interface << " parent 4 classid 4:" << handleStream.str()
         << " htb rate " << dest->bandwidth << "Kbit ceil " << dest->bandwidth << "Kbit"
         << " quantum " << dest->bandwidth/(dest->bandwidth/10.0f);
    callTC(args.str());
    args.str(std::string());

    args.precision(6);
    args << "qdisc add dev " << interface << " parent 4:"<< handleStream.str() << " handle " << handleStream.str()
         << " netem delay " << dest->latency << "ms";
    if(dest->jitter > 0){
        args << " " << dest->jitter << "ms distribution normal";
    }
    if(dest->packetLossRate > 0.0f) {
        args << " loss random " << std::fixed << dest->packetLossRate;
    }
    callTC(args.str());


    char octet3[] = "00";
    char octet4[] = "00";
    destination_getOctetHex(dest, 3, octet3);
    destination_getOctetHex(dest, 4, octet4);
    char hexIp[] = "00000000";
    destination_getIpHex(dest, hexIp);

    //Check if second level hashtable exists
    args.str(std::string());
    args << "filter get dev " << interface << " parent 4:0 prio 2 handle f" <<  octet3 << ": protocol ip u32";
    if(callTC(args.str())){
        args.str(std::string());
        args << "filter add dev " << interface << " parent 4:0 prio 2 handle f" << octet3
             << ": protocol ip u32 divisor 256";
        callTC(args.str());

        args.str(std::string());
        args << "filter add dev " << interface << " parent 4:0 protocol ip prio 2 u32 ht e00:"
             << octet3 <<":0 match ip dst any hashkey mask " << SECOND_HASH_MASK
             << " at 16 link f" << octet3 << ":";
        callTC(args.str());
    }

    //Add the rule itself
    args.str(std::string());
    args << "filter add dev " << interface << " parent 4:0 protocol ip prio 2 u32 ht f"
         << octet3 << ":" << octet4 << " match u32 0x"
         << hexIp << " 0xffffffff at 16 flowid 4:" << handleStream.str();

        //<< dest->getOctetHex(3) << ":" << dest->getOctetHex(4) << " match ip dst "
        //  << dest->getIP() << "/32 flowid 4:" << handleStream.str();
    callTC(args.str());*/

}

void TC_destroy(char* interface) {
    rtnl_close(&rth);

    //TODO later
    set_if_down(interface, 0);

    //std::stringstream args;
    //args << "qdisc delete root dev " << interface;
    //callTC(args.str());

    //TODO later
    set_if_up(interface, 0);

}

void TC_updateUsage(char* interface) {
    return;
}


void TC_changeBandwidth(Destination *dest, char* interface) {
    return;
}
