use std::fs::OpenOptions;
use std::io::prelude::*; 
use std::thread;
use std::env;
use async_std::prelude::*;
use async_std::task;
use async_std::task::block_on;
use async_std::net::{TcpStream,TcpListener};
use crossbeam_channel::{unbounded, Sender,Receiver};
use std::net::Shutdown;
use std::os::unix::io::{AsRawFd};
use std::{time};
use std::collections::HashMap;
type Result<T> = std::result::Result<T, Box<dyn std::error::Error + Send + Sync>>;
mod select;
use crate::select::{FdSet,select};
mod aux;
use crate::aux::{print_message,has_dashboard,retrieve_local_ids,retrieve_remote_ips,get_containers,clone_pipes,wait_for_pipe_creation,get_uint16,put_uint16};

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

    let setup = setup(remote_ips.clone(),containercount,addr.clone());

    task::block_on(setup).map_err(|err| println!("{:?}", err)).ok();

    let local_ids = retrieve_local_ids();

    let has_dashboard = has_dashboard();
    
    let remote_ips = retrieve_remote_ips(":8081".to_string());

    print_message(format!("{:?}",local_ids)).expect("Couldn't add to file");
    print_message(format!("{:?}",remote_ips)).expect("Couldn't add to file");

    //wait for EM's to create pipes
    wait_for_pipe_creation(local_ids.clone(),"/tmp/piperead".to_string());

    wait_for_pipe_creation(local_ids.clone(),"/tmp/pipewrite".to_string());

    //start exchanging of information
    block_on(start(addr,local_ids,remote_ips,has_dashboard)).map_err(|err| println!("{:?}", err)).ok();


    Ok(())

}

/**********************************************************************************************
*       setup
**********************************************************************************************/

//exchanges information with other machines to assure all machines started their containers
async fn setup(remote_ips:Vec<String>,containercount:usize,addr:String)-> Result<()>{
    print_message(format!("SETUP STARTED container count is {}",containercount.to_string())).expect("Couldn't add to file");

    let mut channelvecsender = vec![];
    let mut channelvecreceiver = vec![];

    for _remote_ip in remote_ips.clone(){
        let (sender, receiver) = unbounded();
        channelvecsender.push(sender);
        channelvecreceiver.push(receiver);
    }

    //check if there are remote ips, if yes create an accept loop to accept connections
    if remote_ips.len() !=0{
        let accept_setup_loop = accept_setup_loop(addr.clone(),channelvecsender.clone(),remote_ips.len().clone());
        task::spawn(accept_setup_loop);
    }

    let sleeptime = time::Duration::from_millis(1000);

    thread::sleep(sleeptime);

    //connect to other machines
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

    task::block_on(wait_until_containers_start(streams,containercount,channelvecreceiver.clone())).map_err(|err| println!("{:?}", err)).ok();

    print_message("SETUP ENDED".to_string()).expect("Couldn't add to file");

    Ok(())
}

//exchange number of containers started with other machines
async fn wait_until_containers_start(streams:Vec<TcpStream>,containercount:usize,channelvecreceiver:Vec<Receiver<u16>>) -> Result<()>{

    print_message("WAITING FOR CONTAINERS TO START".to_string()).expect("Couldn't add to file");
    
    loop{

        //message
        let buffer = vec![0;2];

        //curent number of IDS
        let local_ids = retrieve_local_ids();

        let containers_responsible = local_ids.len();

        let mut buffer = put_uint16(buffer,0,containers_responsible as u32);

        //send to other machines
        for mut stream in &streams{
            stream.write(&buffer).await?;
        }

        //receives from other threads(other machines)
        let mut count = 0;
        let mut receiver_count = 0;
        for receiver in &channelvecreceiver{
            let received = receiver.recv().unwrap() as usize;
            receiver_count = receiver_count +1;
            count = count + received;
            print_message(format!("received is {} from {} and local_ids is {}",received.to_string(),receiver_count.to_string(),local_ids.len())).expect("Couldn't add to file");
        }

        //check if all machines started if yes, send message to end the setup
        //print_message(format!("local ids count is {}",local_ids.len()));
        if count + local_ids.len() == containercount as usize{
            buffer.push(1);
            for mut stream in &streams{
                stream.write(&buffer).await?;
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
async fn accept_setup_loop(addr:String,sender: Vec<Sender<u16>>,number_of_remotes:usize) -> Result<()>{

    let addr = format!("{}{}",addr,":8080");
    print_message(format!("ACCEPT_SETUP_LOOP STARTED on {}",addr.to_string())).expect("Couldn't add to file");
    let listener = TcpListener::bind(addr.clone()).await?;

    let mut incoming = listener.incoming();

    let mut remotecount = 0;
    while let Some(stream) = incoming.next().await{
        let stream = stream?;
        let peer_addr = stream.peer_addr()?;
        task::spawn(receive_container_count(stream,peer_addr.to_string().clone(),sender[remotecount].clone()));
        remotecount+=1;

        if remotecount == number_of_remotes{
            break;
        }

    }
    print_message(format!("ACCEPT_SETUP_LOOP ENDED ")).expect("Couldn't add to file");

    Ok(())
}

//reads from the other hosts how many containers they started
async fn receive_container_count(mut stream:TcpStream,_peer:String,sender:Sender<u16>){
    loop{
        let mut buffer = [0; 3];
        
        let _n = match stream.read(&mut buffer).await{
            Ok(n) if n == 0 => return,
            Ok(n) => n,
            Err(e) => {
                eprintln!("failed to read from socket; err = {:?}", e);
                return;
            }
        };
        
        //end of loop message
        if buffer[2] == 1{
            let containers = get_uint16(buffer,0);
            sender.send(containers).map_err(|err| println!("{:?}", err)).ok();
            break;
        }
        let containers = get_uint16(buffer,0);
        sender.send(containers).map_err(|err| println!("{:?}", err)).ok();

    }

}

/**********************************************************************************************
*       start of exchange mechanisms
**********************************************************************************************/

//starts the exchange of  metadata
async fn start(addr:String,local_ids:Vec<String>,remote_ips:Vec<String>,has_dashboard:bool)-> Result<()>{

    print_message("ENTERED START".to_string()).expect("Couldn't add to file");

    //Start accept loop that will start threads to receive metadata from other hosts
    if remote_ips.len() != 0{
        let accept_loop = accept_loop(remote_ips.len().clone(),addr,local_ids.clone());
        task::spawn(accept_loop);
    }

    let sleeptime = time::Duration::from_millis(1000);
    thread::sleep(sleeptime);

    start_message_exchange(local_ids.clone(),remote_ips.clone(),has_dashboard).await?;

    
    Ok(())
}




/**********************************************************************************************
*       start of information exchange
**********************************************************************************************/

async fn start_message_exchange(vector_ids:Vec<String>,remote_ips:Vec<String>,dashboard:bool)-> Result<()>{

    print_message("STARTED MESSAGE EXCHANGE".to_string()).expect("Couldn't add to file");

    //hold pipes to read from
    let mut pipes_read = vec![];

    //position of pipe in vector (key-> fd_raw,value-> position)
    let mut pipes_position = HashMap::new();
    let pathwrite = "/tmp/pipewrite";

    //hold pipes to write to (we want to write to information every container but ourselfs so we create a vector for each container that containers every pipe but the pipe to themselfs)
    let mut vector_pipes_id = vec![];
 
    let containers = get_containers(vector_ids.clone(),"/tmp/piperead".to_string());


    for i in 0..vector_ids.clone().len(){

        //open pipe
        let path = format!("{}{}",pathwrite,vector_ids[i]);
        let file = OpenOptions::new().read(true).open(&path).expect("file not found");

        //insert in hashmap
        pipes_position.insert(file.as_raw_fd(),i);
        //insert in vector
        pipes_read.push(file);

        //containers every pipe but the one respective to vectorids[i]
        let pipes = clone_pipes(vector_ids[i].clone(),containers.clone());

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
                let stream = TcpStream::connect(remote_ip.clone()).await;
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
        let fd = pipe.as_raw_fd();
        max = fd.max(max);
    }
    
    let mut fd_set = FdSet::new();
    let mut vector_fd = vec![];
    for pipe in &pipes_read{
        let fd = pipe.as_raw_fd();
        print_message(format!("FD is {}",fd.to_string())).expect("Couldn't add to file");
        fd_set.set(fd);
        vector_fd.push(fd);
        max = fd.max(max);
    }
    print_message("STARTED EXCHANGE ALL SET".to_string()).expect("Couldn't add to file");
    //let mut read = 0;
    //let mut wrote = 0;
    loop{
        let mut buffer = [0; 512];
        match select(
            max + 1,
            Some(&mut fd_set),                               // read
            None,                                            // write
            None,                                            // error
            None,) // timeout
            {
            Ok(_res) => {
                for i in vector_fd.clone() {

                    if (fd_set).is_set(i) {

                        //get position of pipe in vector of pipes with fd value i
                        let position = pipes_position.get(&i);

                        //read from ipe
                        pipes_read[*position.unwrap()].read(&mut buffer).map_err(|err| print_message(format!("{:?}", err)).expect("Couldn't add to file")).ok();
                        //read = read + 1;
                        //write to vector that contains every pipe but the container it read from
                        for pipe in &vector_pipes_id[*position.unwrap()]{
                            {
                                pipe.lock().unwrap().write(&buffer);
                            }
                            //wrote = wrote + 1;
                        }
                        //write to remote hosts
                        for mut stream in &streams{
                            let _n = stream.write_all(&buffer).await?;
                        }
        
                        fd_set.set(i);
                    }
                    fd_set.set(i);
                }
                //print_message(format!("Wrote {} and read {} ",wrote,read));
    
            }
            Err(err) => {
                println!("Failed to select: {:?}", err);
            }
        }
    }
}

//receives metadata from other hosts
async fn remote_producer(mut stream:TcpStream,local_ids:Vec<String>) {

    print_message("STARTED REMOTE PRODUCER".to_string()).expect("Couldn't add to file");    
    //buffer to hold data
    let mut buffer = [0; 512];
    //let mut count = 0;
    let containers = get_containers(local_ids.clone(),"/tmp/piperead".to_string());
        loop{
            let _n = match stream.read(&mut buffer).await {
                //Socket closed
                Ok(n) if n == 0 => return,
                Ok(n) => n,
                Err(e) => {
                    eprintln!("failed to read from socket; err = {:?}", e);
                    return;
                }
            };

            for pipe in &containers{
                {
                    pipe.lock().unwrap().write(&buffer);
                }
            }
        }

    
}

//accepts connections from other hosts
async fn accept_loop(count:usize,addr:String,local_ids:Vec<String>) -> Result<()>{

    //Bind the socket to the process

    let addr = format!("{}{}",addr,":8081");
    print_message(format!("Listening on: {}",addr)).expect("Couldn't add to file");

    let listener = TcpListener::bind(addr).await?;

    let mut incoming = listener.incoming();

    let mut peers = 0;
    while let Some(stream) = incoming.next().await{

        let stream = stream?;
        let peer_addr = stream.peer_addr()?;
        
        println!("PEER IS : {}",peer_addr);

        //Start remote producer
        task::spawn(remote_producer(stream,local_ids.clone()));

        peers+=1;
        
        if peers == count{
            break;
        }

    }
    print_message(format!("ACCEPT_LOOP ENDED ")).expect("Couldn't add to file");


    Ok(())

}




