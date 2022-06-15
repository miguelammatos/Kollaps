use std::fs::OpenOptions;
use std::io::prelude::*; 
use std::thread;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::net::Ipv4Addr;
use std::path::Path;
use std::{time};
use std::sync::{Arc, Mutex};
type Result<T> = std::result::Result<T, Box<dyn std::error::Error + Send + Sync>>;

pub struct Container{
    pipe: File,
    id_container: String,
    //ip_small:u32,
    //ip_big:u32,
}

impl Container{

    pub fn write(&mut self,content:&[u8]){
        self.pipe.write_all(&content).map_err(|err| print_message(format!("{:?}", err))).ok();
    }
}

/**********************************************************************************************
*       auxiliar functions
**********************************************************************************************/


//retrieves the containers ids from topoinfo
pub fn retrieve_local_ids() -> Vec<String>{
    let sleeptime = time::Duration::from_millis(1000);

    while !(Path::new("/tmp/topoinfo").exists()) || !(Path::new("/tmp/topoinfodashboard").exists()){
        thread::sleep(sleeptime);
        continue;
    }


    thread::sleep(sleeptime);

    let pathtopoinfo = "/tmp/topoinfo";

    let mut local_ids = vec![];

    let file = OpenOptions::new().read(true).open(&pathtopoinfo).expect("file not found");

    let reader = BufReader::new(file);

    let lines = reader.lines();

    for line in lines{
        local_ids.push(line.unwrap());
    }

    let pathtopoinfodashboard = "/tmp/topoinfodashboard";

    let file = OpenOptions::new().read(true).open(&pathtopoinfodashboard).expect("file not found");

    let reader = BufReader::new(file);

    let lines = reader.lines();

    for line in lines{
        local_ids.push(line.unwrap());
    }

    return local_ids;

}

//checks if the host contains the dashboard container
pub fn has_dashboard() -> bool{

    let pathtopoinfodashboard = "/tmp/topoinfodashboard";

    let mut local_ids = vec![];

    let file = OpenOptions::new().read(true).open(&pathtopoinfodashboard).expect("file not found");

    let reader = BufReader::new(file);

    let lines = reader.lines();

    for line in lines{
        local_ids.push(line.unwrap());
    }

    return local_ids.len() != 0;

}

//retrieves the ips of the other hosts in the deployment
pub fn retrieve_remote_ips(port:String) -> Vec<String>{

    while !(Path::new("/remote_ips.txt").exists()){
        continue;
    }

    let pathremoteips = "/remote_ips.txt";

    let file = OpenOptions::new().read(true).open(&pathremoteips).expect("file not found");

    let reader = BufReader::new(file);

    let lines = reader.lines();

    let mut remote_ips = vec![];

    for line in lines{
        let ip = format!("{}{}",int_to_ip(line.unwrap()),port);
        remote_ips.push(ip);
    }

    return  remote_ips;
    
}

//blocks until all pipe files are created
pub fn wait_for_pipe_creation(local_ids:Vec<String>,path:String){

    let mut count;
    loop{
        count = 0;
        for id in local_ids.clone(){
            let path = format!("{}{}",path,id.to_string());
            //print_message(format!("I am checking if this path exists {}",path.clone()));
            let state = Path::new(&path).exists();

            if state{
                count +=1;
            }
    
        }

        if count == local_ids.clone().len(){
            break;
        }

        let sleeptime = time::Duration::from_millis(5000);

        thread::sleep(sleeptime);
    }


}
 

//receives the ids and creates a structure with all the pipes to read from
pub fn get_containers(local_ids:Vec<String>,pathread:String) -> Vec<Arc<Mutex<Container>>>{

    print_message("Started getting pipes".to_string()).expect("Couldn't add to file");

    let mut containers = vec![];

    for id in local_ids.clone(){
        let path = format!("{}{}",pathread,id.to_string());
        let file = OpenOptions::new().write(true).open(&path).expect("file not found");
        
        let container = Container{
            pipe: file,
            id_container: id,
            //ip_small:0,
            //ip_big:0,

        };

        let container = Arc::new(Mutex::new(container));

        containers.push(container);

    }

    print_message("Got pipes".to_string()).expect("Couldn't add to file");

    return containers;

}

//clones the structure containining the pipes to read from
pub fn clone_pipes(id:String,vector_pipes_write:Vec<Arc<Mutex<Container>>>) -> Vec<Arc<Mutex<Container>>>{

    let mut pipes = vec![];

    for pipe in vector_pipes_write{
        if id == pipe.lock().unwrap().id_container{
           continue;
        }
        pipes.push(Arc::clone(&pipe));
    }

    return pipes;
}


fn int_to_ip(intip:String) -> String{

    let intip = intip.parse::<u32>().unwrap();
    
    let mut vector = [0;4];
    for i in 0..vector.len(){
        vector[3 - i] = (intip >> (i * 8)) as u8;
    }


    return Ipv4Addr::new(vector[0],vector[1],vector[2],vector[3]).to_string();
}


pub fn put_uint16(mut message:Vec<u8>,index:usize,value:u32) -> Vec<u8>{

    message[index] = ((value >> 0) & 0xff) as u8;
    message[index+1] = ((value >> 8) & 0xff) as u8;

    return message;
}

pub fn get_uint16(buffer:[u8;3],index:usize) -> u16{
    return (u16::from(buffer[index+1]) << 8) | (u16::from(buffer[index])) ;

}


/**********************************************************************************************
*       print
**********************************************************************************************/

pub fn print_message(message:String) -> Result<()>{
    let message = format!("RUST GOD: {} \n",message);
    //println!("{}",message);
    let mut file = OpenOptions::new()
    .write(true)
    .create(true)
    .append(true)
    .open("/logs.txt")
    .unwrap();
    file.write_all(message.as_bytes()).expect("Unable to write data");
    Ok(())
}
