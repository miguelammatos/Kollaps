// Licensed to the Apache Software Foundation (ASF) under one or more
// contributor license agreements.  See the NOTICE file distributed with
// this work for additional information regarding copyright ownership.
// The ASF licenses this file to You under the Apache License, Version 2.0
// (the "License"); you may not use this file except in compliance with
// the License.  You may obtain a copy of the License at

//    http://www.apache.org/licenses/LICENSE-2.0

// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

use std::sync::{Arc, Mutex};

//Represents a bridge and a container
pub struct Service{
    pub ip:u32,
    //amount of bytes sent to this container from the perspective of this EC
    pub last_bytes:u32,
    pub hostname:String,
    pub shared:bool,
    pub reuse:bool,
    pub replicas:u32,
    pub supervisor:bool,
    pub supervisor_port:u32,
    pub links:Vec<u16>,
    pub replica_id:usize,
    pub activepaths:Vec<String>,
    pub script:String

}

impl Service{
    pub fn new(hostname:String,shared:bool,reuse:bool,replicas:u32) -> Service {
        Service {
            ip: 0,
            last_bytes:0,
            hostname:hostname,
            shared:shared,
            reuse:reuse,
            replicas:replicas,
            supervisor:false,
            supervisor_port:0,
            links:vec![],
            replica_id:0,
            activepaths:vec![],
            script:"".to_string()
        }
    }

    pub fn attach_link(&mut self,id:u16){
        self.links.push(id);
    }

    pub fn remove_link(&mut self,id:u16){
        let index = self.links.iter().position(|&r| r == id);
        if !(index.is_none()){
            self.links.remove(index.unwrap());
        }
    }

    pub fn set_activepaths(&mut self,activepaths:Vec<String>){
        self.activepaths = activepaths;
    }
}


//Structure used to represent a link, paths have bandwidth, Links are descriptive
pub struct Link{
    pub id:u16,
    pub bandwidth:f32,
    pub latency:f32,
    pub jitter:f32,
    pub drop:f32,
    pub source:Arc<Mutex<Service>>,
    pub destination:Arc<Mutex<Service>>,
    pub flows:Vec<Vec<f32>>
}

impl Link{
    pub fn new(id:u16,latency:f32,jitter:f32,drop:f32,bandwidth:f32,source:Arc<Mutex<Service>>,destination:Arc<Mutex<Service>>) -> Link {
        Link {
            id: id,
            bandwidth: bandwidth,
            latency:latency,
            jitter:jitter,
            drop:drop,
            source:source,
            destination:destination,
            flows:vec![],
        }
    }

    pub fn clear_flows(&mut self){
        self.flows.clear();
    }

    // pub fn print(&mut self){
    //     println!("Link with id {} from {} to {} and parameters: bw {} | latency {:.1} | jitter {:.1} | drop {:.1}",
    //             self.id,self.source.lock().unwrap().hostname,self.destination.lock().unwrap().hostname,self.bandwidth,self.latency,self.jitter,self.drop);
    // }

    // pub fn print_flows(&mut self){
    //     println!("Link id: {}",self.id);
    //     for flow in &self.flows{
    //         println!("Flow with rtt {:.1} and bandwidth {:.1}",flow[0],flow[1])
    //     }
    // }
}   
//Path between two network elements, hold multiple links with different network values, the ones in the structure result from calculations
pub struct Path{
    pub links:Vec<u16>,
    pub id:u32,
    pub latency:f32,
    pub rtt:f32,
    pub drop:f32,
    pub max_bandwidth:f32,
    pub jitter:f32,
    pub used_bandwidth:f32,
    pub current_bandwidth:f32,
    pub start:String,
    pub finish:String,
}

impl Path{
    pub fn new(id:u32,links:Vec<u16>) -> Path {
        Path {
            links: links,
            id: id,
            latency:0.0,
            rtt:0.0,
            drop:0.0,
            max_bandwidth:0.0,
            jitter:0.0,
            used_bandwidth:0.0,
            current_bandwidth:0.0   ,
            start:"".to_string(),
            finish:"".to_string(),
        }
    }

    // pub fn print(&mut self){
    //     println!("Path with id {} from {} to {} and parameters: bw {} | latency {:.1} | jitter {:.1} | drop {:.1}",
    //             self.id,self.start,self.finish, self.max_bandwidth,self.latency,self.jitter,self.drop);

    //     println!("And has links:");
    //      for link in &self.links{
    //         println!("{}",link);
    //     }
    // }


    pub fn set_used_bandwidth(&mut self,used_bandwidth:f32){
        self.used_bandwidth = used_bandwidth;
    }

    pub fn set_current_bandwidth(&mut self,current_bandwidth:f32){
        self.current_bandwidth = current_bandwidth;
    }

    pub fn set_max_bandwidth(&mut self,max_bandwidth:f32){
        self.max_bandwidth = max_bandwidth;
    }
}

//Metadata circulating in the emulation
pub struct Flowu8{
    //bytes that circulated
    pub bandwidth:f32,
    //links it went through
    pub link_indices:Vec<u8>,
    pub age:u32,
}

impl Flowu8{
    pub fn new(bandwidth:f32,link_indices:Vec<u8>) -> Flowu8{
        Flowu8{
            bandwidth:bandwidth,
            link_indices:link_indices,
            age:1,
        }
    }

    // pub fn print(&mut self){
    //     println!("Flow with key {:?} and bandwidth {:.1} with age {}",
    //             self.link_indices,self.bandwidth,self.age);

    // }

}

//Metadata circulating in the emulation
pub struct Flowu16{
    //bytes that circulated
    pub bandwidth:f32,
    //links it went through
    pub link_indices:Vec<u16>,
    pub age:u32,
}

impl Flowu16{
    pub fn new(bandwidth:f32,link_indices:Vec<u16>) -> Flowu16{
        Flowu16{
            bandwidth:bandwidth,
            link_indices:link_indices,
            age:1,
        }
    }

    // pub fn print(&mut self){
    //     println!("Flow with key {:?} and bandwidth {:.1} with age {}",
    //             self.link_indices,self.bandwidth,self.age);

    // }

}