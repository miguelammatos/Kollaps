use crate::elements::Service;
use std::sync::{Arc, Mutex};
use std::process;
use std::thread;
use std::time;
use pnet::datalink;
use ipnetwork::IpNetwork;
use subprocess::PopenConfig;
use subprocess::Popen;
use subprocess::Redirection;



//converts an array of u8 to an ip
pub fn convert_to_int(octets:[u8;4]) -> u32{
    return ((octets[0] as u32) <<24)+((octets[1] as u32) <<16)+((octets[2] as u32) <<8)+octets[3] as u32 
}

pub fn get_own_ip(networkdevice:Option<String>) -> u32{

    if networkdevice.is_none(){
        for iface in datalink::interfaces() {
            if iface.name == "eth0"{
                let ip = iface.ips[0];
                match ip{
                    IpNetwork::V4(ipv4)=>{
                        return convert_to_int(ipv4.ip().octets());
                    },
                    IpNetwork::V6(_ipv6) => return 0,
                }
            }
        }
        return 0;
    }
    else{
        for iface in datalink::interfaces() {
            if iface.name == networkdevice.as_ref().unwrap().to_string(){
                let ip = iface.ips[0];
                match ip{
                    IpNetwork::V4(ipv4)=>{
                        return convert_to_int(ipv4.ip().octets());
                    },
                    IpNetwork::V6(_ipv6) => return 0,
                }
            }
        }
        return 0;
    }
}


pub fn print_message(name:String,message_to_print:String){
    let message;
    message = Some(format!("RUST EC - {} : {} ",name,message_to_print));
    println!("{}",message.as_ref().unwrap());
}

//Struct used for the djisktra algorithm
pub struct Dijkstraentry{
    pub distance:f32,
    pub node:Arc<Mutex<Service>>,


}

impl Dijkstraentry{
    pub fn new(distance:f32,node:Arc<Mutex<Service>>) -> Dijkstraentry{
        Dijkstraentry{
            distance:distance,
            node:node
        }
    }
}

pub fn print_and_fail(message:String){

    println!("{}",message);
    let sleeptime = time::Duration::from_millis(2000);
    thread::sleep(sleeptime);

    process::exit(0);
}

pub fn start_script(script:String){
    Popen::create(&["sh",&script], PopenConfig {
        stdout: Redirection::Pipe, ..Default::default()
    }).unwrap();
}