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

use libloading::{Library, Symbol};
use crate::aux::print_and_fail;
use crate::aux::{print_message};
//Interacts with TC library
pub struct Emulation{
    library:Library,
    pub name:String

}

impl Emulation{

    pub fn new()-> Emulation{
        unsafe{
            Emulation{
                library:Library::new("/usr/local/bin/libTCAL.so").unwrap(),
                name:"".to_string()
            }
        }
    }

    pub fn init(&mut self,ip:u32){
        unsafe{
            let udp_port = 7073;
            let tcinit: Symbol<unsafe extern fn (u32,u32,u32)> = self.library.get(b"init").unwrap();
            tcinit(udp_port,1000,ip);
        }

    }

    pub fn initialize_path(&mut self, destinationip:u32,bandwidth:u32,latency:f32,jitter:f32,drop:f32){

        if latency==0.0{
            print_and_fail("Error: Shutting down. latency between two nodes can not be 0".to_string());
        }
        unsafe{

            let initdestination: Symbol< unsafe extern fn(u32,u32,f32,f32,f32)> = self.library.get(b"initDestination").unwrap();

            initdestination(destinationip,bandwidth,latency,jitter,drop);
        }

    }

    pub fn disable_path(&mut self, destinationip:u32){
        unsafe{
            
            let initdestination: Symbol< unsafe extern fn(u32,u32,f32,f32,f32)> = self.library.get(b"initDestination").unwrap();
            initdestination(destinationip,10000,1.0,0.0,1.0);
        }

    }

    pub fn change_bandwidth(&mut self, ip:u32,bandwidth:u32){

        let bw_in_kbps=bandwidth/1000;
        //print_message(self.name.clone(),format!("In change bw {} to {}",bandwidth,ip).to_string());
        if bw_in_kbps==0{
            //print_and_fail("Tried to change bandwidth to 0".to_string());
            print_message(self.name.clone(),"Tried changing to 0".to_string());
            unsafe{
                let changebw: Symbol< unsafe extern fn(u32,u32)> = self.library.get(b"changeBandwidth").unwrap();
                changebw(ip,1);
                //print_message(self.name.clone(),"Changed to 1".to_string());
            }
        }
        else{
            unsafe{
                let changebw: Symbol< unsafe extern fn(u32,u32)> = self.library.get(b"changeBandwidth").unwrap();
                //print_message(self.name.clone(),format!("Changing bw to {}",bandwidth/1000).to_string());
                changebw(ip,bw_in_kbps);
            }
        }
        //print_message(self.name.clone(),"Out of of change bw".to_string());

    }

    pub fn change_loss(&mut self, ip:u32,loss:f32){
        unsafe{
            let changeloss: Symbol< unsafe extern fn(u32,f32)> = self.library.get(b"changeLoss").unwrap();
            changeloss(ip,loss);
        }
    }

    pub fn change_latency(&mut self, ip:u32,latency:f32,jitter:f32){
        unsafe{
            let changelatency: Symbol< unsafe extern fn(u32,f32,f32)> = self.library.get(b"changeLatency").unwrap();
            changelatency(ip,latency,jitter);
        }
    }

    pub fn disconnect(&mut self){
        unsafe{
            let disconnect:Symbol<unsafe extern fn ()> = self.library.get(b"disconnect").unwrap();
            disconnect();
        }
    }


    pub fn reconnect(&mut self){
        unsafe{
            let reconnect:Symbol<unsafe extern fn ()> = self.library.get(b"reconnect").unwrap();
            reconnect();
        }
    }

    pub fn tear_down(&mut self){
        unsafe{
            let teardown:Symbol<unsafe extern fn (u32)> = self.library.get(b"tearDown").unwrap();
            teardown(0);
        }
    }


        
}