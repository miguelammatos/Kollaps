//
// Created by joao on 1/21/18.
//

#include <array>
#include <memory>
#include <sstream>
#include <iostream>
#include <iomanip>
#include <cstring>

extern "C" {
    #include "stdarg.h"
    #include "utils.h"
    #include "Destination.h"
    #include "TC.h"
};

extern int (*usageCallback)(unsigned int, unsigned long);
extern Destination* hostsByHandle;
struct rtnl_handle rth = {};
int hz = 0;
double ticks_in_usec = 0;



int callTC(std::string args) {
    std::stringstream cmd;
    cmd << TC_BIN << " " << args;
    //std::cout << cmd.str() << std::endl;
    int ret = system(cmd.str().c_str());
    return WEXITSTATUS(ret);
}


void TC_init(char* interface, short controllPort) {
    std::stringstream args;

    if(rtnl_open(&rth, 0)){
        std::cerr << "Failed to create rtlink handle" << std::endl;
        return;
    }

    /*VERY IMPORTANT docker sets txqueuelen to 0 on virtual interfaces
     * if we attach qdiscs to them, some will rely on txquelen and misbehave
     * this has been fixed in newer kernels, but older kernels dont automatically
     * restore the txqueuelen upon attaching a qdisc
     */
    set_txqueuelen(interface, TXQUEUELEN);

    hz = get_hz();
    ticks_in_usec = get_tick_in_usec();

    //Create the prio qdisc
    //This automatically creates 3 classes 1:1 1:2 and 1:3 with different priorities
    args << "qdisc add dev " << interface << " root handle 1:0 prio";
    callTC(args.str());

    //Create the htb qdisc
    //Attach it to the lowest priority 1:3
    args.str(std::string());
    args << "qdisc add dev " << interface << " parent 1:3 handle 4 htb default 1";
    callTC(args.str());

    //Create the filters
    args.str(std::string());
    //Create the first Hashtable e00:
    args << "filter add dev " << interface << " parent 4:0 prio 2 handle e00: protocol ip u32 divisor 256";
    callTC(args.str());


    args.str(std::string());
    //The kernel apparently truncates the hashkey to a value <= divisor so we have to use only the last bits
    args << "filter add dev " << interface
         << " protocol ip parent 4:0 prio 2 u32 ht 800:: match ip dst any hashkey mask "
         << FIRST_HASH_MASK << " at 16 link e00:"; //16 is offset in bytes (not bits)!!
    callTC(args.str());

    //Setup a filter to allow traffic on the controll port to go unrestricted and with maximum priority
    args.str(std::string());
    args << "filter add dev " << interface << " parent 1:0 prio 1 protocol ip u32 match ip dport " << controllPort
         << " 0xffff flowid 1:1";
    callTC(args.str());

    //Force all other traffic to be filtered through the htb filter
    args.str(std::string());
    args << "filter add dev " << interface << " parent 1:0 prio 2 protocol ip u32 match ip src 0.0.0.0/0 flowid 1:3";
    callTC(args.str());

}

void TC_initDestination(Destination *dest, char* interface) {
    std::stringstream args;
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

        /*<< dest->getOctetHex(3) << ":" << dest->getOctetHex(4) << " match ip dst "
          << dest->getIP() << "/32 flowid 4:" << handleStream.str();*/
    callTC(args.str());

}

void TC_destroy(char* interface) {
    rtnl_close(&rth);

    set_if_down(interface, 0);

    std::stringstream args;
    args << "qdisc delete root dev " << interface;
    callTC(args.str());

    set_if_up(interface, 0);

}

int update_class(const struct sockaddr_nl *who,
                    struct nlmsghdr *n, void *arg) {
    /* This is a callback that acts as a filter,
     * selecting only the classes we are interested in*/

    auto t = (tcmsg*)NLMSG_DATA(n);
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
    t.tcm_ifindex = if_nametoindex(interface);
    if (rtnl_dump_request(&rth, RTM_GETTCLASS, &t, sizeof(t)) < 0) {
        std::cerr << "Cannot send tc dump request" << std::endl;
        rtnl_close(&rth);
        return;
    }
    if (rtnl_dump_filter(&rth, update_class, nullptr) < 0) {
        std::cerr << "Cannot obtain tc dump" << std::endl;
        rtnl_close(&rth);
        return;
    }
}


void TC_changeBandwidth(Destination *dest, char* interface) {
    /*Use rtnetlink to communicate with the kernel directly
     * this should be a lot more efficient than calling tc
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
    req.t.tcm_ifindex = if_nametoindex(interface);

    unsigned int handle = (4 << 16) | dest->handle;
    req.t.tcm_handle = handle;

    struct rtattr *tail = NLMSG_TAIL(&req.n);
    addattr_l(&req.n, 1024, TCA_OPTIONS, nullptr, 0);


    __u64 rate64, ceil64; //Should be bytes per second

    auto bandwidth = (unsigned long)dest->bandwidth;
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
    if (tc_calc_rtable(&opt.rate, rtab, cell_log, mtu, LINKLAYER_ETHERNET, ticks_in_usec) < 0) {
        std::cerr << "htb: failed to calculate rate table." << std::endl;
        return;
    }
    opt.buffer = (__u32)((TIME_UNITS_PER_SEC*((double)buffer/(double)rate64))*ticks_in_usec);

    if (tc_calc_rtable(&opt.ceil, ctab, ccell_log, mtu, LINKLAYER_ETHERNET, ticks_in_usec) < 0) {
        std::cerr << "htb: failed to calculate ceil rate table." << std::endl;
        return;
    }
    opt.cbuffer = (__u32)((TIME_UNITS_PER_SEC*((double)cbuffer/(double)ceil64))*ticks_in_usec);

    opt.quantum = (__u32)(ceil64/(ceil64/10));

    addattr_l(&req.n, 2024, TCA_HTB_PARMS, &opt, sizeof(opt));
    addattr_l(&req.n, 3024, TCA_HTB_RTAB, rtab, 1024);
    addattr_l(&req.n, 4024, TCA_HTB_CTAB, ctab, 1024);
    tail->rta_len = (unsigned short) ((char*)NLMSG_TAIL(&req.n) - (char*)tail);

    //ll_init_map(&rth);

    if (rtnl_talk(&rth, &req.n, 0, 0) < 0)
        std::cerr << "failed to comunicate with tc" << std::endl;

    /*std::cout << "rate64: " << rate64 << std::endl <<
              "ceil64: " << ceil64 << std::endl <<
              "hz: " << hz << std::endl <<
              "buffer: " << buffer << std::endl <<
              "cbuffer: " << cbuffer << std::endl <<
              "opt.buffer: " << opt.buffer << std::endl <<
              "opt.cbuffer: " << opt.cbuffer << std::endl <<
              "TIME_UNITS_PER_SEC: " << TIME_UNITS_PER_SEC << std::endl <<
              "ticks_in_usec: " << ticks_in_usec << std::endl <<
              "quantum: " << opt.quantum << std::endl;*/

}
