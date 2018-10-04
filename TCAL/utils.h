//
// Created by joao on 2/1/18.
//



#ifndef TCAL_UTILS_H
#define TCAL_UTILS_H

#include <net/if.h>
#include <asm/types.h>
#include <linux/netlink.h>
#include <linux/pkt_sched.h>
#include <libmnl/libmnl.h>
#include <linux/rtnetlink.h>

#define TIME_UNITS_PER_SEC	1000000

#define MIN(a, b) ((a) < (b) ? (a) : (b))
#define NLMSG_TAIL(nmsg) \
	((struct rtattr *) (((char *) (nmsg)) + NLMSG_ALIGN((nmsg)->nlmsg_len)))


//For some reason, some distros package an old version of netlink.h that doesnt include this:
#define NETLINK_EXT_ACK			11


enum link_layer {
    LINKLAYER_UNSPEC,
    LINKLAYER_ETHERNET,
    LINKLAYER_ATM,
};

struct rtnl_handle {
    int			fd;
    struct sockaddr_nl	local;
    struct sockaddr_nl	peer;
    __u32			seq;
    __u32			dump;
    int			proto;
    FILE		       *dump_fp;
#define RTNL_HANDLE_F_LISTEN_ALL_NSID		0x01
#define RTNL_HANDLE_F_SUPPRESS_NLERR		0x02
    int			flags;
};

int get_hz();
double get_tick_in_usec();
int tc_calc_rtable(struct tc_ratespec *r, __u32 *rtab,
                   int cell_log, unsigned int mtu,
                   enum link_layer linklayer, double ticks_in_usec);



int rtnl_open(struct rtnl_handle *rth, unsigned int subscriptions)
__attribute__((warn_unused_result));


void rtnl_close(struct rtnl_handle *rth);

int rtnl_dump_request(struct rtnl_handle *rth, int type, void *req, int len)
__attribute__((warn_unused_result));


typedef int (*rtnl_filter_t)(const struct sockaddr_nl *,
                             struct nlmsghdr *n, void *);
struct rtnl_dump_filter_arg {
    rtnl_filter_t filter;
    void *arg1;
    __u16 nc_flags;
};


int rtnl_dump_filter_nc(struct rtnl_handle *rth,
						rtnl_filter_t filter,
						void *arg, __u16 nc_flags);

#define rtnl_dump_filter(rth, filter, arg) \
	rtnl_dump_filter_nc(rth, filter, arg, 0)

int parse_rtattr(struct rtattr *tb[], int max, struct rtattr *rta, int len);

typedef int (*nl_ext_ack_fn_t)(const char *errmsg, uint32_t off,
							   const struct nlmsghdr *inner_nlh);

int rtnl_talk(struct rtnl_handle *rtnl, struct nlmsghdr *n,
			  struct nlmsghdr *answer, size_t len)
__attribute__((warn_unused_result));

int addattr_l(struct nlmsghdr *n, int maxlen, int type,
			  const void *data, int alen);

int set_if_down(const char *ifname, short flags);
int set_if_up(const char *ifname, short flags);
int set_txqueuelen(const char* ifname, int num_packets);

#endif //TCAL_UTILS_H
