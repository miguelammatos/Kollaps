//
// Created by joao on 2/1/18.
//

#include <asm/param.h>
#include <asm/types.h>
#include <linux/pkt_sched.h>
#include <time.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>

#include "utils.h"

//Copy pasted utilities from libnetlink source...
int rcvbuf = 1024 * 1024;

int get_hz(void) {
    char name[1024];
    int hz = 0;
    FILE *fp;

    if (getenv("HZ"))
        return atoi(getenv("HZ")) ?: HZ;

    if (getenv("PROC_NET_PSCHED"))
        snprintf(name, sizeof(name) - 1,
                 "%s", getenv("PROC_NET_PSCHED"));
    else if (getenv("PROC_ROOT"))
        snprintf(name, sizeof(name) - 1,
                 "%s/net/psched", getenv("PROC_ROOT"));
    else
        strcpy(name, "/proc/net/psched");

    fp = fopen(name, "r");

    if (fp) {
        unsigned int nom, denom;

        if (fscanf(fp, "%*08x%*08x%08x%08x", &nom, &denom) == 2)
            if (nom == 1000000)
                hz = denom;
        fclose(fp);
    }
    if (hz)
        return hz;
    return HZ;
}

double get_tick_in_usec(void){
    FILE *fp;
    __u32 clock_res;
    __u32 t2us;
    __u32 us2t;

    fp = fopen("/proc/net/psched", "r");
    if (fp == NULL)
        return -1;

    if (fscanf(fp, "%08x%08x%08x", &t2us, &us2t, &clock_res) != 3) {
        fclose(fp);
        return -1;
    }
    fclose(fp);

    /* compatibility hack: for old iproute binaries (ignoring
     * the kernel clock resolution) the kernel advertises a
     * tick multiplier of 1000 in case of nano-second resolution,
     * which really is 1. */
    if (clock_res == 1000000000)
        t2us = us2t;

    double clock_factor  = (double)clock_res / TIME_UNITS_PER_SEC;
    return  (double)t2us / us2t * clock_factor;
}

int tc_calc_rtable(struct tc_ratespec *r, __u32 *rtab,
                   int cell_log, unsigned int mtu,
                   enum link_layer linklayer, double ticks_in_usec)
{
    int i;
    unsigned int sz;
    unsigned int bps = r->rate;
    unsigned int mpu = r->mpu;

    if (mtu == 0)
        mtu = 2047;

    if (cell_log < 0) {
        cell_log = 0;
        while ((mtu >> cell_log) > 255)
            cell_log++;
    }

    for (i = 0; i < 256; i++) {
        sz = (i + 1) << cell_log;
        if(sz < mpu)
            sz = mpu;
        rtab[i] = (__u32)((TIME_UNITS_PER_SEC*(sz/bps))*ticks_in_usec);
    }

    r->cell_align =  -1;
    r->cell_log = cell_log;
    r->linklayer = (linklayer & TC_LINKLAYER_MASK);
    return cell_log;
}


void rtnl_close(struct rtnl_handle *rth)
{
    if (rth->fd >= 0) {
        close(rth->fd);
        rth->fd = -1;
    }
}

int rtnl_open_byproto(struct rtnl_handle *rth, unsigned int subscriptions,
                      int protocol)
{
    socklen_t addr_len;
    int sndbuf = 32768;
    int one = 1;

    memset(rth, 0, sizeof(*rth));

    rth->proto = protocol;
    rth->fd = socket(AF_NETLINK, SOCK_RAW | SOCK_CLOEXEC, protocol);
    if (rth->fd < 0) {
        perror("Cannot open netlink socket");
        return -1;
    }

    if (setsockopt(rth->fd, SOL_SOCKET, SO_SNDBUF,
                   &sndbuf, sizeof(sndbuf)) < 0) {
        perror("SO_SNDBUF");
        return -1;
    }

    if (setsockopt(rth->fd, SOL_SOCKET, SO_RCVBUF,
                   &rcvbuf, sizeof(rcvbuf)) < 0) {
        perror("SO_RCVBUF");
        return -1;
    }

    /* Older kernels may no support extended ACK reporting */
    setsockopt(rth->fd, SOL_NETLINK, NETLINK_EXT_ACK,
               &one, sizeof(one));

    memset(&rth->local, 0, sizeof(rth->local));
    rth->local.nl_family = AF_NETLINK;
    rth->local.nl_groups = subscriptions;

    if (bind(rth->fd, (struct sockaddr *)&rth->local,
             sizeof(rth->local)) < 0) {
        perror("Cannot bind netlink socket");
        return -1;
    }
    addr_len = sizeof(rth->local);
    if (getsockname(rth->fd, (struct sockaddr *)&rth->local,
                    &addr_len) < 0) {
        perror("Cannot getsockname");
        return -1;
    }
    if (addr_len != sizeof(rth->local)) {
        fprintf(stderr, "Wrong address length %d\n", addr_len);
        return -1;
    }
    if (rth->local.nl_family != AF_NETLINK) {
        fprintf(stderr, "Wrong address family %d\n",
                rth->local.nl_family);
        return -1;
    }
    rth->seq = time(NULL);
    return 0;
}

int rtnl_open(struct rtnl_handle *rth, unsigned int subscriptions)
{
    return rtnl_open_byproto(rth, subscriptions, NETLINK_ROUTE);
}

static int rtnl_dump_done(struct nlmsghdr *h)
{
    int len = *(int *)NLMSG_DATA(h);

    if (h->nlmsg_len < NLMSG_LENGTH(sizeof(int))) {
        fprintf(stderr, "DONE truncated\n");
        return -1;
    }

    if (len < 0) {
        errno = -len;
        switch (errno) {
            case ENOENT:
            case EOPNOTSUPP:
                return -1;
            case EMSGSIZE:
                fprintf(stderr,
                        "Error: Buffer too small for object.\n");
                break;
            default:
                perror("RTNETLINK answers");
        }
        return len;
    }

    return 0;
}

static void rtnl_dump_error(const struct rtnl_handle *rth,
                            struct nlmsghdr *h)
{

    if (h->nlmsg_len < NLMSG_LENGTH(sizeof(struct nlmsgerr))) {
        fprintf(stderr, "ERROR truncated\n");
    } else {
        const struct nlmsgerr *err = (struct nlmsgerr *)NLMSG_DATA(h);

        errno = -err->error;
        if (rth->proto == NETLINK_SOCK_DIAG &&
            (errno == ENOENT ||
             errno == EOPNOTSUPP))
            return;

        if (!(rth->flags & RTNL_HANDLE_F_SUPPRESS_NLERR))
            perror("RTNETLINK answers");
    }
}
int rtnl_dump_request(struct rtnl_handle *rth, int type, void *req, int len)
{
    struct nlmsghdr nlh = {
            .nlmsg_len = (__u32)NLMSG_LENGTH(len),
            .nlmsg_type = (__u16)type,
            .nlmsg_flags = NLM_F_DUMP | NLM_F_REQUEST,
            .nlmsg_seq = rth->dump = ++rth->seq,
    };
    struct sockaddr_nl nladdr = { .nl_family = AF_NETLINK };
    struct iovec iov[2] = {
            { .iov_base = &nlh, .iov_len = sizeof(nlh) },
            { .iov_base = req, .iov_len = (size_t)len }
    };
    struct msghdr msg = {
            .msg_name = &nladdr,
            .msg_namelen = sizeof(nladdr),
            .msg_iov = iov,
            .msg_iovlen = 2,
    };

    return sendmsg(rth->fd, &msg, 0);
}

int rtnl_dump_filter_l(struct rtnl_handle *rth,
                       const struct rtnl_dump_filter_arg *arg)
{
    struct sockaddr_nl nladdr;
    struct iovec iov;
    struct msghdr msg = {
            .msg_name = &nladdr,
            .msg_namelen = sizeof(nladdr),
            .msg_iov = &iov,
            .msg_iovlen = 1,
    };
    char buf[32768];
    int dump_intr = 0;

    iov.iov_base = buf;
    while (1) {
        int status;
        const struct rtnl_dump_filter_arg *a;
        int found_done = 0;
        int msglen = 0;

        iov.iov_len = sizeof(buf);
        status = recvmsg(rth->fd, &msg, 0);

        if (status < 0) {
            if (errno == EINTR || errno == EAGAIN)
                continue;
            fprintf(stderr, "netlink receive error %s (%d)\n",
                    strerror(errno), errno);
            return -1;
        }

        if (status == 0) {
            fprintf(stderr, "EOF on netlink\n");
            return -1;
        }

        if (rth->dump_fp)
            fwrite(buf, 1, NLMSG_ALIGN(status), rth->dump_fp);

        for (a = arg; a->filter; a++) {
            struct nlmsghdr *h = (struct nlmsghdr *)buf;

            msglen = status;

            while (NLMSG_OK(h, msglen)) {
                int err = 0;

                h->nlmsg_flags &= ~a->nc_flags;

                if (nladdr.nl_pid != 0 ||
                    h->nlmsg_pid != rth->local.nl_pid ||
                    h->nlmsg_seq != rth->dump)
                    goto skip_it;

                if (h->nlmsg_flags & NLM_F_DUMP_INTR)
                    dump_intr = 1;

                if (h->nlmsg_type == NLMSG_DONE) {
                    err = rtnl_dump_done(h);
                    if (err < 0)
                        return -1;

                    found_done = 1;
                    break; /* process next filter */
                }

                if (h->nlmsg_type == NLMSG_ERROR) {
                    rtnl_dump_error(rth, h);
                    return -1;
                }

                if (!rth->dump_fp) {
                    err = a->filter(&nladdr, h, a->arg1);
                    if (err < 0)
                        return err;
                }

                skip_it:
                h = NLMSG_NEXT(h, msglen);
            }
        }

        if (found_done) {
            if (dump_intr)
                fprintf(stderr,
                        "Dump was interrupted and may be inconsistent.\n");
            return 0;
        }

        if (msg.msg_flags & MSG_TRUNC) {
            fprintf(stderr, "Message truncated\n");
            continue;
        }
        if (msglen) {
            fprintf(stderr, "!!!Remnant of size %d\n", msglen);
            exit(1);
        }
    }
}

int rtnl_dump_filter_nc(struct rtnl_handle *rth,
                        rtnl_filter_t filter,
                        void *arg1, __u16 nc_flags)
{
    const struct rtnl_dump_filter_arg a[2] = {
            { .filter = filter, .arg1 = arg1, .nc_flags = nc_flags, },
            { .filter = NULL,   .arg1 = NULL, .nc_flags = 0, },
    };

    return rtnl_dump_filter_l(rth, a);
}

static void rtnl_talk_error(struct nlmsghdr *h, struct nlmsgerr *err,
                            nl_ext_ack_fn_t errfn)
{
    fprintf(stderr, "RTNETLINK answers: %s\n",
            strerror(-err->error));
}

static int __rtnl_talk(struct rtnl_handle *rtnl, struct nlmsghdr *n,
                       struct nlmsghdr *answer, size_t maxlen,
                       bool show_rtnl_err, nl_ext_ack_fn_t errfn)
{
    int status;
    unsigned int seq;
    struct nlmsghdr *h;
    struct sockaddr_nl nladdr = { .nl_family = AF_NETLINK };
    struct iovec iov = {
            .iov_base = n,
            .iov_len = n->nlmsg_len
    };
    struct msghdr msg = {
            .msg_name = &nladdr,
            .msg_namelen = sizeof(nladdr),
            .msg_iov = &iov,
            .msg_iovlen = 1,
    };
    char   buf[32768] = {};

    n->nlmsg_seq = seq = ++rtnl->seq;

    if (answer == NULL)
        n->nlmsg_flags |= NLM_F_ACK;

    status = sendmsg(rtnl->fd, &msg, 0);
    if (status < 0) {
        perror("Cannot talk to rtnetlink");
        return -1;
    }

    iov.iov_base = buf;
    while (1) {
        iov.iov_len = sizeof(buf);
        status = recvmsg(rtnl->fd, &msg, 0);

        if (status < 0) {
            if (errno == EINTR || errno == EAGAIN)
                continue;
            fprintf(stderr, "netlink receive error %s (%d)\n",
                    strerror(errno), errno);
            return -1;
        }
        if (status == 0) {
            fprintf(stderr, "EOF on netlink\n");
            return -1;
        }
        if (msg.msg_namelen != sizeof(nladdr)) {
            fprintf(stderr,
                    "sender address length == %d\n",
                    msg.msg_namelen);
            exit(1);
        }
        for (h = (struct nlmsghdr *)buf; status >= sizeof(*h); ) {
            int len = h->nlmsg_len;
            int l = len - sizeof(*h);

            if (l < 0 || len > status) {
                if (msg.msg_flags & MSG_TRUNC) {
                    fprintf(stderr, "Truncated message\n");
                    return -1;
                }
                fprintf(stderr,
                        "!!!malformed message: len=%d\n",
                        len);
                exit(1);
            }

            if (nladdr.nl_pid != 0 ||
                h->nlmsg_pid != rtnl->local.nl_pid ||
                h->nlmsg_seq != seq) {
                /* Don't forget to skip that message. */
                status -= NLMSG_ALIGN(len);
                h = (struct nlmsghdr *)((char *)h + NLMSG_ALIGN(len));
                continue;
            }

            if (h->nlmsg_type == NLMSG_ERROR) {
                struct nlmsgerr *err = (struct nlmsgerr *)NLMSG_DATA(h);

                if (l < sizeof(struct nlmsgerr)) {
                    fprintf(stderr, "ERROR truncated\n");
                } else if (!err->error) {
                    if (answer)
                        memcpy(answer, h,
                               MIN(maxlen, h->nlmsg_len));
                    return 0;
                }

                if (rtnl->proto != NETLINK_SOCK_DIAG &&
                    show_rtnl_err)
                    rtnl_talk_error(h, err, errfn);

                errno = -err->error;
                return -1;
            }

            if (answer) {
                memcpy(answer, h,
                       MIN(maxlen, h->nlmsg_len));
                return 0;
            }

            fprintf(stderr, "Unexpected reply!!!\n");

            status -= NLMSG_ALIGN(len);
            h = (struct nlmsghdr *)((char *)h + NLMSG_ALIGN(len));
        }

        if (msg.msg_flags & MSG_TRUNC) {
            fprintf(stderr, "Message truncated\n");
            continue;
        }

        if (status) {
            fprintf(stderr, "!!!Remnant of size %d\n", status);
            exit(1);
        }
    }
}

int rtnl_talk(struct rtnl_handle *rtnl, struct nlmsghdr *n,
              struct nlmsghdr *answer, size_t maxlen)
{
    return __rtnl_talk(rtnl, n, answer, maxlen, true, NULL);
}

int addattr_l(struct nlmsghdr *n, int maxlen, int type, const void *data,
              int alen)
{
    int len = RTA_LENGTH(alen);
    struct rtattr *rta;

    if (NLMSG_ALIGN(n->nlmsg_len) + RTA_ALIGN(len) > maxlen) {
        fprintf(stderr,
                "addattr_l ERROR: message exceeded bound of %d\n",
                maxlen);
        return -1;
    }
    rta = NLMSG_TAIL(n);
    rta->rta_type = type;
    rta->rta_len = len;
    if (alen)
        memcpy(RTA_DATA(rta), data, alen);
    n->nlmsg_len = NLMSG_ALIGN(n->nlmsg_len) + RTA_ALIGN(len);
    return 0;
}

int parse_rtattr_flags(struct rtattr *tb[], int max, struct rtattr *rta,
                       int len, unsigned short flags)
{
    unsigned short type;

    memset(tb, 0, sizeof(struct rtattr *) * (max + 1));
    while (RTA_OK(rta, len)) {
        type = rta->rta_type & ~flags;
        if ((type <= max) && (!tb[type]))
            tb[type] = rta;
        rta = RTA_NEXT(rta, len);
    }
    if (len)
        fprintf(stderr, "!!!Deficit %d, rta_len=%d\n",
                len, rta->rta_len);
    return 0;
}

int parse_rtattr(struct rtattr *tb[], int max, struct rtattr *rta, int len)
{
    return parse_rtattr_flags(tb, max, rta, len, 0);
}


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


int set_if_flags(const char *ifname, short flags)
{
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

int set_if_up(const char *ifname, short flags)
{
    return set_if_flags(ifname, flags | IFF_UP);
}

int set_if_down(const char *ifname, short flags)
{
    return set_if_flags(ifname, flags & ~IFF_UP);
}