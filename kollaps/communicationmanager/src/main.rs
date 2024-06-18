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

use std::borrow::Borrow;
use std::borrow::BorrowMut;
use std::io::prelude::*; 
use std::thread;
use std::env;
//use async_std::task;
//use async_std::task::block_on;
use std::net::{TcpStream,TcpListener};
use crossbeam_channel::{unbounded, Sender,Receiver};
use std::net::Shutdown;
use std::os::unix::io::AsRawFd;
use std::time;
use std::collections::HashMap;
type Result<T> = std::result::Result<T, Box<dyn std::error::Error + Send + Sync>>;
mod select;
use crate::select::{FdSet,select};
mod aux;
use crate::aux::{print_message,has_dashboard,retrieve_local_ids,retrieve_remote_ips,get_containers,clone_pipes,wait_for_pipe_creation,get_uint16,put_uint16,Container};
use std::sync::{Arc, Mutex};
use std::fs::File;

pub mod messages_capnp {
    include!(concat!(env!("OUT_DIR"), "/src/messages_capnp.rs"));
}

use capnp::serialize_packed;
use capnp::message::{Builder, HeapAllocator};
use crate::messages_capnp::message;
use std::io::BufReader;

static mut CONTAINERS:Option<Vec<Arc<Mutex<Container>>>> = None;


fn main()-> Result<()>{

    let containercount = env::args()
        .nth(1)
        .unwrap();

    //address where the socket will run
    let addr = env::args()
        .nth(2)
        .unwrap();

    let sleeptime = time::Duration::from_millis(1000);

    thread::sleep(sleeptime);
    
    let containercount = containercount.parse::<usize>().unwrap();

    
    let remote_ips = aux::retrieve_remote_ips(":8080".to_string());

    print_message(format!("{:?}",remote_ips)).expect("Couldn't add to file");

    setup(remote_ips.clone(),containercount,addr.clone());

    // let handle = thread::spawn(move || {setup});
    // handle.join();

    let local_ids = retrieve_local_ids();

    let has_dashboard = has_dashboard();
    
    let remote_ips = retrieve_remote_ips(":8081".to_string());

    print_message(format!("{:?}",local_ids)).expect("Couldn't add to file");
    //print_message(format!("{:?}",remote_ips)).expect("Couldn't add to file");

    //wait for EM's to create pipes
    print_message("Waiting for pipes".to_string());
    wait_for_pipe_creation(local_ids.clone(),"/tmp/piperead".to_string());

    wait_for_pipe_creation(local_ids.clone(),"/tmp/pipewrite".to_string());
    print_message("Pipes created".to_string());

    //start exchanging of information
    //let handle = thread::spawn(move || {start(addr,local_ids,remote_ips,has_dashboard)});
    //handle.join();

    let containers = get_containers(local_ids.clone(),"/tmp/piperead".to_string()).clone();

    unsafe{
        CONTAINERS = Some(containers);
    }


    start_remote_producers(addr,local_ids.clone(),remote_ips.clone(),has_dashboard);

    start_message_exchange(local_ids.clone(),remote_ips.clone(),has_dashboard.clone());


    Ok(())

}

/**********************************************************************************************
*       setup
**********************************************************************************************/

//exchanges information with other machines to assure all machines started their containers
fn setup(remote_ips:Vec<String>,containercount:usize,addr:String)-> Result<()>{
    print_message(format!("SETUP STARTED container count is {}",containercount.to_string())).expect("Couldn't add to file");

    let mut channelvecsender = vec![];
    let mut channelvecreceiver = vec![];

    let remote_ips_len = remote_ips.len().clone();

    for _remote_ip in remote_ips.clone(){
        let (sender, receiver) = unbounded();
        channelvecsender.push(sender);
        channelvecreceiver.push(receiver);
    }

    //check if there are remote ips, if yes create an accept loop to accept connections
    if remote_ips.len() !=0{
        //let accept_setup_loop = accept_setup_loop(addr.clone(),channelvecsender.clone(),remote_ips.len().clone());
        thread::spawn(move || {accept_setup_loop(addr.clone(),channelvecsender.clone(),remote_ips_len.clone())});
    }

    let sleeptime = time::Duration::from_millis(1000);
    print_message("Starting to connect to other machines ".to_string());

    //connect to other machines
    let mut streams = vec![];
    let mut ips_connected = vec![];
    while ips_connected.len() != remote_ips_len{
        thread::sleep(sleeptime);
        for (i,remote_ip) in remote_ips.clone().iter().enumerate(){
            if !(ips_connected.contains(&i)){
                print_message(format!("CONNECTING TO {}",remote_ip.clone()));
                let stream = TcpStream::connect(remote_ip.clone());
                match stream{
                    Ok(stream)=> {
                        streams.push(stream);
                        print_message(format!("CONNECTED TO {} pos is {}",remote_ip.clone(),i));
                        ips_connected.push(i.clone());
                    },
                    Err(e)=> println!("{}",e.to_string()),
                }; 
            }   
        }
    }

    let handle = thread::spawn(move || {wait_until_containers_start(streams,containercount,channelvecreceiver.clone())});

    handle.join();
    print_message("SETUP ENDED".to_string()).expect("Couldn't add to file");

    Ok(())
}

//exchange number of containers started with other machines
fn wait_until_containers_start(streams:Vec<TcpStream>,containercount:usize,channelvecreceiver:Vec<Receiver<u16>>) -> Result<()>{

    print_message("WAITING FOR CONTAINERS TO START".to_string()).expect("Couldn't add to file");
    
    loop{
        //message
        let buffer = vec![0;2];

        //curent number of IDS
        //print_message("Retrieving local".to_string());
        let local_ids = retrieve_local_ids();
        //print_message("Retrieved local".to_string());

        let containers_responsible = local_ids.len();

        let mut buffer = put_uint16(buffer,0,containers_responsible as u32);

        //send to other machines
        let mut stream_count = 0;
        for mut stream in &streams{
           //print_message(format!("Trying to write to {}",stream_count).to_string());
            let bytes = stream.write(&buffer);

            match bytes{
                Ok(n) => {
                    stream.flush();
                    print_message(format!("Wrote {} to {}",n,stream_count).to_string());
                    stream_count+=1;
                },
                Err(e) =>{
                    print_message(format!("Err: {} to {}",e,stream_count).to_string());
                }
            };
        }


        //print_message("Wrote to streams".to_string());


        //receives from other threads(other machines)
        let mut count = 0;
        let mut receiver_count = 0;
        for receiver in &channelvecreceiver{
            // let received = receiver.try_recv();
            // match received{
            //     Ok(received) =>{
            //         receiver_count = receiver_count +1;
            //         count = count + received as usize;
            //         print_message(format!("received is {} from {} and local_ids is {}",received.to_string(),receiver_count.to_string(),local_ids.len())).expect("Couldn't add to file");
            //     }
            //     Err(e) => {
            //         receiver_count = receiver_count +1;
            //         print_message(format!("Failed to read from channel {}; err = {:?}",receiver_count,e).to_string());
  
            //     }
            // };
            let received = receiver.recv().unwrap() as usize;
            count = count + received as usize;
            print_message(format!("received is {} from {} and local_ids is {}",received.to_string(),receiver_count.to_string(),local_ids.len())).expect("Couldn't add to file");
            receiver_count = receiver_count +1;
        }

        //print_message("Received from streams".to_string());

        //check if all machines started if yes, send message to end the setup
        //print_message(format!("local ids count is {}",local_ids.len()));
        if count + local_ids.len() == containercount as usize{
            print_message("Finishing setup \n".to_string());    
            buffer.push(1);
            for mut stream in &streams{
                stream.write(&buffer).expect("Failed to write to stream");
            }
            break;
        }

        let sleeptime = time::Duration::from_millis(1000);

        thread::sleep(sleeptime);

    }

    for stream in &streams{
        stream.shutdown(Shutdown::Both)?;
    }

    print_message("ENDED WAITING FOR CONTAINERS".to_string()).expect("Couldn't add to file");

    Ok(())
}


//accept connections from other machines for setup
fn accept_setup_loop(addr:String,sender: Vec<Sender<u16>>,number_of_remotes:usize) -> Result<()>{

    let addr = format!("{}{}",addr,":8080");
    print_message(format!("ACCEPT_SETUP_LOOP STARTED on {}",addr.to_string())).expect("Couldn't add to file");
    let listener = TcpListener::bind(addr.clone()).unwrap();

    let mut incoming = listener.incoming();

    let remotecount = Arc::new(Mutex::new(0));
    
    let mut vector_handles = vec![];
    // while let Some(stream) = incoming.next(){
    //     let mut remotecount = remotecount.lock().unwrap();
    //     let stream = stream?;
    //     let peer_addr = stream.peer_addr()?;
    //     print_message(format!("Accepted {} count is {}",remotecount,peer_addr));
    //     let join_handle = task::spawn(receive_container_count(stream,peer_addr.to_string().clone(),sender[*remotecount].clone()));
    //     print_message(format!("Created task {} for peer {}",remotecount,peer_addr));
    //     vector_handles.push(join_handle);

    //     *remotecount += 1;

    //     if *remotecount == number_of_remotes{
    //         break;
    //     }

    // }

    for stream in listener.incoming() {
        match stream {
            Ok(stream) => {
                let mut remotecount = remotecount.lock().unwrap();
                
                let peer_addr = stream.peer_addr()?;

                let sender_channel = sender[*remotecount].clone();
                print_message(format!("Accepted {} count is {}",remotecount,peer_addr));
                let join_handle = thread::spawn(move || {receive_container_count(stream,peer_addr.to_string().clone(),sender_channel.clone())});
                print_message(format!("Created task {} for peer {}",remotecount,peer_addr));
                vector_handles.push(join_handle);

                *remotecount += 1;

                if *remotecount == number_of_remotes{
                    break;
                }
            }
            Err(e) => { print_message("Failed".to_string()); }
        };
    }
    

    for handle in vector_handles{
        handle.join();
    }
    print_message(format!("ACCEPT_SETUP_LOOP ENDED ")).expect("Couldn't add to file");

    Ok(())
}

//reads from the other hosts how many containers they started
fn receive_container_count(mut stream:TcpStream,_peer:String,sender:Sender<u16>){

    print_message(format!("Started for peer {}",_peer).to_string());

    loop{
        let mut buffer = [0; 3];
        print_message(format!("Trying to read from peer {}",_peer).to_string());  
        let _n = match stream.read(&mut buffer){
            Ok(n) => n,
            Err(e) => {
                print_message(format!("failed to read from socket; err = {:?}", e).to_string());
                0
            }
        };
        //print_message(format!("Read from peer {}",_peer).to_string());
        //end of loop message
        if buffer[2] == 1{
            print_message("Ended loop".to_string());
            let containers = get_uint16(buffer,0);
            sender.send(containers).map_err(|err| println!("{:?}", err));
            break;
        }
        let containers = get_uint16(buffer,0);
        //print_message(format!("Trying to send from rcc peer {}",_peer).to_string());
        sender.send(containers).map_err(|err| println!("{:?}", err));
        //print_message(format!("Sent from rcc peer {}",_peer).to_string());

        // let send_result = sender.try_send(containers);
        // match send_result{
        //     Ok(send_result) =>{
        //         print_message(format!("Sent from rcc peer {}",_peer).to_string());
        //         //print_message(format!("received is {} from {} and local_ids is {}",received.to_string(),receiver_count.to_string(),local_ids.len())).expect("Couldn't add to file");
        //     }
        //     Err(e) => {
        //         print_message(format!("Failed to send to channel {}; err = {:?}", e,_peer).to_string());

        //     }
        // };

    }

}

/**********************************************************************************************
*       start of exchange mechanisms
**********************************************************************************************/

//starts the exchange of  metadata
fn start_remote_producers(addr:String,local_ids:Vec<String>,remote_ips:Vec<String>,has_dashboard:bool){

    print_message("ENTERED START".to_string()).expect("Couldn't add to file");
    
    //Start accept loop that will start threads to receive metadata from other hosts
    if remote_ips.len() != 0{
        //let accept_loop = accept_loop(remote_ips.len().clone(),addr,containers.clone());
        thread::spawn(move ||{accept_loop(remote_ips.len().clone(),addr)});
    }

    let sleeptime = time::Duration::from_millis(1000);
    thread::sleep(sleeptime);

}




/**********************************************************************************************
*       start of information exchange
**********************************************************************************************/

fn start_message_exchange(vector_ids:Vec<String>,remote_ips:Vec<String>,dashboard:bool)-> Result<()>{

    print_message("STARTED MESSAGE EXCHANGE".to_string()).expect("Couldn't add to file");

    //hold pipes to read from
    let mut pipes_read = vec![];

    //position of pipe in vector (key-> fd_raw,value-> position)
    let mut pipes_position = HashMap::new();
    let pathwrite = "/tmp/pipewrite";

    //hold pipes to write to (we want to write to information every container but ourselfs so we create a vector for each container that containers every pipe but the pipe to themselfs)
    let mut vector_pipes_id = vec![];

    for i in 0..vector_ids.clone().len(){

        //open pipe
        let path = format!("{}{}",pathwrite,vector_ids[i]);

        let file = File::open(path.clone()).unwrap();

        let buf_reader = BufReader::new(file);

        //insert in hashmap
        pipes_position.insert(buf_reader.get_ref().as_raw_fd(),i);
        //insert in vector
        pipes_read.push(buf_reader);

        //containers every pipe but the one respective to vectorids[i]
        let pipes;
        unsafe{
            pipes = clone_pipes(vector_ids[i].clone(),CONTAINERS.as_ref().unwrap());
        }

        vector_pipes_id.push(pipes);
    }

    //if we are the host with the dashboard remove it because the dashboard does not send information
    if dashboard{
        pipes_read.remove(pipes_read.len() - 1 as usize);
        print_message(format!("REMOVED DASHBOARD")).expect("Couldn't add to file");
    }

    //hold references to remote hosts
    let mut streams = vec![];
    let mut ips_connected = vec![];

    let sleeptime = time::Duration::from_millis(1000);
    //open connections
    while ips_connected.len() != remote_ips.clone().len(){
        for (i,remote_ip) in remote_ips.clone().iter().enumerate(){
            if !(ips_connected.contains(&i)){
                print_message(format!("CONNECTING TO {}",remote_ip.clone())).expect("Couldn't add to file");
                let stream = TcpStream::connect(remote_ip.clone());
                match stream{
                    Ok(stream)=> {
                        streams.push(stream);
                        print_message(format!("CONNECTED TO {}",remote_ip.clone())).expect("Couldn't add to file");
                        ips_connected.push(i.clone());
                    },
                    Err(e)=> println!("{}",e.to_string()),
                }; 
            }   
        }
        thread::sleep(sleeptime);
    }

    //Max fd for select
    let mut max = 0;

    //Calculate max
    for pipe in &pipes_read{
        let fd = pipe.get_ref().as_raw_fd();
        max = fd.max(max);
    }
    
    let mut fd_set = FdSet::new();

    let mut vector_fd = vec![];
    for pipe in &pipes_read{
        let fd = pipe.get_ref().as_raw_fd();
        print_message(format!("FD is {}",fd.to_string())).expect("Couldn't add to file");
        fd_set.set(fd);
        vector_fd.push(fd);
        max = fd.max(max);
    }
    print_message("STARTED EXCHANGE ALL SET".to_string()).expect("Couldn't add to file");
    loop{
        match select(
            max + 1,
            Some(&mut fd_set),                               // read
            None,                                            // write
            None,                         // error//
//            Some(&make_timeval(time::Duration::from_millis(1))))
            None) // timeout
            {
            Ok(_res) => {
                for i in &vector_fd{
                    if (fd_set).is_set(*i) {

                        //get position of pipe in vector of pipes with fd value i
                        let position = pipes_position.get(&i);

                        //read from pipe
                        let buf_reader = pipes_read[*position.unwrap()].borrow_mut();

                        //create new message 
                        let message_reader = serialize_packed::read_message(buf_reader,capnp::message::ReaderOptions::new()).unwrap();
                    
                        let mut message_to_send = capnp::message::Builder::new(capnp::message::HeapAllocator::new());
                        
                        message_to_send.set_root(message_reader.get_root::<message::Reader>().unwrap()).expect("Failed to set root");

                        //write to vector that contains every pipe but the container it read from
                        let vector_pipes:Vec<Arc<Mutex<Container>>> = vector_pipes_id[*position.unwrap()].clone();
                        for pipe in vector_pipes{ 

                                pipe.lock().unwrap().write(message_to_send.borrow());
                        }
                        //write to remote hosts
                        for mut stream in &streams{
                            serialize_packed::write_message(stream, message_to_send.borrow()).unwrap();
                            stream.flush().expect("Failed to flush to stream");
                        }

        
                        fd_set.set(*i);
                    }
                    fd_set.set(*i);
                }

            }
            Err(err) => {
                println!("Failed to select: {:?}", err);
            }
        }
    }
}

//receives metadata from other hosts
fn remote_producer<'a>(stream:TcpStream) {

    print_message("STARTED REMOTE PRODUCER".to_string()).expect("Couldn't add to file");    

    let mut buf_reader = BufReader::new(stream);

        loop{

            let message_reader = serialize_packed::read_message(buf_reader.borrow_mut(),capnp::message::ReaderOptions::new()).unwrap(); 

            let mut message_to_send: Builder<HeapAllocator> = capnp::message::Builder::new_default();
                        
            message_to_send.set_root(message_reader.get_root::<message::Reader>().unwrap()).expect("Failed to set root");
            unsafe{
                for pipe in CONTAINERS.as_ref().unwrap(){

                    pipe.lock().unwrap().write(message_to_send.borrow());
                } 
            }

        }

    
}

//accepts connections from other hosts
fn accept_loop(count:usize,addr:String) -> Result<()>{

    //Bind the socket to the process

    let addr = format!("{}{}",addr,":8081");
    print_message(format!("Listening on: {}",addr)).expect("Couldn't add to file");

    let listener = TcpListener::bind(addr).unwrap();

    let mut incoming = listener.incoming();

    let mut peers = 0;
    while let Some(stream) = incoming.next(){

        let stream = stream?;
        let peer_addr = stream.peer_addr()?;
        
        print_message(format!("PEER IS : {}",peer_addr).to_string());

        //Start remote producer
        thread::spawn( || {remote_producer(stream)});

        peers+=1;
        
        if peers == count{
            break;
        }

    }
    print_message(format!("ACCEPT_LOOP ENDED ")).expect("Couldn't add to file");


    Ok(())

}




