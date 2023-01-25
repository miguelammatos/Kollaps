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

use std::env;
use std::sync::Arc;
use std::sync::Mutex;
use emulationcore::xmlgraphparser::XMLGraphParser;
use emulationcore::state::State;
use async_std::prelude::*;
use async_std::task;
use async_std::net::TcpStream;
use std::{time};
use std::fs::OpenOptions;
use std::io::prelude::*; 
use std::thread;
use std::io::{BufRead, BufReader};
use roxmltree::Document;
use emulationcore::aux::print_message;


fn main() {

    let topology_file = env::args().nth(1).unwrap();

    let command = env::args().nth(2).unwrap();

    task::block_on(process_command(topology_file.clone(),command.clone())).map_err(|err| println!("{:?}", err)).ok();

    
}

type Result<T> = std::result::Result<T, Box<dyn std::error::Error + Send + Sync>>;
async fn process_command(topology_file:String,command:String)->Result<()>{

    let shutdown_command:u8 = 2;
    let ready_command:u8 = 3;
    let start_command:u8 = 4;
    
    if command == "ready"{
        let state = Arc::new(Mutex::new(State::new("controller".to_string())));

        state.lock().unwrap().insert_graph();
    
        let mut parser = XMLGraphParser::new(state.clone(),"baremetal".to_string());

        let text = std::fs::read_to_string(topology_file.clone()).unwrap();
        
        let doc = Document::parse(&text).unwrap();

        let root = doc.root().first_child().unwrap();
    
        parser.fill_graph(root);

        let mut remote_ips = vec![];
    
        let ips = parser.ips.clone();
    
        let mut file = OpenOptions::new()
        .write(true)
        .create(true)
        .append(true)
        .open("/ips.txt")
        .unwrap();
    
        for ip in ips{

            let mut ip_with_port;
            if ip == parser.controller_ip{
                continue;
            } 
            else{
                ip_with_port = format!("{}{}",ip,":7073");
            }          
            remote_ips.push(ip_with_port.clone());
            file.write_all(format!("{}\n",ip_with_port.clone()).as_bytes()).expect("Unable to write data");

            ip_with_port = format!("0.0.0.0{}",":7073");
            remote_ips.push(ip_with_port.clone());
        }


        let sleeptime = time::Duration::from_millis(1000);

        let mut streams = vec![];
        let mut ips_connected = vec![];
        while ips_connected.len() != remote_ips.clone().len(){
            thread::sleep(sleeptime);
            for (i,remote_ip) in remote_ips.clone().iter().enumerate(){
                if !(ips_connected.contains(&i)){
                    println!("CONNECTING TO {}",remote_ip.clone());
                    let stream = TcpStream::connect(remote_ip.clone()).await;
                    match stream{
                        Ok(stream)=> {
                            streams.push(stream);
                            println!("CONNECTED TO {}",remote_ip.clone());
                            ips_connected.push(i.clone());
                        },
                        Err(e)=> println!("{}",e.to_string()),
                    }; 
                }   
            }
        }

        let mut buffer = vec![0;1];

        buffer[0] = ready_command;

        for mut stream in streams{
            stream.write(&buffer).await?;
        }
    }

    if command == "start"{

        let pathremoteips = "/ips.txt";

        let file = OpenOptions::new().read(true).open(&pathremoteips).expect("file not found");
    
        let reader = BufReader::new(file);
    
        let lines = reader.lines();
    
        let mut remote_ips = vec![];
    
        for line in lines{
            remote_ips.push(line.unwrap());
        }


        let sleeptime = time::Duration::from_millis(1000);

        let mut streams = vec![];
        let mut ips_connected = vec![];
        while ips_connected.len() != remote_ips.clone().len(){
            thread::sleep(sleeptime);
            for (i,remote_ip) in remote_ips.clone().iter().enumerate(){
                if !(ips_connected.contains(&i)){
                    //print_message(format!("CONNECTING TO {}",remote_ip.clone()));
                    let stream = TcpStream::connect(remote_ip.clone()).await;
                    match stream{
                        Ok(stream)=> {
                            streams.push(stream);
                            //print_message(format!("CONNECTED TO {}",remote_ip.clone()));
                            ips_connected.push(i.clone());
                        },
                        Err(e)=> println!("{}",e.to_string()),
                    }; 
                }   
            }
        }

        let mut buffer = vec![0;1];

        buffer[0] = start_command;

        for mut stream in streams{
            stream.write(&buffer).await?;
        }
    }

    if command == "stop"{

        let pathremoteips = "/ips.txt";

        let file = OpenOptions::new().read(true).open(&pathremoteips).expect("file not found");
    
        let reader = BufReader::new(file);
    
        let lines = reader.lines();
    
        let mut remote_ips = vec![];
    
        for line in lines{
            remote_ips.push(line.unwrap());
        }


        let sleeptime = time::Duration::from_millis(1000);

        let mut streams = vec![];
        let mut ips_connected = vec![];
        while ips_connected.len() != remote_ips.clone().len(){
            thread::sleep(sleeptime);
            for (i,remote_ip) in remote_ips.clone().iter().enumerate(){
                if !(ips_connected.contains(&i)){
                    print_message("controller".to_string(),format!("CONNECTING TO {}",remote_ip.clone()));
                    let stream = TcpStream::connect(remote_ip.clone()).await;
                    match stream{
                        Ok(stream)=> {
                            streams.push(stream);
                            print_message("controller".to_string(),format!("CONNECTED TO {}",remote_ip.clone()));
                            ips_connected.push(i.clone());
                        },
                        Err(e)=> println!("{}",e.to_string()),
                    }; 
                }   
            }
        }

        let mut buffer = vec![0;1];

        buffer[0] = shutdown_command;

        for mut stream in streams{
            print_message("controller".to_string(),"Wrote to stream".to_string());
            stream.write(&buffer).await?;
        }
    }

    Ok(())
}
