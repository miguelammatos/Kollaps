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

extern crate libc;
use std::borrow::BorrowMut;
use std::fs::OpenOptions;
use std::io::prelude::*;
use std::fs::File;
use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use std::thread;
use std::ffi::CString;

pub mod messages_capnp {
    include!(concat!(env!("OUT_DIR"), "/src/messages_capnp.rs"));
}

use capnp::serialize_packed;
use capnp::message::{Builder, HeapAllocator};
use crate::messages_capnp::message;
use std::io::BufReader;

pub struct FdSet(libc::fd_set);

//docker container id
static mut CONTAINERID:Option<String> = None;

//docker container name
static mut CONTAINERNAME:Option<String> = None;

//ip of container in int (smallendian)
static mut CONTAINERIP:u32 = 0;

//limit of links in topology
static mut CONTAINERLIMIT:u32 = 0;

//pipe to write to RM, pipe to read from RM, pipe to read local usage from RM
struct Communication {
    writepipe: Option<File>,
    readpipe: Option<File>,
    buf_reader: Option<BufReader<File>>
}

//struct of messages to RM
struct Message{
    content: Vec<u8>,
    index: usize,
}

//init global
static mut COMMUNICATION:Communication = Communication{
    writepipe: None,
    readpipe: None,
    buf_reader: None,
};

//init message (always the same struct all function write to and read from this)
static mut MESSAGE:Message = Message{
    content: Vec::new(),
    //where the to start writing information to
    index: 0,
};

//python reference
static mut COMMUNICATIONMANAGER: Option<PyObject> = None;


//python module definitions
#[pymodule]
fn libcommunicationcore(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(start, m)?)?;
    m.add_function(wrap_pyfunction!(register_communicationmanager, m)?)?;
    m.add_function(wrap_pyfunction!(start_polling_u8, m)?)?;
    m.add_function(wrap_pyfunction!(start_polling_u16, m)?)?;


    Ok(())
}

/**********************************************************************************************
*       buffer and different sized ints
**********************************************************************************************/


fn put_uint16(index:usize,value:u32){

    unsafe{
        MESSAGE.content[index] = ((value >> 0) & 0xff) as u8;
        MESSAGE.content[index+1] = ((value >> 8) & 0xff) as u8;
    }
}

/*fn put_uint32_in_buffer(value:u32) -> [u8;4]{

    let mut buffer = [0;4];
    buffer[0] = ((value >> 0) & 0xff) as u8;
    buffer[1] = ((value >> 8) & 0xff)  as u8;
    buffer[2] = ((value >> 16) & 0xff) as u8;
    buffer[3] = ((value >> 24)& 0xff) as u8;
    return buffer;
}*/

/*fn get_uint8(buffer:&Vec<u8>,index:usize)-> u32{

    return ((buffer[index] >> 0) & 0xff) as u32;

}*/

fn get_uint16(buffer:&Vec<u8>,index:usize) -> u16{
    return (u16::from(buffer[index+1]) << 8) | (u16::from(buffer[index])) ;

}


fn get_uint32(buffer:&Vec<u8>,index:usize) -> u32{

    return (u32::from(buffer[index+3]) << 24) | 
            (u32::from(buffer[index+2]) << 16) | 
            (u32::from(buffer[index+1]) << 8)  |
            (u32::from(buffer[index])) ;
}


fn init_content(){
    unsafe{
        MESSAGE.content.resize(512,0);
    }
}


/**********************************************************************************************
*       lib functions
**********************************************************************************************/


#[pyfunction]
//start the lib
fn start(_py: Python,id: String,name:String,ip:u32,link_count:u32){

    unsafe{
        CONTAINERID = Some(id.clone());
        CONTAINERNAME = Some(name.clone());
        CONTAINERIP = ip;
        if link_count <= 255{
            CONTAINERLIMIT = 8
        }
        else{
            CONTAINERLIMIT = 16
        }
        
    }

    //create files
    let pathwrite = "/tmp/pipewrite";
    let pathread = "/tmp/piperead";


    let pathread = format!("{}{}",pathread ,id.to_string());


    let filename = CString::new(pathread.clone()).unwrap();
        unsafe {
            libc::mkfifo(filename.as_ptr(), 0o644);
        }

    
    let pathwrite = format!("{}{}",pathwrite,id.to_string());


    let filename = CString::new(pathwrite.clone()).unwrap();
    unsafe {
        libc::mkfifo(filename.as_ptr(), 0o644);
    }


    let pathlocal = "/tmp/pipelocal";
    let pathlocal = format!("{}{}",pathlocal ,id.to_string());

    let filename = CString::new(pathlocal.clone()).unwrap();
    unsafe {
        libc::mkfifo(filename.as_ptr(), 0o644);
    }

    //collect pipe for reading
    print_message("STARTED GETTING READ PIPE".to_string());
    let fileread = OpenOptions::new().read(true).open(pathread).expect("file not found");
    print_message("GOT READ PIPE".to_string());

    //collect pipe for writing
    print_message("STARTED GETTING WRITE PIPE".to_string());
    let filewrite = OpenOptions::new().write(true).open(pathwrite).expect("file not found");

    print_message("GOT WRITE PIPE".to_string());

    unsafe{
        COMMUNICATION.readpipe = Some(fileread);
        COMMUNICATION.writepipe = Some(filewrite);
    }

}


//save reference to python
#[pyfunction]
fn register_communicationmanager(objectpython:PyObject){

    unsafe{
        COMMUNICATIONMANAGER = Some(objectpython);
    }
}


//start reading information from RM related to flows from other containers
#[pyfunction]
fn start_polling_u8(){

    let _handle = thread::spawn(move || {
    //buffer to hold data
    let mut receive_buffer = vec![0;1024];
    loop{

        // unsafe{
        //     COMMUNICATION.readpipe.as_ref().unwrap().read(&mut receive_buffer).map_err(|err| print_message(format!("{:?}", err))).ok();
        // }

        // let mut recv_ptr = 0;


        // let flow_count = receive_buffer[recv_ptr];
        // recv_ptr += 1;

        // //0 flows means the other node left
        // if flow_count == 0{

        // }else{
        //     for _f in 0..flow_count {

        //         let mut ids = Vec::new();
    
        //         let bandwidth = get_uint32(&receive_buffer,recv_ptr);
        //         recv_ptr += 4;
    
        //         let link_count = receive_buffer[recv_ptr] as usize;
        //         recv_ptr += 1;
    
        //         for _l in 0..link_count {
        //             ids.push(receive_buffer[recv_ptr]);
        //             recv_ptr+=1;
        //         }
    
        //          callreceive_flow(bandwidth,link_count,ids);
    
        //     }
        // }


    }
        
    });

}

//same as u8 but for u16
#[pyfunction]
fn start_polling_u16(){

    let _handle = thread::spawn(move || {
        //buffer to hold data

        unsafe{

            let mut buf_reader = BufReader::new(COMMUNICATION.readpipe.as_ref().unwrap());

                loop{
                
                    let message_reader = serialize_packed::read_message(buf_reader.borrow_mut(),capnp::message::ReaderOptions::new()).unwrap();
       

                    let message = message_reader.get_root::<message::Reader>().unwrap();

                    let mut flows = message.get_flows().unwrap();

                    for flow in flows{

                        let bandwidth = flow.get_bw();

                        let links = flow.get_links().unwrap();

                        let link_count = links.len() as u16;

                        let mut ids = vec![];


                        for i in (0..link_count){
                            ids.push(links.get(i as u32).get_id());
                        } 


                        callreceive_flow_16(bandwidth,link_count,ids);
                    } 


                }

        }
    });

}



//call python to give information about flows from other containers
fn callreceive_flow(bandwidth:u32,link_count:usize,ids:Vec<u8>){
    let gil = Python::acquire_gil();
    let py = gil.python();
    unsafe{
        COMMUNICATIONMANAGER.as_ref().unwrap().call_method(py,"receive_flow",(bandwidth,link_count,ids),None).map_err(|err| println!("{:?}", err)).ok();
    }
}

//call python to give information about flows from other containers
fn callreceive_flow_16(bandwidth:u32,link_count:u16,ids:Vec<u16>){
    let gil = Python::acquire_gil();
    let py = gil.python();
    unsafe{
        COMMUNICATIONMANAGER.as_ref().unwrap().call_method(py,"receive_flow",(bandwidth,link_count,ids),None).map_err(|err| println!("{:?}", err)).ok();
    }
}

fn print_message(message_to_print:String){
    let message;
    unsafe{
        message = Some(format!("RUST EC - {} : {} ",CONTAINERNAME.as_ref().unwrap(),message_to_print));
    }
    println!("{}",message.as_ref().unwrap());
}