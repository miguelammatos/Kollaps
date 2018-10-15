//
// Created by joao on 10/12/18.
//
#include <unistd.h>
#include <stdlib.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <stdarg.h>
#include <ctype.h>
#include <math.h>

//To avoid warnings, declare these here:
struct sockaddr_nl;
struct nlmsghdr;
struct rtattr;
struct qdisc_util;

#include "tc_common.h"
#include "tc_core.h"
#include "tc_util.h"
#include "libnetlink.h"
#include "linux/pkt_sched.h"
#include "utils.h"
#include "TCAL_utils.h"


//Get the pointers to the tc parsing functions
extern struct qdisc_util prio_qdisc_util;
extern struct qdisc_util htb_qdisc_util;
extern struct filter_util u32_filter_util;
//Netem is special, we override it and use our own
struct qdisc_util netem_qdisc_costum_util = {
        .id		= "netem",
        .parse_qopt	= netem_parse_costum_opt,
        .print_qopt	= NULL,
};
#define QDISC_COUNT 3
#define FILTER_COUNT 1
static struct qdisc_util* qdisc_list[QDISC_COUNT] = {&prio_qdisc_util, &htb_qdisc_util, &netem_qdisc_costum_util};
static struct filter_util* filter_list[FILTER_COUNT] = {&u32_filter_util};

//These functions return the correct function for parsing tc options
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

//These functions are for setting interface properties
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


//Wrappers for oppensing and closing
void open_rtnl(struct rtnl_handle* h){
    if (rtnl_open(h, 0) < 0) {
        fprintf(stderr, "Cannot open rtnetlink\n");
        exit(1);
    }
}
void close_rtnl(struct rtnl_handle* h){
    rtnl_close(h);
}

__s16 normalDistribution[NORMAL_SIZE];
void fillNormalDist(){
    int i, n;
    int value;
    double x;

    __s16 *table;

    table = (__s16 *)calloc(MAX_DIST+1, sizeof(__s16));

    n = 0;
    for (x = -10.0; x < 10.05; x += .00005) {
        i = rint(MAX_DIST * (.5 + .5*erf((x)/sqrt(2.0))));
        value = (int)rint(x*NETEM_DIST_SCALE);
        if (value < SHRT_MIN) value = SHRT_MIN;
        if (value > SHRT_MAX) value = SHRT_MAX;
        table[i] = value;
    }
    for (i = n = 0; i < MAX_DIST; i += 4) {
        normalDistribution[n++] = table[i];
    }

    free(table);
}

static int get_ticks(__u32 *ticks, const char *str)
{
    unsigned int t;

    if (get_time(&t, str))
        return -1;

    if (tc_core_time2big(t)) {
        fprintf(stderr, "Illegal %u time (too large)\n", t);
        return -1;
    }

    *ticks = tc_core_time2tick(t);
    return 0;
}

int netem_parse_costum_opt(struct qdisc_util *qu, int argc, char **argv, struct nlmsghdr *n, const char *dev){
    int dist_size = 0;
    struct rtattr *tail;
    struct tc_netem_qopt opt = { .limit = 1000 };
    __s16 *dist_data = NULL;

    for ( ; argc > 0; --argc, ++argv) {
        if (matches(*argv, "latency") == 0 ||
            matches(*argv, "delay") == 0) {
            NEXT_ARG();
            if (get_ticks(&opt.latency, *argv)) {
                return -1;
            }
            if (NEXT_IS_NUMBER()) {
                NEXT_ARG();
                if (get_ticks(&opt.jitter, *argv)) {
                    return -1;
                }
            }
        } else if (matches(*argv, "loss") == 0 ||
                   matches(*argv, "drop") == 0) {
            NEXT_ARG();
            if (!strcmp(*argv, "random")) {
                NEXT_ARG();
                double per;
                if (parse_percent(&per, *argv))
                    return -1;
                opt.loss = rint(per * UINT32_MAX);
            }
        } else if (matches(*argv, "distribution") == 0) {
            NEXT_ARG();
            dist_data = normalDistribution;
            dist_size = NORMAL_SIZE;
        }
    }
    tail = NLMSG_TAIL(n);
    if (addattr_l(n, 1024, TCA_OPTIONS, &opt, sizeof(opt)) < 0)
        return -1;
    if (dist_data) {
        if (addattr_l(n, MAX_DIST * sizeof(dist_data[0]),
                      TCA_NETEM_DELAY_DIST,
                      dist_data, dist_size * sizeof(dist_data[0])) < 0)
            return -1;
    }
    tail->rta_len = (void *) NLMSG_TAIL(n) - (void *) tail;
    return 0;
}

static struct
{
    unsigned int tb;
    int cloned;
    int flushed;
    char *flushb;
    int flushp;
    int flushe;
    int protocol, protocolmask;
    int scope, scopemask;
    __u64 typemask;
    int tos, tosmask;
    int iif, iifmask;
    int oif, oifmask;
    int mark, markmask;
    int realm, realmmask;
    __u32 metric, metricmask;
    inet_prefix rprefsrc;
    inet_prefix rvia;
    inet_prefix rdst;
    inet_prefix mdst;
    inet_prefix rsrc;
    inet_prefix msrc;
} filter;


int get_route_interface(unsigned int ip){
    struct {
        struct nlmsghdr	n;
        struct rtmsg		r;
        char			buf[1024];
    } req = {
            .n.nlmsg_len = NLMSG_LENGTH(sizeof(struct rtmsg)),
            .n.nlmsg_flags = NLM_F_REQUEST,
            .n.nlmsg_type = RTM_GETROUTE,
            .r.rtm_family = AF_INET,
    };

    char  *idev = NULL;
    char  *odev = NULL;

    struct nlmsghdr *answer;

    memset(&filter, 0, sizeof(filter));
    filter.mdst.bitlen = -1;
    filter.msrc.bitlen = -1;
    filter.oif = 0;
    filter.cloned = 2;

    inet_prefix addr;
    struct in_addr addr_c;
    addr_c.s_addr = ntohl(ip);
    char* rebuiltIP = inet_ntoa(addr_c);
    get_prefix(&addr, rebuiltIP, req.r.rtm_family);
    if (req.r.rtm_family == AF_UNSPEC)
        req.r.rtm_family = addr.family;
    if (addr.bytelen)
        addattr_l(&req.n, sizeof(req), RTA_DST, &addr.data, addr.bytelen);
    req.r.rtm_dst_len = addr.bitlen;

    if (req.r.rtm_dst_len == 0) {
        fprintf(stderr, "need at least a destination address\n");
        return -1;
    }

    req.r.rtm_family = AF_INET;

    req.r.rtm_flags |= RTM_F_LOOKUP_TABLE;

    if (rtnl_talk(&rth, &req.n, &answer) < 0)
        return -2;

    struct rtmsg *r = NLMSG_DATA(answer);
    int len = answer->nlmsg_len;
    struct rtattr *tb[RTA_MAX+1];

    len -= NLMSG_LENGTH(sizeof(*r));
    parse_rtattr(tb, RTA_MAX, RTM_RTA(r), len);
    unsigned int if_index = rta_getattr_u32(tb[RTA_OIF]);
    free(answer);
    return if_index;
}
