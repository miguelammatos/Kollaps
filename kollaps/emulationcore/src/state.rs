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

use std::sync::{Arc, Mutex};
use crate::graph::{Graph};
use crate::elements::{Link,Path,Flowu8,Flowu16};
use crate::emulation::{Emulation};
use std::io::Result;
use crate::aux::{print_message};

//Represents the State of the Emulation
pub struct State{
    pub age: usize, //Age represents which graph we currently have, a dynamic event that changes paths represent a new age
    pub graphs: Vec<Arc<Mutex<Graph>>>, //Vector containing the precomputed graphs
    pub graph_counter: usize, //auxiliary value with the number of graphs
    pub active_paths:Vec<Arc<Mutex<Path>>>, //paths that this container sent bytes to
    pub active_paths_ids:Vec<u32>,
    pub name:String,
    pub emulation:Arc<Mutex<Emulation>>, //object that handles TC
    pub id:String,
    pub link_count:u32,


}


impl State {
    pub fn new(id:String) -> State {
        State {
            age: 0,
            graphs: vec![],
            graph_counter:0,
            active_paths:vec![],
            active_paths_ids:vec![],
            name:"".to_string(),
            emulation: Arc::new(Mutex::new(Emulation::new())),
            id:id,
            link_count:0,

        }
    }

    //Here we setup the TC qdisc to emulate the network state
    pub fn init(&mut self,ip:u32) -> Result<()> {

        self.emulation.lock().unwrap().init(ip);

        let ips = self.get_current_graph().lock().unwrap().ip_to_path_id.clone();
        
        let activepaths = self.get_current_graph().lock().unwrap().graph_root.as_ref().unwrap().lock().unwrap().activepaths.clone();

        let mut opened_paths = vec![];


        //If we do not have active paths we do not know which paths need to be shaped so we shape all
        if activepaths.len() == 0{
            let mut paths = self.get_current_graph().lock().unwrap().paths.clone();
            for (id,path) in paths.iter_mut(){

                let service_name = &path.lock().unwrap().finish.clone();

                if self.get_current_graph().lock().unwrap().bridges_by_name.contains_key(service_name){
                    continue;
                }
                let bandwidth = (path.lock().unwrap().max_bandwidth.clone() / 1000.0) as u32;
            
                let latency = path.lock().unwrap().latency.clone();
                
                let jitter = path.lock().unwrap().jitter.clone();
                
                let drop = path.lock().unwrap().drop.clone();

                let ip = self.get_current_graph().lock().unwrap().path_id_to_ip.get(id).unwrap().clone();
                if path.lock().unwrap().links.len() == 0{
                    //self.emulation.lock().unwrap().disable_path(ip);

                // else is a path to another container
                }else{
                    self.emulation.lock().unwrap().initialize_path(ip,bandwidth,latency,jitter,drop);
                    opened_paths.push(service_name.clone());
                }
        
            }

            for (ip,_id) in ips{
                if self.get_current_graph().lock().unwrap().ip_to_path_id.get(&ip).is_none(){
                    //self.emulation.lock().unwrap().disable_path(ip);   
                }
            }

            

        }
        //If we do know active paths, we only shape those paths
        else{

            let mut opened_paths = vec![];
            //opens from me to them
            for service_name in activepaths{
                let ip = self.get_current_graph().lock().unwrap().services_by_name.get(&service_name).unwrap()[0].lock().unwrap().ip;

                let path_id = self.get_current_graph().lock().unwrap().ip_to_path_id.get(&ip).unwrap().clone();

                let path = self.get_current_graph().lock().unwrap().paths.get(&path_id).unwrap().clone();

                let bandwidth = (path.lock().unwrap().max_bandwidth.clone() / 1000.0) as u32;
            
                let latency = path.lock().unwrap().latency.clone();
                
                let jitter = path.lock().unwrap().jitter.clone();
                
                let drop = path.lock().unwrap().drop.clone();

                if path.lock().unwrap().links.len() == 0{
                    //self.emulation.lock().unwrap().disable_path(ip);

                // else is a path to another container
                }else{
                    self.emulation.lock().unwrap().initialize_path(ip,bandwidth,latency,jitter,drop);
                    opened_paths.push(service_name);
                }

            }
            
            let my_name = self.get_current_graph().lock().unwrap().graph_root.as_ref().unwrap().lock().unwrap().hostname.clone();

            let services = self.get_current_graph().lock().unwrap().services.clone();
            for (ip,service) in services.iter() {

                let service_name = service.lock().unwrap().hostname.clone();

                //if we for some reason create 2 paths (qdiscs) to the same hosts then dynamic changes will not work
                if service.lock().unwrap().activepaths.contains(&my_name) && !opened_paths.contains(&service_name){
                    let path_id = self.get_current_graph().lock().unwrap().ip_to_path_id.get(&ip).unwrap().clone();

                    let path = self.get_current_graph().lock().unwrap().paths.get(&path_id).unwrap().clone();

                    let bandwidth = (path.lock().unwrap().max_bandwidth.clone() / 1000.0) as u32;
                
                    let latency = path.lock().unwrap().latency.clone();
                    
                    let jitter = path.lock().unwrap().jitter.clone();
                    
                    let drop = path.lock().unwrap().drop.clone();

                    if path.lock().unwrap().links.len() == 0{
                        //self.emulation.lock().unwrap().disable_path(*ip);

                    // else is a path to another container
                    }else{
                        self.emulation.lock().unwrap().initialize_path(*ip,bandwidth,latency,jitter,drop);
                    }
                }
            }
            
        }

        Ok(())


    }

    pub fn set_link_count(&mut self,link_count:u32){
        self.link_count = link_count;

        for graph in self.graphs.iter_mut(){
            graph.lock().unwrap().link_count = link_count
        }
    }

    //Creates and inserts an empty graph in the vector
    pub fn insert_graph(&mut self){
        let graph = Arc::new(Mutex::new(Graph::new()));
        if self.graphs.len() !=0{
            graph.lock().unwrap().create_from_graph(self.get_graph().clone());
        }
        self.graphs.push(graph);
        self.graph_counter +=1;
    }

    //Returns the graph the emulation is using
    pub fn get_current_graph(&mut self) -> Arc<Mutex<Graph>>{
        return Arc::clone(&self.graphs[self.age]);
    }

    //Returns the most recent graph we are editing (temporary only used to pass the graphs to rust)
    pub fn get_graph(&mut self) -> Arc<Mutex<Graph>>{
        return Arc::clone(&self.graphs[self.graph_counter-1]);
    }

    //Returns a graph based on age
    pub fn get_graph_with_age(&mut self,age:usize) -> Arc<Mutex<Graph>>{
        return Arc::clone(&self.graphs[age]);
    }

    pub fn shrink_maps(&mut self){
        for graph in self.graphs.iter_mut(){
            let mut graph = graph.lock().unwrap();
            {
                graph.services.shrink_to_fit();
                graph.paths.shrink_to_fit();
                graph.links.shrink_to_fit();
                graph.bridges.shrink_to_fit();
                graph.services_by_name.shrink_to_fit();
                graph.bridges_by_name.shrink_to_fit();
                graph.ip_to_path_id.shrink_to_fit();
                graph.path_id_to_ip.shrink_to_fit();
            }
        }
    }
    
    //Increments the age and updates the new structures with older emulation metadata
    pub fn increment_age(&mut self){

        print_message(self.name.clone(),"Started changing properties".to_string());
        self.path_changes();
        self.collect_old_usages();

        self.age +=1;

        //clear because we are reactive
        self.active_paths_ids.clear();

    }

    //Retrieves bandwidth values of older graph
    pub fn path_changes(&mut self){

        let age = self.age;

        //Get current ip_to_id (can be cloned just u32 values)
        let ip_to_path_ids = self.get_graph_with_age(age+1).lock().unwrap().ip_to_path_id.clone();

        //Get old ip_to_path_ids (can be cloned just u32 values)
        let old_ip_to_path_ids = self.get_graph_with_age(age).lock().unwrap().ip_to_path_id.clone();

        for (ip,id) in &old_ip_to_path_ids{
            match ip_to_path_ids.get(&ip){
                Some(new_id)=>{
                    continue;
                }None=>{
                    let root_ip = self.get_current_graph().lock().unwrap().graph_root.as_ref().unwrap().lock().unwrap().ip;
                    if root_ip == *ip{
                        continue;
                    }
                    let new_path = self.get_graph_with_age(age).lock().unwrap().get_path(*id);

                    let new_path = new_path.unwrap().clone();

                    let start = &new_path.lock().unwrap().start.clone();

                    let finish = &new_path.lock().unwrap().finish.clone();

                    if self.get_graph_with_age(age  ).lock().unwrap().bridges_by_name.contains_key(finish){
                        continue;
                    }

                    print_message(self.name.clone(),format!("Blocked path from {} to {}",start,finish));
                    self.emulation.lock().unwrap().change_loss(*ip,1.0);

                }
            }
        }

        //Iterate through the new ones
        for (ip,id) in &ip_to_path_ids{
            //If it is the connection to myself skip
            let root_ip = self.get_current_graph().lock().unwrap().graph_root.as_ref().unwrap().lock().unwrap().ip;
            if root_ip == *ip{
                continue;
            }
            //Check old ones to see if there was a path to the IP
            match old_ip_to_path_ids.get(&ip){
                
                //If there was get old bandwidth values
                Some (old_id) =>{
                    match self.get_graph_with_age(age).lock().unwrap().paths.get_mut(old_id){
                        Some(path) => {

                            let used_bandwidth = path.lock().unwrap().used_bandwidth.clone();
                            let current_bandwidth = path.lock().unwrap().current_bandwidth.clone();
                            
                            
                            let new_path = self.get_graph_with_age(age+1).lock().unwrap().get_path(*id);

                            if new_path.is_none(){
                                continue;
                            }
                            
                            let new_path = new_path.unwrap().clone();

                            let start = &new_path.lock().unwrap().start.clone();

                            let finish = &new_path.lock().unwrap().finish.clone();

                            if self.get_graph_with_age(age+1).lock().unwrap().bridges_by_name.contains_key(finish){
                                print_message(self.name.clone(),"Continued".to_string());
                                continue;
                            }
        
                            new_path.lock().unwrap().set_used_bandwidth(used_bandwidth);
        
                            new_path.lock().unwrap().set_current_bandwidth(current_bandwidth);

                            let new_latency = new_path.lock().unwrap().latency.clone();
                            let new_jitter = new_path.lock().unwrap().jitter.clone();
                            let new_loss = new_path.lock().unwrap().drop.clone();
                            print_message(self.name.clone(),format!("Changed path from {} to {} and new latency is {} and new drop is {}",start,finish,new_latency.clone(),new_loss.clone()));
                            self.emulation.lock().unwrap().change_loss(*ip,new_loss);

                            if new_latency != 0.0{
                                self.emulation.lock().unwrap().change_latency(*ip,new_latency,new_jitter);
                            }        
                        },
                        None =>{
                       }
                    }
                },
                None=>{
                    
                    let new_path = self.get_graph_with_age(age+1).lock().unwrap().get_path(*id);

                    let new_path = new_path.unwrap().clone();

                    let start = &new_path.lock().unwrap().start.clone();

                    let finish = &new_path.lock().unwrap().finish.clone();

                    if self.get_graph_with_age(age+1).lock().unwrap().bridges_by_name.contains_key(finish){
                        continue;
                    }

                    let new_latency = new_path.lock().unwrap().latency.clone();
                    let new_jitter = new_path.lock().unwrap().jitter.clone();
                    let new_loss = new_path.lock().unwrap().drop.clone();
                    print_message(self.name.clone(),format!("New path from {} to {} and new latency is {} and new drop is {}",start,finish,new_latency.clone(),new_loss.clone()));
                    self.emulation.lock().unwrap().change_loss(*ip,new_loss);

                    if new_latency != 0.0{
                        self.emulation.lock().unwrap().change_latency(*ip,new_latency,new_jitter);
                    }
                }
            };

        }
        print_message(self.name.clone(),"Done Changes".to_string());

    }
    
    //Retrieve the amount of bytes sent to services to update in the new HashMap
    pub fn collect_old_usages(&mut self){

        {
            let age = self.age;
            let services_ips = self.get_graph_with_age(age+1).lock().unwrap().ips.clone();
            for ip in services_ips{
                match self.get_graph_with_age(age).lock().unwrap().services.get(&ip){
                    Some (service_old)=>{
                        let last_bytes = service_old.lock().unwrap().last_bytes;
                        self.get_graph_with_age(age+1).lock().unwrap().set_lastbytes(&ip,last_bytes);
                    },
                    None =>{

                    }
                }
            }
        }

    }

    pub fn insert_active_path_id(&mut self,ip:u32){
        let path_id = self.get_current_graph().lock().unwrap().get_path_id_from_ip(ip).clone();

        match path_id {
            Some(id) =>{
                if id == 0{
                    return;
                }
                self.active_paths_ids.push(id);
            },
            None =>{
                return;
            }
        };


    }

    pub fn calculate_bandwidth(&mut self){
        let rtt = 0;
        let bw = 1;

        let mut active_links_ids = vec![];

        let mut ips_and_bandwidths = vec![];
        
        //add info about our flows
        
        let active_paths_ids = self.active_paths_ids.clone();

        //print_message(self.name.clone(),format!("Active paths ids size is {}",active_paths_ids.len().clone()));

        for path_id in &active_paths_ids{
            let path = self.get_path(*path_id).unwrap().clone();
            let links =  path.lock().unwrap().links.clone();
            let pathrtt = path.lock().unwrap().rtt.clone();
            let path_used_bandwidth = path.lock().unwrap().used_bandwidth.clone();

            for link_id in links{
                let link = self.get_link(link_id);
                let mut flow = vec![];
                flow.push(pathrtt);
                flow.push(path_used_bandwidth);
                link.lock().unwrap().flows.push(flow);
                active_links_ids.push(link_id);
            }
        }

        //add info about other flows
        let flow_keys = self.get_flow_keys();

        for key in flow_keys{

            if self.link_count <=255{
                self.apply_flow_u8(&key);
                let flow = self.get_flow_u8(&key);
                let link_indices = flow.lock().unwrap().link_indices.clone();

                for link_id in link_indices{
                    active_links_ids.push(link_id as u16);
                }

                flow.lock().unwrap().age = 0;
            }
            else{
                self.apply_flow_u16(&key);
                let flow = self.get_flow_u16(&key);
                let link_indices = flow.lock().unwrap().link_indices.clone();

                for link_id in link_indices{
                    active_links_ids.push(link_id as u16);
                }

                flow.lock().unwrap().age = 0;
            }
        }

        //print_message(self.name.clone(),format!("We have this many active_links_ids {}",active_links_ids.len().clone()).to_string());

        //Calculations

        for path_id in &active_paths_ids{
            let path = self.get_path(*path_id).unwrap().clone();

            let mut max_bandwidth = path.lock().unwrap().max_bandwidth.clone();

            let max_bandwidth_path = path.lock().unwrap().max_bandwidth.clone();

            let links = path.lock().unwrap().links.clone();


            for link_id in links{   
                let mut rtt_reverse_sum = 0.000;

                let link = self.get_link(link_id);
                let link_flows = &link.lock().unwrap().flows.clone();
                for flow in link_flows{
                    rtt_reverse_sum +=1.0/flow[rtt];
                }

                let mut max_bandwidth_on_link = vec![];

                //calculate our bandwidth
                let bandwidth_bps = link.lock().unwrap().bandwidth;
                let value = 1.0/link_flows[0][rtt];
                
                let max_bandwidth_element = (value / rtt_reverse_sum) * bandwidth_bps;
                //calculated our bandwidth push to vector
                max_bandwidth_on_link.push(max_bandwidth_element);

                //maximize link utilization to 100%

                let mut spare_bw = bandwidth_bps - max_bandwidth_on_link[0];

                let our_share = max_bandwidth_on_link[0]/bandwidth_bps;

                let mut hungry_usage_sum = our_share;

                for position in 1..link_flows.len(){
                    let flow = &link_flows[position];
                    //calculate bandwidth for everyone
                    let value = 1.0/flow[rtt];

                    let max_bandwidth_element = (value / rtt_reverse_sum) * bandwidth_bps;

                    max_bandwidth_on_link.push(max_bandwidth_element);
                    //check if a flow is hungry (wants more than its allocated share)
                    if flow[bw] > max_bandwidth_on_link[position]{


                        spare_bw-=max_bandwidth_on_link[position];

                        hungry_usage_sum += max_bandwidth_on_link[position] / bandwidth_bps;
                    }
                    else{

                        spare_bw-= flow[bw]
                    }

                }
                //we get a share of the spare proportional to our RTT
                let normalized_share = our_share / hungry_usage_sum;


                let maximized = max_bandwidth_on_link[0] + (normalized_share*spare_bw);

                if maximized > max_bandwidth_on_link[0]{

                    max_bandwidth_on_link[0] = maximized;
                }
                //If this link restricts us more than previously try to assume this bandwidth as the max
                if max_bandwidth_on_link[0] < max_bandwidth{
                    max_bandwidth = max_bandwidth_on_link[0];
                }
            }

            let current_bandwidth = path.lock().unwrap().current_bandwidth.clone();

            if max_bandwidth <= max_bandwidth_path && max_bandwidth != current_bandwidth{

                if max_bandwidth <= current_bandwidth{

                    path.lock().unwrap().set_current_bandwidth(max_bandwidth);

                }
                else{
                    let new_current_bandwidth = 0.75 * current_bandwidth + 0.25 * max_bandwidth;
                    path.lock().unwrap().set_current_bandwidth(new_current_bandwidth);

                }

                //get_services
                let ip = self.get_current_graph().lock().unwrap().get_ip_from_path_id(*path_id).clone();
                //call tc to change
                let new_bandwidth = path.lock().unwrap().current_bandwidth.clone();

                let mut ip_and_bandwidth = vec![];

                ip_and_bandwidth.push(ip);
                ip_and_bandwidth.push(new_bandwidth as u32);

                ips_and_bandwidths.push(ip_and_bandwidth);

                self.emulation.lock().unwrap().change_bandwidth(ip,new_bandwidth as u32);

            }   

        }

        //print_message(self.name.clone(),format!("tc changes {}",self.tc_changes.clone()));

        for id in active_links_ids.clone(){
            self.clear_link(id as u16);
        }
        
    }

    //Add flow received from CM to our state  
    pub fn apply_flow_u8(&mut self,key:&String){
        let flow = self.get_flow_u8(key);

        let link_indices = flow.lock().unwrap().link_indices.clone();
        let path_used_bandwidth = flow.lock().unwrap().bandwidth.clone();
        if path_used_bandwidth == 0.0
            {return;}
        //print_message(self.name.clone(),format!("Used bandwidth by other is {}",path_used_bandwidth).to_string());
        let mut pathrtt = 0.0;
        //calculate RTT
        for index in link_indices.clone(){
            let link = self.get_link(index as u16);
            pathrtt+= link.lock().unwrap().latency * 2.0;
        }

        for index in link_indices.clone(){
            let link = self.get_link(index as u16);
            
            let mut flow = vec![];

            flow.push(pathrtt);

            flow.push(path_used_bandwidth);


            link.lock().unwrap().flows.push(flow);
        }

    }
    //Add flow received from CM to our state
    pub fn apply_flow_u16(&mut self,key:&String){
        let flow = self.get_flow_u16(key);

        let link_indices = flow.lock().unwrap().link_indices.clone();
        let path_used_bandwidth = flow.lock().unwrap().bandwidth.clone();
        if path_used_bandwidth == 0.0
            {return;}
        let mut pathrtt = 0.0;
        //calculate RTT
        for index in link_indices.clone(){
            let link = self.get_link(index as u16);
            pathrtt+= link.lock().unwrap().latency * 2.0;
        }

        for index in link_indices.clone(){
            let link = self.get_link(index as u16);
            
            let mut flow = vec![];

            flow.push(pathrtt);

            flow.push(path_used_bandwidth);


            link.lock().unwrap().flows.push(flow);
        }

    }

    pub fn get_link(&mut self,id:u16)-> Arc<Mutex<Link>>{

        return Arc::clone(self.get_current_graph().lock().unwrap().links.get_mut(&id).unwrap());

    }

    pub fn clear_link(&mut self,id:u16){
        self.get_current_graph().lock().unwrap().links.get_mut(&id).unwrap().lock().unwrap().clear_flows();
    }

    pub fn get_path(&mut self,id:u32)-> Option<Arc<Mutex<Path>>>{

        return self.get_current_graph().lock().unwrap().get_path(id);

    }

    pub fn get_flow_u8(&mut self,key:&String) -> Arc<Mutex<Flowu8>>{
        return Arc::clone(self.get_current_graph().lock().unwrap().flow_accumulator_u8.get_mut(key).unwrap());
    }

    pub fn get_flow_u16(&mut self,key:&String) -> Arc<Mutex<Flowu16>>{
        return Arc::clone(self.get_current_graph().lock().unwrap().flow_accumulator_u16.get_mut(key).unwrap());
    }

    pub fn get_flow_keys(&mut self) -> Vec<String>{
        return self.get_current_graph().lock().unwrap().flow_accumulator_keys.clone();
    }
    pub fn clear_paths(&mut self){
        self.active_paths.clear();
        self.active_paths_ids.clear();
    }

    pub fn get_active_paths(&mut self) -> Vec<Arc<Mutex<Path>>>{
        let mut paths = vec![];

        for id in &self.active_paths_ids.clone(){
            paths.push(self.get_path(*id).unwrap().clone());
        }

        return paths;
    }

}
