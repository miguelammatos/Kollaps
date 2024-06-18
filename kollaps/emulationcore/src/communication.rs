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

use std::borrow::BorrowMut;
use std::sync::{Arc, Mutex};
use std::fs::OpenOptions;
use std::fs::File;
use std::ffi::CString;
use crate::state::State;
use std::thread;
use crate::aux::print_message;
use capnp::serialize_packed;
use capnp::message::{Builder, HeapAllocator};
use crate::messages_capnp::message;
use std::io::BufReader;
use libc::O_WRONLY;


pub struct Communication{
    pub id:String,
    pub ip:u32,
    writepipe:Option<File>,
    readpipe:Arc<Mutex<Option<File>>>,
    pub name: String,
    pub filewriter:Option<File>,
    pub filereader:Arc<Mutex<Option<BufReader<File>>>>,
}

impl Communication{
    pub fn new(id:String) -> Communication{

        Communication{
            id:id.clone(),
            ip:0,
            writepipe:None,
            readpipe:Arc::new(Mutex::new(None)),
            name:"".to_string(),
            filewriter:None,
            filereader:Arc::new(Mutex::new(None)),

            
        }
    }

    pub fn init(&mut self){

        let pathwrite = "/tmp/pipewrite";
        let pathread = "/tmp/piperead";


        let pathread = format!("{}{}",pathread ,self.id.to_string());


        let filename = CString::new(pathread.clone()).unwrap();
            unsafe {
                libc::mkfifo(filename.as_ptr(), O_WRONLY as u32);
            }

        
        let pathwrite = format!("{}{}",pathwrite,self.id.to_string());


        let filename = CString::new(pathwrite.clone()).unwrap();
        unsafe {
            libc::mkfifo(filename.as_ptr(), O_WRONLY as u32);
        }

        let readpipe = Some(OpenOptions::new().read(true).open(pathread.clone()).expect("file not found"));

        self.readpipe = Arc::new(Mutex::new(readpipe));

        self.writepipe = Some(OpenOptions::new().write(true).open(pathwrite.clone()).expect("file not found"));



    }

    pub fn start_polling(&mut self,state:Arc<Mutex<State>>,linkcount:u32){

        start_polling_u16(state.clone(),self.readpipe.clone());

    }


    pub fn init_message<'a>(&mut self,mut msg:message::Builder<'a>, round_number:u32,flow_count:u32){
    
        msg.set_round(round_number);
        msg.init_flows(flow_count);


    }


    pub fn add_flow<'a>(&mut self,msg:message::Builder<'a>, bandwidth:u32,len_links:u32,links_vector:Vec<u16>,flow_number:u32){

        let flows = msg.get_flows().unwrap();

        let mut flow = flows.get(flow_number);

        flow.set_bw(bandwidth);

        let mut links = flow.init_links(len_links);

        for i in 0..links_vector.len(){
            links.reborrow().get(i as u32).set_id(links_vector[i as usize]);
        }
    }


    pub fn send_message(&mut self,msg:Builder<HeapAllocator>){
        
        serialize_packed::write_message(self.writepipe.as_ref().unwrap(), &msg).unwrap();

    }


}


//Pool info from our pipe
fn start_polling_u16(state:Arc<Mutex<State>>,readpipe:Arc<Mutex<Option<File>>>){

    let _handle = thread::spawn(move || {
    //buffer to hold data
        let name: String = state.lock().unwrap().name.clone();
        let readpipe_unlocked = readpipe.lock().unwrap();
        let mut filereader = BufReader::new(readpipe_unlocked.as_ref().unwrap());  
        loop{
            

            let message_reader = serialize_packed::read_message(filereader.borrow_mut(),capnp::message::ReaderOptions::new()).unwrap();

            
            let message: message::Reader<'_> = match message_reader.get_root::<message::Reader>(){
                Ok(message)=>{
                    message
                },
                Err(e)=>{
                    print_message(name.clone(),format!("Error in parsing message {} \n Contents: {:?}",e,message_reader.canonicalize()).to_string());
                    continue;

                }
            };

            let flows = message.get_flows().unwrap();
            for flow in flows{

                let bandwidth = flow.get_bw();

                let links = flow.get_links().unwrap();

                let link_count = links.len() as u16;

                let mut ids = vec![];

                for i in 0..link_count{
                    ids.push(links.get(i as u32).get_id());
                } 

                callreceive_flow_16(state.clone(),bandwidth,link_count,ids);

            }
            
        }
        
    });

}


fn callreceive_flow_16(state:Arc<Mutex<State>>,bandwidth:u32,link_count:u16,ids:Vec<u16>){

    state.lock().unwrap().get_current_graph().lock().unwrap().collect_flow_u16(bandwidth as f32,link_count,ids.clone());
}