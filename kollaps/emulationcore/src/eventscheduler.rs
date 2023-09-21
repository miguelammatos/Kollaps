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

use crate::state::State;
use std::sync::Mutex;
use std::sync::Arc;
use std::time::Instant;
use std::time::Duration;
use std::thread;
use crate::docker::start_experiment;
use crate::docker::stop_experiment;
use tokio::runtime::Handle;
use crate::aux::{start_script,print_message};

pub struct EventScheduler{
    pub events:Vec<Event>,
    pub state:Arc<Mutex<State>>,
    pub timebetweenevents:Vec<f32>,
    pub pid:u32,
    pub tokiohandler:Option<Handle>,
    orchestrator:String,
    pub script:String,
    pub name:String

}

impl EventScheduler{
    pub fn new(state:Arc<Mutex<State>>,orchestrator:String) -> EventScheduler{
        EventScheduler{
            events:vec![],
            name:"".to_string(),
            state:state,
            timebetweenevents:vec![],
            pid:0,
            tokiohandler:None,
            orchestrator,
            script:"".to_string()
        }
    }

    pub fn schedule_join(&mut self,time:f32){

        let event = Event::new(0,time);

        self.events.push(event);
    }

    
    pub fn schedule_leave(&mut self,time:f32){

        let event = Event::new(2,time);
        self.events.push(event);
    }
    
    
    pub fn schedule_crash(&mut self,time:f32){
        let event = Event::new(3,time);

        self.events.push(event);
    }

    pub fn schedule_disconnect(&mut self,time:f32){

        let event = Event::new(4,time);

        self.events.push(event);
    }

    pub fn schedule_reconnect(&mut self,time:f32){

        let event = Event::new(5,time);

        self.events.push(event);
    }

    pub fn schedule_bridge_join(&mut self,time:f32,bridge_name:String){

        self.state.lock().unwrap().insert_graph();

        let bridge = self.state.lock().unwrap().get_graph().lock().unwrap().removed_bridges.get(&bridge_name).unwrap().clone();

        self.state.lock().unwrap().get_graph().lock().unwrap().bridges_by_name.insert(bridge_name.clone(),bridge.clone());

        //if it already existed remove it from removed_bridges
        self.state.lock().unwrap().get_graph().lock().unwrap().removed_bridges.remove(&bridge_name);
        
        self.recompute_and_store();

        let event = Event::new(1,time);
        
        self.events.push(event);
    }


    pub fn schedule_bridge_leave(&mut self,time:f32,bridge_name:String){

        self.state.lock().unwrap().insert_graph();

        let bridges = self.state.lock().unwrap().get_graph().lock().unwrap().bridges_by_name.get(&bridge_name).unwrap().clone();

        //insert in removed_bridges
        self.state.lock().unwrap().get_graph().lock().unwrap().removed_bridges.insert(bridge_name.clone(),bridges);

        //remove from bridges_by_name
        self.state.lock().unwrap().get_graph().lock().unwrap().bridges_by_name.remove(&bridge_name);

        self.recompute_and_store();

        let event = Event::new(1,time);

        self.events.push(event);

        
    }

    pub fn schedule_link_leave(&mut self,time:f32,origin:String,destination:String){


        self.state.lock().unwrap().insert_graph();

        let links = self.state.lock().unwrap().get_graph().lock().unwrap().links.clone();

        //get id of links with origin and destination
        let mut ids = vec![];
        for (id,link) in links.iter(){
            let source = link.lock().unwrap().source.lock().unwrap().hostname.clone();

            let dest = link.lock().unwrap().destination.lock().unwrap().hostname.clone();

            if source == origin && dest == destination{
                ids.push(id);
                self.state.lock().unwrap().get_graph().lock().unwrap().removed_links.push(link.clone());
            }

        }

        //remove them from the services and bridges
        for id in ids{
            self.state.lock().unwrap().get_graph().lock().unwrap().links.remove(id);

            let services = self.state.lock().unwrap().get_graph().lock().unwrap().services.clone();


            for (_ip,service) in services.iter(){
                service.lock().unwrap().remove_link(*id);
            }

            let bridges = self.state.lock().unwrap().get_graph().lock().unwrap().bridges.clone();


            for (_ip,bridge) in bridges.iter(){
                bridge.lock().unwrap().remove_link(*id);
            }

        }

        let event = Event::new(1,time);

        self.events.push(event);

        self.recompute_and_store();


    }

    pub fn schedule_link_join(&mut self,time:f32,origin:String,destination:String) -> bool{


        self.state.lock().unwrap().insert_graph();

        let mut joining_links = vec![];

        let removed_links = self.state.lock().unwrap().get_graph().lock().unwrap().removed_links.clone();

        let mut link_existed = false;

        //remove from removed_links and get joining links
        for (i,link) in removed_links.iter().enumerate(){

            let source = link.lock().unwrap().source.lock().unwrap().hostname.clone();

            let dest = link.lock().unwrap().destination.lock().unwrap().hostname.clone();

            if source == origin && dest == destination{
                joining_links.push(link.clone());
                self.state.lock().unwrap().get_graph().lock().unwrap().removed_links.remove(i);
                self.state.lock().unwrap().get_graph().lock().unwrap().links.insert(link.lock().unwrap().id,link.clone());
            }

        }

        //add them to services and bridges
        for link in joining_links{

            link_existed = true;

            let services = self.state.lock().unwrap().get_graph().lock().unwrap().services_by_name.clone();
            let source = link.lock().unwrap().source.lock().unwrap().hostname.clone();
            for (name,services) in services.iter(){
                if source == *name{
                    for service in services{
                        service.lock().unwrap().attach_link(link.lock().unwrap().id);
                    }
                }
            }
            let bridges = self.state.lock().unwrap().get_graph().lock().unwrap().bridges_by_name.clone();

            for (name,bridges) in bridges.iter(){
                if source == *name{
                    for bridge in bridges{
                        bridge.lock().unwrap().attach_link(link.lock().unwrap().id);
                    }
                }
            }
        }

        let event = Event::new(1,time);

        self.events.push(event);

        self.recompute_and_store();

        

        return link_existed;
    }

    pub fn schedule_new_link(&mut self,time:f32,origin:String,destination:String,latency:f32,jitter:f32,drop:f32,bandwidth:f32){
        
        self.state.lock().unwrap().insert_graph();

        self.state.lock().unwrap().get_graph().lock().unwrap().insert_link(latency,jitter,drop,bandwidth,origin,destination);
   
        let event = Event::new(1,time);

        self.events.push(event);
        
        self.recompute_and_store();
    }

    pub fn schedule_link_change(&mut self,time:f32,origin:String,destination:String,latency:f32,jitter:f32,drop:f32,bandwidth:f32){
    
        self.state.lock().unwrap().insert_graph();

        for (_id,link) in self.state.lock().unwrap().get_graph().lock().unwrap().links.iter_mut(){
            let link_origin = link.lock().unwrap().source.lock().unwrap().hostname.clone();
            let link_dest = link.lock().unwrap().destination.lock().unwrap().hostname.clone();

            if origin == link_origin && link_dest == destination{
                if bandwidth >= 0.0{
                    link.lock().unwrap().bandwidth = bandwidth;
                }
                if latency >= 0.0{
                    link.lock().unwrap().latency= latency;
                }
                if jitter >= 0.0{
                    link.lock().unwrap().jitter = jitter;
                }
                if drop >= 0.0{
                    link.lock().unwrap().drop = drop;
                }

                //print_message(self.name.clone(),format!("origin is {} and dest is {} and new latency is {}",origin,destination,latency).to_string());
            }

        }
   
        let event = Event::new(1,time);

        self.events.push(event);
        
        self.recompute_and_store();
    }



    pub fn recompute_and_store(&mut self){

        self.state.lock().unwrap().get_graph().lock().unwrap().calculate_shortest_paths();

        self.state.lock().unwrap().get_graph().lock().unwrap().calculate_properties();
        
    }

    // pub fn print_events(&mut self){
    //     for event in self.events.iter(){
    //         println!("id {} and time {}", event.id,event.time);
    //     }
    // }

    pub fn start(&mut self){
        println!("Started experiment");
        let now = Instant::now();
        let mut count = 0;

        //self.print_events();

        loop{   
            if now.elapsed().as_millis() >= (self.events[count].time * 1000.0) as u128{
                if self.events[count].id == 0{

                    let id = self.state.lock().unwrap().id.clone();

                    if self.orchestrator == "baremetal"{

                        if self.script != ""{
                            println!("STARTED SCRIPT WITH NAME {}",self.script.clone());
                            start_script(self.script.clone());
                        }
                    }
                    else{
                        self.tokiohandler.as_ref().unwrap().spawn(async move{start_experiment(id).await});
                        print_message(self.name.clone(), "Started my script".to_string());
                    }
                    //task::spawn(start_experiment(self.state.lock().unwrap().id.clone()));
                }

                if self.events[count].id == 3{
                    stop_experiment(self.pid.clone());
                }
                if self.events[count].id == 2{
                    //This is not properly implemented since 1.0
                    //self.state.lock().unwrap().increment_age();
                }
                if self.events[count].id == 1{
                    self.state.lock().unwrap().increment_age();
                }

                if self.events[count].id == 4{
                    self.state.lock().unwrap().emulation.lock().unwrap().disconnect();
                }

                if self.events[count].id == 5{
                    self.state.lock().unwrap().emulation.lock().unwrap().reconnect();
                }
                if count == self.events.len() - 1{
                    println!("BROKE OUT");
                    break;
                }
                count = count +1;
                
            }
            thread::sleep(Duration::from_secs_f32(0.5));
        }

    }

    pub fn sort_events(&mut self){
        self.events.sort_by(|a, b| a.time.partial_cmp(&b.time).unwrap());
    }
}

pub struct Event{   
    pub id:u32,
    pub time:f32
}

impl Event{
    pub fn new(id:u32,time:f32) -> Event{
        Event{
            id:id,
            time:time
        }
    }
}