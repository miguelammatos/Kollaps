//
// Created by joao on 1/21/18.
//
#include <unistd.h>
#include <stdlib.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <stdarg.h>
#include <ctype.h>
#include <math.h>


#include "TC.h"
#include "tc_common.h"
#include "tc_core.h"
#include "tc_util.h"
#include "libnetlink.h"
#include "linux/pkt_sched.h"
#include "utils.h"
#include "TCAL_utils.h"

#include "Destination.h"


extern void (*usageCallback)(unsigned int, unsigned long, unsigned int);
extern Destination* hostsByHandle;


int txqueuelen = 0; //This is set by init

struct rtnl_handle rth;  //handle used by initialization calls to tc
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
#define ADD_DEV { ARG("add")ARG("dev")ARG(netiface) }
#define PARENT {ARG("parent")};
#define HTB_HANDLE {ARG("4:0")};
#define PROTOCOL_IP {ARG("protocol")ARG("ip")};
#define PRINT { for(int i=0;i<argc;i++){printf("%s ", argv[i]);}printf("\n");}

#define NEED__MIN(a, b) ((a) < (b) ? (a) : (b))


#define MAX_INT_CHAR_LEN 10


unsigned short freePort = 0;

void TC_init(unsigned short controllPort, int txqlen) {
    freePort = controllPort;
    tc_core_init();
    open_rtnl(&rth_persistent);
    hz = get_hz();
    txqueuelen = txqlen;
}

void init_interface(unsigned int if_index){

    int argc = 0;
    char* argv[100];
    char* netiface;

    char controllPort_buf[MAX_INT_CHAR_LEN];
    snprintf(controllPort_buf, MAX_INT_CHAR_LEN, "%hu", freePort);

    netiface = strdup(ll_index_to_name(if_index));

    /*VERY IMPORTANT docker sets txqueuelen to 0 on virtual interfaces
     * if we attach qdiscs to them, some will rely on txquelen and misbehave
     * this has been fixed in newer kernels, but older kernels dont automatically
     * restore the txqueuelen upon attaching a qdisc
     */


    set_txqueuelen(netiface, txqueuelen);


    //Create the prio qdisc
    //This automatically creates 3 classes 1:1 1:2 and 1:3 with different priorities
    ADD_DEV ARG("root")ARG("handle")ARG("1:0")ARG("prio")
    PRINT
    open_rtnl(&rth);
    do_qdisc(argc, argv);
    close_rtnl(&rth);
    argc = 0;

    //Create the htb qdisc
    //Attach it to the lowest priority 1:3
    ADD_DEV ARG("parent")ARG("1:3")ARG("handle") HTB_HANDLE ARG("htb")ARG("default")ARG("1")
    PRINT
    open_rtnl(&rth);
    do_qdisc(argc, argv);
    close_rtnl(&rth);
    argc = 0;

    //Create the filters
    //Create the first Hashtable e00:
    ADD_DEV
    ARG("parent") HTB_HANDLE ARG("prio")ARG("2")ARG("handle")ARG("e00:") PROTOCOL_IP
    ARG("u32")ARG("divisor")ARG("256")
    PRINT
    open_rtnl(&rth);
    do_filter(argc, argv, NULL, 0);
    close_rtnl(&rth);
    argc = 0;

    //The kernel apparently truncates the hashkey to a value <= divisor so we have to use only the last bits
    //Set up the hashtable to match the 3rd octect and link it to hashtable e00:
    ADD_DEV
    PROTOCOL_IP PARENT HTB_HANDLE ARG("prio")ARG("2")
    ARG("u32")ARG("ht")ARG("800::")ARG("match")ARG("ip")ARG("dst")ARG("any")ARG("hashkey")ARG("mask")
    ARG(FIRST_HASH_MASK)ARG("at")ARG("16")ARG("link")ARG("e00:")
    PRINT
    open_rtnl(&rth);
    do_filter(argc, argv, NULL, 0);
    close_rtnl(&rth);
    argc = 0;

    //Setup a filter to allow traffic on the controll port to go unrestricted and with maximum priority
    //this filter has prio 1, and it sends to qdisc:class prio 1:1 (max priority)
    ADD_DEV
    PARENT ARG("1:0")ARG("prio")ARG("1") PROTOCOL_IP
    ARG("u32")ARG("match")ARG("ip")ARG("dport")ARG(controllPort_buf)ARG("0xffff")ARG("flowid")ARG("1:1")
    PRINT
    open_rtnl(&rth);
    do_filter(argc, argv, NULL, 0);
    close_rtnl(&rth);
    argc = 0;

    //Force all other traffic to be filtered through the htb filter
    //by pointing it to 1:3 (prio class 3, where htb 4: is)
    ADD_DEV
    PARENT ARG("1:0")ARG("prio")ARG("2") PROTOCOL_IP
    ARG("u32")ARG("match")ARG("ip")ARG("src")ARG("any")ARG("flowid")ARG("1:3")
    PRINT
    open_rtnl(&rth);
    do_filter(argc, argv, NULL, 0);
    close_rtnl(&rth);
    argc = 0;

    free(netiface);
}


void TC_initDestination(Destination *dest) {
    int argc = 0;
    char* argv[100];
    char* netiface;

    open_rtnl(&rth);
    unsigned int if_index = get_route_interface(dest->ipv4);
    close_rtnl(&rth);
    dest->if_index = if_index;

    netiface = strdup(ll_index_to_name(dest->if_index));

    //Check if this interface has been initialized
    ARG("get")ARG("dev")ARG(netiface)PARENT ARG("1:0")ARG("prio")ARG("1")
    ARG("handle")ARG("800:")PROTOCOL_IP ARG("u32")
    PRINT
    open_rtnl(&rth);
    int status = (do_filter(argc, argv, NULL, 0));
    close_rtnl(&rth);
    argc = 0;
    if(status) {
        init_interface(if_index);
    }

    char htb_class_handle[MAX_INT_CHAR_LEN+2];
    char netem_qdisc_handle[MAX_INT_CHAR_LEN];
    snprintf(htb_class_handle, MAX_INT_CHAR_LEN+2, "4:%x", dest->handle);
    snprintf(netem_qdisc_handle, MAX_INT_CHAR_LEN, "%x", dest->handle);

    char bandwidth[MAX_INT_CHAR_LEN+4];
    snprintf(bandwidth, MAX_INT_CHAR_LEN+4, "%uKbit", dest->bandwidth);

    char latency[MAX_INT_CHAR_LEN+2];
    snprintf(latency, MAX_INT_CHAR_LEN+2, "%ums", dest->latency);

    char txqlen[MAX_INT_CHAR_LEN];
    snprintf(txqlen, MAX_INT_CHAR_LEN, "%u", txqueuelen);

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
    open_rtnl(&rth);
    do_class(argc, argv);
    close_rtnl(&rth);
    argc = 0;
    free(quantum);


    char* loss = NULL;
    char* jitter = NULL;
    //Create the netem qdisc for emulating latency and attach it to the previous htb class
    //Warning, if we use new netem features, double check that TC_changePacketLoss() still works (might need changes)
    ADD_DEV
    PARENT ARG(htb_class_handle)ARG("handle")ARG(netem_qdisc_handle)
    ARG("netem")ARG("limit")ARG(txqlen)ARG("delay")ARG(latency)
    if(dest->jitter > 0){
        size = snprintf(NULL, 0, "%0.6fms", dest->jitter);
        jitter = (char*)malloc(sizeof(char)*(size+1));
        snprintf(jitter, size+1, "%0.6fms", dest->jitter);
        ARG(jitter)ARG("distribution")ARG("normal")
    }
    if(dest->packetLossRate > 0.0f) {
        size = snprintf(NULL, 0, "%0.6f%%", dest->packetLossRate*100);
        loss = (char*)malloc(sizeof(char)*(size+1));
        snprintf(loss, size+1, "%0.6f%%", dest->packetLossRate*100);
        ARG("loss")ARG("random")ARG(loss)
        /*char p[] = "0.00001%";
        char r[] = "0.00001%";
        ARG("loss")ARG("gemodel")ARG(p)ARG(r)
         FOR FUTURE REFERENCE (regarding NEED):
         If you want to get loss behaviour like real-world buffers filling,
         than Gilbert model is not enough, it has to be coordinated with bw throttling.
         TCP reacts to loss by reducing throughput, but it will always try to be on the edge of packet loss
         if there is no loss, it will rapidly scale up again, simply using p and r will result in a lot of variation
         but fluctuations will be very fast, (and not over long periods of time like in real life)*/
    }
    PRINT
    open_rtnl(&rth);
    do_qdisc(argc, argv);
    close_rtnl(&rth);
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
    ARG("get")ARG("dev")ARG(netiface)PARENT HTB_HANDLE ARG("prio")ARG("2")
    ARG("handle")ARG(second_ht_handle)PROTOCOL_IP ARG("u32")
    PRINT
    open_rtnl(&rth);
    status = (do_filter(argc, argv, NULL, 0));
    close_rtnl(&rth);
    argc = 0;

    if(status) {

        ADD_DEV PARENT HTB_HANDLE ARG("prio") ARG("2") ARG("handle") ARG(second_ht_handle)PROTOCOL_IP
        ARG("u32") ARG("divisor") ARG("256")
        PRINT
        open_rtnl(&rth);
        do_filter(argc, argv, NULL, 0);
        close_rtnl(&rth);
        argc = 0;

        ADD_DEV PARENT HTB_HANDLE PROTOCOL_IP ARG("prio") ARG("2")
        ARG("u32") ARG("ht") ARG(first_ht_handle) ARG("match") ARG("ip") ARG("dst") ARG("any") ARG("hashkey")
        ARG("mask")ARG(SECOND_HASH_MASK)ARG("at")ARG("16")ARG("link")ARG(second_ht_handle)
        PRINT
        open_rtnl(&rth);
        do_filter(argc, argv, NULL, 0);
        close_rtnl(&rth);
        argc = 0;
    }

    //Add the rule itself
    ADD_DEV
    PARENT HTB_HANDLE PROTOCOL_IP ARG("prio")ARG("2")ARG("u32")ARG("ht")ARG(final_ht_handle)
    ARG("match")ARG("u32")ARG(hexIp)ARG("0xffffffff")ARG("at")ARG("16")ARG("flowid")ARG(htb_class_handle)
    PRINT
    open_rtnl(&rth);
    do_filter(argc, argv, NULL, 0);
    close_rtnl(&rth);
    argc = 0;
    free(netiface);

}

void TC_destroy(unsigned int if_index, int disableNetwork) {
    char* netiface;
    rtnl_close(&rth_persistent);

    netiface = strdup(ll_index_to_name(if_index));

    set_if_down(netiface, 0);

    char* argv[10];
    int argc = 0;
    ARG("delete")ARG("root")ARG("dev")ARG(netiface);
    open_rtnl(&rth);
    do_qdisc(argc, argv);
    close_rtnl(&rth);

    if(!disableNetwork) {
        sleep(1); //This is necessary on fast machines, otherwise the interface stays down (maybe do a loop and check?)
        set_if_up(netiface, 0);
    }
    free(netiface);

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
        memcpy(&st, RTA_DATA(tb[TCA_STATS]), NEED__MIN(RTA_PAYLOAD(tb[TCA_STATS]), sizeof(st)));
        unsigned int handle = TC_H_MIN(t->tcm_handle);

        Destination *d;
        HASH_FIND(hh_h, hostsByHandle, &handle, sizeof(int), d);
        if(d->usage != st.bytes || d->queuelen != st.qlen) {
            d->usage = st.bytes;
            d->queuelen = st.qlen;
            if(usageCallback)
                usageCallback(d->ipv4, st.bytes, st.qlen);
        }
    }
    return 0;
}

void TC_updateUsage(unsigned int if_index) {
    /*Use rtnetlink to communicate with the kernel directly
     * this should be a lot more efficient than calling tc
     * altough the API is not very well documented
     */

    struct tcmsg t = { .tcm_family = AF_UNSPEC };
    t.tcm_parent = (4<<16);  //We are only interested in classes from qdisc 4 (the htb root)
    t.tcm_ifindex = if_index;
    if (rtnl_dump_request(&rth_persistent, RTM_GETTCLASS, &t, sizeof(t)) < 0) {
        printf("Cannot send tc dump request\n");
        return;
    }
    if (rtnl_dump_filter(&rth_persistent, update_class, NULL) < 0) {
        printf("Cannot obtain tc dump\n");
        return;
    }
}

void TC_changeBandwidth(Destination *dest) {
    /*Use rtnetlink to communicate with the kernel directly
     * this should be more efficient than calling tc
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
    req.t.tcm_ifindex = dest->if_index;

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
       sure that buffer is larger than mtu and to have some safeguard space */
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

void TC_changeNetem(Destination *dest){
    struct {
        struct nlmsghdr	n;
        struct tcmsg t;
        char buf[4096];
    } req = {};

    req.n.nlmsg_len = NLMSG_LENGTH(sizeof(struct tcmsg)),
    req.n.nlmsg_flags = NLM_F_REQUEST,
    req.n.nlmsg_type = RTM_NEWQDISC,
    req.t.tcm_family = AF_UNSPEC,
    req.t.tcm_ifindex = dest->if_index;

    unsigned int parent_handle = (4 << 16) | dest->handle;
    req.t.tcm_parent = parent_handle;
    req.t.tcm_handle = dest->handle << 16;

    struct rtattr *tail = NLMSG_TAIL(&req.n);

    struct tc_netem_qopt opt = { .limit = txqueuelen };
    opt.loss = rint(dest->packetLossRate * UINT32_MAX);
    //Since we are updating the opt structure, we have to fill in latency and jitter as well
    // (distribution is not necessary however)
    opt.latency = tc_core_time2tick(dest->latency*(TIME_UNITS_PER_SEC/1000));
    opt.jitter = tc_core_time2tick(dest->jitter*(TIME_UNITS_PER_SEC/1000));

    if (addattr_l(&req.n, 1024, TCA_OPTIONS, &opt, sizeof(opt)) < 0)
        return;

    tail->rta_len = (void *) NLMSG_TAIL(&req.n) - (void *) tail;

    if (rtnl_talk(&rth_persistent, &req.n, NULL) < 0)
        printf("failed to comunicate with tc\n");
    return;
}
