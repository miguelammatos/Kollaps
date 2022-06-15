// This program can be executed by
// # cargo run --example tcp-lifetime [interface]
#![no_std]
#![no_main]
use core::mem::{self, MaybeUninit};
use memoffset::offset_of;

use redbpf_probes::socket_filter::prelude::*;

use monitor::usage::{SocketAddr,message};

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

    let ip_proto = skb.load::<__u8>(eth_len + offset_of!(iphdr, protocol))? as u32;
    if ip_proto != IPPROTO_TCP {
        return Ok(SkBuffAction::Ignore);
    }

    let mut ip_hdr = unsafe { MaybeUninit::<iphdr>::zeroed().assume_init() };
    ip_hdr._bitfield_1 = __BindgenBitfieldUnit::new([skb.load::<u8>(eth_len)?]);
    if ip_hdr.version() != 4 {
        return Ok(SkBuffAction::Ignore);
    }
    //Retrieve IPs from skbuff
    let ihl = ip_hdr.ihl() as usize;
    let dst = SocketAddr::new(
        skb.load::<__be32>(eth_len + offset_of!(iphdr, daddr))?,
        skb.load::<__be16>(eth_len + ihl * 4 + offset_of!(tcphdr, dest))?,
    );
    //We send new values every 25 milli seconds for a given ip, via perf_events
    unsafe{
        //retrieve size of packet
        let len:u32 = (*skb.skb).len;
        let currenttime = bpf_ktime_get_ns();
        match time.get(&dst.addr){
            None=>{
                time.set(&dst.addr,&currenttime);
            },
            Some(oldtime)=>{
                if currenttime-oldtime > 25000000{
                    match usage.get(&dst.addr){
                        None => usage.set(&dst.addr,&len),
                        Some(value) =>{
                            let newvalue = value + len;
                            usage.set(&dst.addr,&newvalue);
                            perf_events.insert(skb.skb as *mut __sk_buff,&message {dst:dst.addr,bytes:newvalue,}, );
                            time.set(&dst.addr,&currenttime);
                        }
                    }   
                }else{
                    match usage.get(&dst.addr){
                        None => usage.set(&dst.addr,&len),
                        Some(value) =>{
                            let newvalue = value + len;
                            usage.set(&dst.addr,&newvalue);
                        }
                    }
                }
            }
        }
    }

    Ok(SkBuffAction::Ignore)
}