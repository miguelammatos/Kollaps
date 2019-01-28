//
// Created by joao on 10/12/18.
//

#ifndef TCAL_TCAL_UTILS_H
#define TCAL_TCAL_UTILS_H



#define MAX_DIST	(16*1024)
#define NORMAL_SIZE  (4*1024)
#define NEXT_IS_NUMBER() (NEXT_ARG_OK() && isdigit(argv[1][0]))
static int get_ticks(__u32 *ticks, const char *str);
int netem_parse_costum_opt(struct qdisc_util *qu, int argc, char **argv, struct nlmsghdr *n, const char *dev);
void fillNormalDist();

int set_txqueuelen(const char* ifname, int num_packets);
int set_if_flags(const char *ifname, short flags);
int set_if_up(const char *ifname, short flags);
int set_if_down(const char *ifname, short flags);

struct qdisc_util *get_qdisc_kind(const char *str);
struct filter_util *get_filter_kind(const char *str);

void open_rtnl(struct rtnl_handle* h);
void close_rtnl(struct rtnl_handle* h);

int get_route_interface(unsigned int ip);
#endif //TCAL_TCAL_UTILS_H
