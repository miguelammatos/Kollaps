use libloading::{Library, Symbol};

//Interacts with TC library
pub struct Emulation{
    library:Library,

}

impl Emulation{

    pub fn new()-> Emulation{
        unsafe{
            Emulation{
                library:Library::new("/usr/local/bin/libTCAL.so").unwrap(),
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
        unsafe{
            let changebw: Symbol< unsafe extern fn(u32,u32)> = self.library.get(b"changeBandwidth").unwrap();
            changebw(ip,bandwidth/1000);
        }
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