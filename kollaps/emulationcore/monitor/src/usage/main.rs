#![no_std]
#![no_main]

use core::mem::{self, MaybeUninit};
use memoffset::offset_of;

use redbpf_macros::program;
use redbpf_probes::socket_filter::prelude::*;

use monitor::usage::{SocketAddr, message};

//map to hold perf_events
#[map(link_section = "maps")]
static mut perf_events: PerfMap<message> = PerfMap::with_max_entries(512);

//map to hold the bytes sent
#[map(link_section = "maps")]
static mut usage: HashMap<u32, u32> = HashMap::with_max_entries(4096);

//map to hold time that has passed
#[map(link_section = "maps")]
static mut time: HashMap<u32, u64> = HashMap::with_max_entries(4096);


program!(0xFFFFFFFE, "GPL");
#[socket_filter]
fn measure_tcp_lifetime(skb: SkBuff) -> SkBuffResult {
    let eth_len = mem::size_of::<ethhdr>();
    let eth_proto = skb.load::<__be16>(offset_of!(ethhdr, h_proto))? as u32;
    if eth_proto != ETH_P_IP {
        return Ok(SkBuffAction::Ignore);
    }

    let mut ip_hdr = unsafe { MaybeUninit::<iphdr>::zeroed().assume_init() };
    ip_hdr._bitfield_1 = __BindgenBitfieldUnit::new([skb.load::<u8>(eth_len)?]);

    if ip_hdr.version() != 4 {
        return Ok(SkBuffAction::Ignore);
    }


    // Use ttl + 32bits + 32bits for destination address for compatibility with Kernel 6.0 and above.
    // The struct iphdr has been redesigned in kernel 6.0 to contains an anonymous union instead of
    // saddr and daddr.
    // Report to the IP Header format: https://www.rfc-editor.org/rfc/rfc791#section-3.1
    // The offset bellow is calculated in term of bytes.
    // Implementation of iphdr for Kernel 5:  https://elixir.bootlin.com/linux/v5.19.17/source/include/uapi/linux/ip.h#L86
    // Implementation of iphdr for Kernel 6 : https://elixir.bootlin.com/linux/v6.0.17/source/include/uapi/linux/ip.h#L86
    let dest_addr_offset = eth_len + offset_of!(iphdr, ttl) + 4 + 4;

    //Retrieve IPs from skbuff
    let dst = SocketAddr::new(
        skb.load::<__be32>(dest_addr_offset)?,
    );


    //We send new values every 25 milli seconds for a given ip, via perf_events
    unsafe {
        //retrieve size of packet
        let len: u32 = (*skb.skb).len;
        let currenttime = bpf_ktime_get_ns();
        match time.get(&dst.addr) {
            None => {
                time.set(&dst.addr, &currenttime);
            }
            Some(oldtime) => {
                if currenttime - oldtime > 5000000 {
                    match usage.get(&dst.addr) {
                        None => usage.set(&dst.addr, &len),
                        Some(value) => {
                            let newvalue = value + len;
                            usage.set(&dst.addr, &newvalue);
                            perf_events.insert(skb.skb as *mut __sk_buff, &message { dst: dst.addr, bytes: newvalue });
                            time.set(&dst.addr, &currenttime);
                        }
                    }
                } else {
                    match usage.get(&dst.addr) {
                        None => usage.set(&dst.addr, &len),
                        Some(value) => {
                            let newvalue = value + len;
                            usage.set(&dst.addr, &newvalue);
                        }
                    }
                }
            }
        }
    }
    Ok(SkBuffAction::Ignore)
}