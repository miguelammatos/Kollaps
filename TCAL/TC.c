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
//#include <net/if.h>


//To avoid warnings, declare these here:
struct sockaddr_nl;
struct nlmsghdr;
struct rtattr;

#include "tc_common.h"
#include "tc_core.h"
#include "tc_util.h"
#include "libnetlink.h"
#include "linux/pkt_sched.h"

#include "utils.h"
#include "Destination.h"
#include "TC.h"


extern void (*usageCallback)(unsigned int, unsigned long);
extern Destination* hostsByHandle;

struct rtnl_handle rth;  //handle used by calls to tc
struct rtnl_handle rth_persistent; //handle kept throughout emulation

int hz = 0;

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

#define ARG(string){ argv[argc++]=string; }
#define ADD_DEV { ARG("add")ARG("dev")ARG(interface) }
#define PARENT {ARG("parent")};
#define HTB_HANDLE {ARG("4:0")};
#define PROTOCOL_IP {ARG("protocol")ARG("ip")};
#define PRINT { for(int i=0;i<argc;i++){printf("%s ", argv[i]);}printf("\n");}

#define MIN(a, b) ((a) < (b) ? (a) : (b))

extern struct qdisc_util prio_qdisc_util;
extern struct qdisc_util htb_qdisc_util;
extern struct qdisc_util netem_qdisc_util;
extern struct filter_util u32_filter_util;

#define QDISC_COUNT 3
#define FILTER_COUNT 1
static struct qdisc_util* qdisc_list[QDISC_COUNT] = {&prio_qdisc_util, &htb_qdisc_util, &netem_qdisc_util};
static struct filter_util* filter_list[FILTER_COUNT] = {&u32_filter_util};

#define MAX_INT_CHAR_LEN 10

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

static void open_rtnl(){
    if (rtnl_open(&rth, 0) < 0) {
        fprintf(stderr, "Cannot open rtnetlink\n");
        exit(1);
    }
}
static void close_rtnl(){
    rtnl_close(&rth);
}


void TC_init(char* interface, short controllPort) {
    int argc = 0;
    char* argv[100];

    char controllPort_buf[MAX_INT_CHAR_LEN];
    snprintf(controllPort_buf, MAX_INT_CHAR_LEN, "%hu", controllPort);

    tc_core_init();
    if (rtnl_open(&rth_persistent, 0) < 0) {
        fprintf(stderr, "Cannot open rtnetlink\n");
        exit(1);
    }


    /*VERY IMPORTANT docker sets txqueuelen to 0 on virtual interfaces
     * if we attach qdiscs to them, some will rely on txquelen and misbehave
     * this has been fixed in newer kernels, but older kernels dont automatically
     * restore the txqueuelen upon attaching a qdisc
     */
    set_txqueuelen(interface, TXQUEUELEN);

    hz = get_hz();

    //Create the prio qdisc
    //This automatically creates 3 classes 1:1 1:2 and 1:3 with different priorities
    ADD_DEV ARG("root")ARG("handle")ARG("1:0")ARG("prio")
    PRINT
    open_rtnl();
    do_qdisc(argc, argv);
    close_rtnl();
    argc = 0;

    //Create the htb qdisc
    //Attach it to the lowest priority 1:3
    ADD_DEV ARG("parent")ARG("1:3")ARG("handle") HTB_HANDLE ARG("htb")ARG("default")ARG("1")
    PRINT
    open_rtnl();
    do_qdisc(argc, argv);
    close_rtnl();
    argc = 0;

    //Create the filters
    //Create the first Hashtable e00:
    ADD_DEV
    ARG("parent") HTB_HANDLE ARG("prio")ARG("2")ARG("handle")ARG("e00:") PROTOCOL_IP
    ARG("u32")ARG("divisor")ARG("256")
    PRINT
    open_rtnl();
    do_filter(argc, argv, NULL, 0);
    close_rtnl();
    argc = 0;

    //The kernel apparently truncates the hashkey to a value <= divisor so we have to use only the last bits
    //Set up the hashtable to match the 3rd octect and link it to hashtable e00:
    ADD_DEV
    PROTOCOL_IP PARENT HTB_HANDLE ARG("prio")ARG("2")
    ARG("u32")ARG("ht")ARG("800::")ARG("match")ARG("ip")ARG("dst")ARG("any")ARG("hashkey")ARG("mask")
    ARG(FIRST_HASH_MASK)ARG("at")ARG("16")ARG("link")ARG("e00:")
    PRINT
    open_rtnl();
    do_filter(argc, argv, NULL, 0);
    close_rtnl();
    argc = 0;

    //Setup a filter to allow traffic on the controll port to go unrestricted and with maximum priority
    //this filter has prio 1, and it sends to qdisc:class prio 1:1 (max priority)
    ADD_DEV
    PARENT ARG("1:0")ARG("prio")ARG("1") PROTOCOL_IP
    ARG("u32")ARG("match")ARG("ip")ARG("dport")ARG(controllPort_buf)ARG("0xffff")ARG("flowid")ARG("1:1")
    PRINT
    open_rtnl();
    do_filter(argc, argv, NULL, 0);
    close_rtnl();
    argc = 0;

    //Force all other traffic to be filtered through the htb filter
    //by pointing it to 1:3 (prio class 3, where htb 4: is)
    ADD_DEV
    PARENT ARG("1:0")ARG("prio")ARG("2") PROTOCOL_IP
    ARG("u32")ARG("match")ARG("ip")ARG("src")ARG("any")ARG("flowid")ARG("1:3")
    PRINT
    open_rtnl();
    do_filter(argc, argv, NULL, 0);
    close_rtnl();
    argc = 0;

}

void TC_initDestination(Destination *dest, char* interface) {
    int argc = 0;
    char* argv[100];

    char htb_class_handle[MAX_INT_CHAR_LEN+2];
    char netem_qdisc_handle[MAX_INT_CHAR_LEN];
    snprintf(htb_class_handle, MAX_INT_CHAR_LEN+2, "4:%x", dest->handle);
    snprintf(netem_qdisc_handle, MAX_INT_CHAR_LEN, "%x", dest->handle);

    char bandwidth[MAX_INT_CHAR_LEN+4];
    snprintf(bandwidth, MAX_INT_CHAR_LEN+4, "%uKbit", dest->bandwidth);

    char latency[MAX_INT_CHAR_LEN+2];
    snprintf(latency, MAX_INT_CHAR_LEN+2, "%ums", dest->latency);

    float q = dest->bandwidth/(dest->bandwidth/10.0f);
    size_t size = snprintf(NULL, 0, "%f", q);
    char *quantum = (char*)malloc(sizeof(char)*(size+1));
    snprintf(quantum, size+1, "%d", (int)q);


    //Create the htb class for imposing the bandwidth limit
    ADD_DEV
    PARENT HTB_HANDLE ARG("classid")ARG(htb_class_handle)
    ARG("htb")ARG("rate")ARG(bandwidth)ARG("ceil")ARG(bandwidth)
    ARG("quantum")ARG(quantum)
    PRINT
    open_rtnl();
    do_class(argc, argv);
    close_rtnl();
    argc = 0;
    free(quantum);


    char* loss = NULL;
    char* jitter = NULL;
    //Create the netem qdisc for emulating latency and attach it to the previous htb class
    ADD_DEV
    PARENT ARG(htb_class_handle)ARG("handle")ARG(netem_qdisc_handle)
    ARG("netem")ARG("delay")ARG(latency)
    if(dest->jitter > 0){
        //TODO we have to generate the normal table ourselves and change the qdisc to include it!
        size = snprintf(NULL, 0, "%0.6fms", dest->jitter);
        jitter = (char*)malloc(sizeof(char)*(size+1));
        snprintf(jitter, size+1, "%0.6fms", dest->jitter);
        ARG(jitter)ARG("distribution")ARG("normal")
    }
    if(dest->packetLossRate > 0.0f) {
        size = snprintf(NULL, 0, "%0.6f", dest->packetLossRate);
        loss = (char*)malloc(sizeof(char)*(size+1));
        snprintf(loss, size+1, "%0.6f", dest->packetLossRate);
        ARG("loss")ARG("random")ARG(loss)
    }
    PRINT
    open_rtnl();
    do_qdisc(argc, argv);
    close_rtnl();
    if(loss)
        free(loss);
    if(jitter)
        free(jitter);
    argc = 0;


    char octet3[] = "00";
    char octet4[] = "00";
    char first_ht_handle[] = "e00:00:0";
    char second_ht_handle[] = "f00:";
    char final_ht_handle[] = "f00:00";
    destination_getOctetHex(dest, 3, octet3);
    destination_getOctetHex(dest, 4, octet4);
    char hexIp[] = "0x00000000";
    destination_getIpHex(dest, hexIp);
    snprintf(first_ht_handle, 9, "e00:%s:0", octet3);
    snprintf(second_ht_handle, 5, "f%s:", octet3);
    snprintf(final_ht_handle, 7, "f%s:%s", octet3, octet4);


    //Check if second level hashtable exists
    ARG("get")ARG("dev")ARG(interface)PARENT HTB_HANDLE ARG("prio")ARG("2")
    ARG("handle")ARG(second_ht_handle)PROTOCOL_IP ARG("u32")
    PRINT
    open_rtnl();
    int status = (do_filter(argc, argv, NULL, 0));
    close_rtnl();
    argc = 0;

    if(status) {

        ADD_DEV PARENT HTB_HANDLE ARG("prio") ARG("2") ARG("handle") ARG(second_ht_handle)PROTOCOL_IP
        ARG("u32") ARG("divisor") ARG("256")
        PRINT
        open_rtnl();
        do_filter(argc, argv, NULL, 0);
        close_rtnl();
        argc = 0;

        ADD_DEV PARENT HTB_HANDLE PROTOCOL_IP ARG("prio") ARG("2")
        ARG("u32") ARG("ht") ARG(first_ht_handle) ARG("match") ARG("ip") ARG("dst") ARG("any") ARG("hashkey")
        ARG("mask")ARG(SECOND_HASH_MASK)ARG("at")ARG("16")ARG("link")ARG(second_ht_handle)
        PRINT
        open_rtnl();
        do_filter(argc, argv, NULL, 0);
        close_rtnl();
        argc = 0;
    }

    //Add the rule itself
    ADD_DEV
    PARENT HTB_HANDLE PROTOCOL_IP ARG("prio")ARG("2")ARG("u32")ARG("ht")ARG(final_ht_handle)
    ARG("match")ARG("u32")ARG(hexIp)ARG("0xffffffff")ARG("at")ARG("16")ARG("flowid")ARG(htb_class_handle)
    PRINT
    open_rtnl();
    do_filter(argc, argv, NULL, 0);
    close_rtnl();
    argc = 0;

}

void TC_destroy(char* interface) {
    rtnl_close(&rth_persistent);

    set_if_down(interface, 0);

    char* argv[10];
    int argc = 0;
    ARG("delete")ARG("root")ARG("dev")ARG(interface);
    open_rtnl();
    do_qdisc(argc, argv);
    close_rtnl();

    set_if_up(interface, 0);

}

int update_class(const struct sockaddr_nl *who,
                 struct nlmsghdr *n, void *arg) {
    /* This is a callback that acts as a filter,
     * selecting only the classes we are interested in*/

    struct tcmsg* t = (struct tcmsg*)NLMSG_DATA(n);
    int len = n->nlmsg_len;
    struct rtattr *tb[TCA_MAX + 1];

    if (n->nlmsg_type != RTM_NEWTCLASS && n->nlmsg_type != RTM_DELTCLASS) {
        //"Not a class\n"
        return 0;
    }
    len -= NLMSG_LENGTH(sizeof(*t));
    if (len < 0) {
        //Wrong len ;
        return -1;
    }

    if(!t->tcm_handle)
        return 1;

    parse_rtattr(tb, TCA_MAX, TCA_RTA(t), len);

    if (!tb[TCA_KIND])
        return -1;

    if (n->nlmsg_type == RTM_DELTCLASS) //if class is deleted
        return -1;

    if (tb[TCA_STATS]) {
        struct tc_stats st = {};
        memcpy(&st, RTA_DATA(tb[TCA_STATS]), MIN(RTA_PAYLOAD(tb[TCA_STATS]), sizeof(st)));
        unsigned int handle = TC_H_MIN(t->tcm_handle);

        Destination *d;
        HASH_FIND(hh_h, hostsByHandle, &handle, sizeof(int), d);
        if(d->usage != st.bytes) {
            d->usage = st.bytes;
            if(usageCallback)
                usageCallback(d->ipv4, st.bytes);
        }
    }
    return 0;
}

void TC_updateUsage(char* interface) {
    /*Use rtnetlink to communicate with the kernel directly
     * this should be a lot more efficient than calling tc
     * altough the API is not very well documented
     */

    struct tcmsg t = { .tcm_family = AF_UNSPEC };
    t.tcm_parent = (4<<16);  //We are only interested in classes from qdisc 4 (the htb root)
    t.tcm_ifindex = ll_name_to_index(interface);
    if (rtnl_dump_request(&rth_persistent, RTM_GETTCLASS, &t, sizeof(t)) < 0) {
        printf("Cannot send tc dump request\n");
        return;
    }
    if (rtnl_dump_filter(&rth_persistent, update_class, NULL) < 0) {
        printf("Cannot obtain tc dump\n");
        return;
    }
}


void TC_changeBandwidth(Destination *dest, char* interface) {
    /*Use rtnetlink to communicate with the kernel directly
     * this should be a more efficient than calling tc
     * altough the API is not very well documented
     */
    struct {
        struct nlmsghdr	n;
        struct tcmsg t;
        char buf[4096];
    } req = {};

    req.n.nlmsg_len = NLMSG_LENGTH(sizeof(struct tcmsg)),
    req.n.nlmsg_flags = NLM_F_REQUEST,
    req.n.nlmsg_type = RTM_NEWTCLASS,
    req.t.tcm_family = AF_UNSPEC,
    req.t.tcm_ifindex = ll_name_to_index(interface);

    unsigned int handle = (4 << 16) | dest->handle;
    req.t.tcm_handle = handle;

    struct rtattr *tail = NLMSG_TAIL(&req.n);
    addattr_l(&req.n, 1024, TCA_OPTIONS, NULL, 0);


    __u64 rate64, ceil64; //Should be bytes per second

    unsigned long bandwidth = (unsigned long)dest->bandwidth;
    rate64 = (bandwidth*1000)/8; //Need to convert from Kbps to Bytes per second
    ceil64 = rate64;

    if (rate64 >= (1ULL << 32))
        addattr_l(&req.n, 1124, TCA_HTB_RATE64, &rate64, sizeof(rate64));

    if (ceil64 >= (1ULL << 32))
        addattr_l(&req.n, 1224, TCA_HTB_CEIL64, &ceil64, sizeof(ceil64));

    struct tc_htb_opt opt = {};

    //For some reason we also need to fill this 32bit field even though we took care of it above with 64bits...
    opt.rate.rate = (__u32)((rate64 >= (1ULL << 32)) ? ~0U : rate64);
    opt.ceil.rate = (__u32)((ceil64 >= (1ULL << 32)) ? ~0U : ceil64);

    /* compute minimal allowed burst from rate; mtu is added here to make
       sute that buffer is larger than mtu and to have some safeguard space */
    unsigned int mtu = 1600; /* eth packet len */
    unsigned long buffer = rate64 / hz + mtu;
    unsigned long cbuffer = ceil64 / hz + mtu;

    opt.ceil.overhead = 0;
    opt.rate.overhead = 0;
    opt.ceil.mpu = 0;
    opt.rate.mpu = 0;

    __u32 rtab[256], ctab[256];
    int cell_log =  -1, ccell_log = -1;
    if (tc_calc_rtable(&opt.rate, rtab, cell_log, mtu, LINKLAYER_ETHERNET) < 0) {
        printf("htb: failed to calculate rate table.\n");
        return;
    }
    //opt.buffer = (__u32)((TIME_UNITS_PER_SEC*((double)buffer/(double)rate64))*ticks_in_usec);
    opt.buffer = tc_calc_xmittime(rate64, buffer);

    if (tc_calc_rtable(&opt.ceil, ctab, ccell_log, mtu, LINKLAYER_ETHERNET) < 0) {
        printf("htb: failed to calculate ceil rate table.\n");
        return;
    }
    //opt.cbuffer = (__u32)((TIME_UNITS_PER_SEC*((double)cbuffer/(double)ceil64))*ticks_in_usec);
    opt.cbuffer = tc_calc_xmittime(ceil64, cbuffer);

    opt.quantum = (__u32)(ceil64/(ceil64/10));

    addattr_l(&req.n, 2024, TCA_HTB_PARMS, &opt, sizeof(opt));
    addattr_l(&req.n, 3024, TCA_HTB_RTAB, rtab, 1024);
    addattr_l(&req.n, 4024, TCA_HTB_CTAB, ctab, 1024);
    tail->rta_len = (unsigned short) ((char*)NLMSG_TAIL(&req.n) - (char*)tail);

    if (rtnl_talk(&rth_persistent, &req.n, NULL) < 0)
        printf("failed to comunicate with tc\n");
    return;
}
