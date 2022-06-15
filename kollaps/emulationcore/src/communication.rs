use std::sync::{Arc, Mutex};
use std::fs::OpenOptions;
use std::io::prelude::*;
use std::fs::File;
use std::ffi::CString;
use crate::state::{State};
use std::thread;
// use crate::aux::{print_message};

struct Message{
    //content has first entry number of flows, then the info of each flow[bw,len(link),linkid1,linkid2,...]
    content: Vec<u8>,
    index: usize,
}

impl Message{
    fn add_flow_count_u8(&mut self){
        self.content[0] += 1;
    }
    
    fn add_flow_count_u16(&mut self){
        let current_flow = self.get_uint16(0);
        let new_flows = current_flow + 1;
        self.put_uint16(0,new_flows as u16);
    }
    fn addindex(&mut self,value:usize){
        self.index += value;
    }
    
    fn put_uint8(&mut self,index:usize,value:u16){
    
        self.content[index] = value as u8;
    }
    
    fn put_uint16(&mut self,index:usize,value:u16){
    
        self.content[index] = ((value >> 0) & 0xff) as u8;
        self.content[index+1] = ((value >> 8) & 0xff) as u8;
    }
    
    
    fn put_uint32(&mut self,index:usize,value:u32){
    
        self.content[index] = ((value >> 0) & 0xff) as u8;
        self.content[index+1] = ((value >> 8) & 0xff)  as u8;
        self.content[index+2] = ((value >> 16) & 0xff) as u8;
        self.content[index+3] = ((value >> 24)& 0xff) as u8;
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
    
    fn get_uint16(&mut self,index:usize) -> u16{
        return (u16::from(self.content[index+1]) << 8) | (u16::from(self.content[index])) ;
    
    }
    
    
    // fn get_uint32(&mut self,index:usize) -> u32{
    
    //     return (u32::from(self.content[index+3]) << 24) | 
    //             (u32::from(self.content[index+2]) << 16) | 
    //             (u32::from(self.content[index+1]) << 8)  |
    //             (u32::from(self.content[index])) ;
    // }

}

pub struct Communication{
    pub id:String,
    pub ip:u32,
    writepipe:Option<File>,
    readpipe:Arc<Mutex<Option<File>>>,
    message:Message,
    containerlimit:u32,
}

impl Communication{
    pub fn new(id:String) -> Communication{

        Communication{
            id:id.clone(),
            ip:0,
            writepipe:None,
            message:Message{
                content:vec![],
                index:0
            },
            containerlimit:0,
            readpipe:Arc::new(Mutex::new(None))
            
        }
    }

    pub fn init(&mut self){

        let pathwrite = "/tmp/pipewrite";
        let pathread = "/tmp/piperead";


        let pathread = format!("{}{}",pathread ,self.id.to_string());


        let filename = CString::new(pathread.clone()).unwrap();
            unsafe {
                libc::mkfifo(filename.as_ptr(), 0o644);
            }

        
        let pathwrite = format!("{}{}",pathwrite,self.id.to_string());


        let filename = CString::new(pathwrite.clone()).unwrap();
        unsafe {
            libc::mkfifo(filename.as_ptr(), 0o644);
        }

        let readpipe = Some(OpenOptions::new().read(true).open(pathread).expect("file not found"));

        self.readpipe = Arc::new(Mutex::new(readpipe));

        self.writepipe = Some(OpenOptions::new().write(true).open(pathwrite).expect("file not found"));

    }

    pub fn start_polling(&mut self,state:Arc<Mutex<State>>,linkcount:u32){

        self.message.content.resize(512,0);
        if linkcount <= 255{
            self.containerlimit = 8
        }
        else{
            self.containerlimit = 16
        }

        if self.containerlimit == 8{
            self.message.content[0] = 0;
            self.message.index = 1;
        }
        else{
            self.message.put_uint16(0,0);
            self.message.index = 2;
        }

        //start the thread that will read from CommunicationManager
        if linkcount <= 255{
            start_polling_u8(state.clone(),self.readpipe.clone());
        }else{
            start_polling_u16(state.clone(),self.readpipe.clone());
        }
    }

    //Add a flow to the message
    pub fn add_flow_u8(&mut self, bandwidth:u32,total_links:u16,list:Vec<u16>){

        //add bandwidth to message
        self.message.put_uint32(self.message.index,bandwidth);
        self.message.addindex(4);

        //add number of links
        self.message.put_uint8(self.message.index,total_links);

        self.message.addindex(1);

        //add the id of each links
        for id in list {
            self.message.put_uint8(self.message.index,id);
            self.message.addindex(1);
        }
        
        //increment number of flows
        self.message.add_flow_count_u8();
    
       
    }

    pub fn add_flow_u16(&mut self,bandwidth:u32,total_links:u16,list:Vec<u16>){

        //add bandwidth to message
        self.message.put_uint32(self.message.index,bandwidth);
        self.message.addindex(4);

        //add number of links
        self.message.put_uint16(self.message.index,total_links);
        self.message.addindex(2);


        //add the id of each links
        for id in list {
            self.message.put_uint16(self.message.index,id);
            self.message.addindex(2);
        }

        //increment number of flows
        self.message.add_flow_count_u16();
    
    
    }

    //Writes to the pipe
    pub fn flush(&mut self){

        self.writepipe.as_ref().unwrap().write_all(&self.message.content).map_err(|err| println!("ERROR in EM writing with container id {} {:?}",self.id, err)).ok();
        
        //reset message
        if self.containerlimit == 8{
            self.message.content[0] = 0;
            self.message.index = 1;
        }
        else{
            self.message.put_uint16(0,0);
            self.message.index = 2;
        }



    }



}

fn start_polling_u8(state:Arc<Mutex<State>>,readpipe:Arc<Mutex<Option<File>>>){

    //buffer to hold data
    let _handle = thread::spawn(move || {
    let mut receive_buffer = vec![0;512];
        loop{
            readpipe.lock().unwrap().as_ref().unwrap().read(&mut receive_buffer).map_err(|err| println!("{:?}", err)).ok();

            let mut recv_ptr = 0;


            let flow_count = receive_buffer[recv_ptr];
            recv_ptr += 1;

            //0 flows means the other node left, might be useful for later
            if flow_count == 0{


            }else{
                for _f in 0..flow_count {

                    let mut ids = Vec::new();
        
                    let bandwidth = get_uint32(&receive_buffer,recv_ptr);
                    recv_ptr += 4;
        
                    let link_count = receive_buffer[recv_ptr] as usize;
                    recv_ptr += 1;
                    
                    for _l in 0..link_count {
                        ids.push(receive_buffer[recv_ptr]);
                        recv_ptr+=1;
                    }
        
                    callreceive_flow_u8(state.clone(),bandwidth,link_count,ids);
        
                }
            }

        }
    
    });
    

}


//same as u8 but for u16
fn start_polling_u16(state:Arc<Mutex<State>>,readpipe:Arc<Mutex<Option<File>>>){

    let _handle = thread::spawn(move || {
    //buffer to hold data
    let mut receive_buffer = vec![0;512];

        loop{
            readpipe.lock().unwrap().as_ref().unwrap().read(&mut receive_buffer).map_err(|err| println!("{:?}", err)).ok();

            let mut recv_ptr = 0;


            let flow_count = get_uint16(&receive_buffer,recv_ptr);
            
                //0 flows means the other node left, might be useful for later
            if flow_count == 0{

    
            }
            else{
                recv_ptr += 2;
                for _f in 0..flow_count {

                    let mut ids = Vec::new();
    
                    let bandwidth = get_uint32(&receive_buffer,recv_ptr);
                    recv_ptr += 4;
    
                    let link_count = get_uint16(&receive_buffer,recv_ptr) as usize;
                    recv_ptr += 2;
    
                    for _l in 0..link_count {
                        ids.push(get_uint16(&receive_buffer,recv_ptr));
                        recv_ptr+=2;
                    }
    
                    callreceive_flow_16(state.clone(),bandwidth,link_count,ids);
    
                }
            }
        }
        
    });

}


fn get_uint16(buffer:&Vec<u8>,index:usize) -> u16{
    return (u16::from(buffer[index+1]) << 8) | (u16::from(buffer[index])) ;

}


fn get_uint32(buffer:&Vec<u8>,index:usize) -> u32{

    return (u32::from(buffer[index+3]) << 24) | 
            (u32::from(buffer[index+2]) << 16) | 
            (u32::from(buffer[index+1]) << 8)  |
            (u32::from(buffer[index])) ;
}

fn callreceive_flow_u8(state:Arc<Mutex<State>>,bandwidth:u32,link_count:usize,ids:Vec<u8>){

    let mut unlocked_state = state.lock().unwrap();
    unlocked_state.get_current_graph().lock().unwrap().collect_flow_u8(bandwidth as f32,link_count,ids.clone());

}

fn callreceive_flow_16(state:Arc<Mutex<State>>,bandwidth:u32,link_count:usize,ids:Vec<u16>){

    let mut unlocked_state = state.lock().unwrap();
    unlocked_state.get_current_graph().lock().unwrap().collect_flow_u16(bandwidth as f32,link_count,ids.clone());
}