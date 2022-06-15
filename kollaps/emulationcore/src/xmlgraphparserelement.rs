use crate::state::{State};
use std::sync::{Arc, Mutex};
use roxmltree::{Document,Node   };
use random_string::generate;
use regex::Regex;
use crate::eventscheduler::{EventScheduler};
use rand::prelude::*;
use rand_pcg::Pcg64;
use std::f32 ::INFINITY;
use crate::aux::print_and_fail;
use crate::aux::convert_to_int;
use std::net::IpAddr;
use std::str::FromStr;
use elementtree::Element;


pub struct XMLGraphParser{
    file:String,
    state:Arc<Mutex<State>>,
    mode:String,
    pub ips:Vec<String>,
    pub controller_ip:String,

}

impl XMLGraphParser{
    pub fn new (file:String,state:Arc<Mutex<State>>,mode:String) -> XMLGraphParser{
        XMLGraphParser{
            file:file,
            state:state,
            mode:mode,
            ips:vec![],
            controller_ip:"".to_string()
        }
    }

    pub fn fill_graph(&mut self,root:Element)
    {

        if root.tag().name() != "experiment"{
            print_and_fail(format!("{}",root.tag().name()));
            print_and_fail("Not a valid Kollaps topology file, root is not <experiment>".to_string());
            return;
        }

        if root.get_attr("boot").is_none(){
            print_and_fail("<experiment boot = > The experiment needs a valid boostrapper image tag".to_string());
            return;
        }

        let mut services:Option<&Element> = root.find("services");

        let mut bridges:Option<&Element> = root.find("bridges");

        let mut links:Option<&Element> = root.find("links");

        let mut dynamic:Option<&Element> = root.find("dynamic   ");

        // for node in root.children(){
        //     // if !node.is_element(){
        //     //     continue;
        //     // }
        //     if node.tag().name() == "services"{
        //         if !services.is_none(){
        //             print_and_fail("Only one <services> block is allowed.".to_string());
        //         }
        //         services = Some(node);

        //     }
        //     if  node.tag().name() == "bridges"{
        //         if !bridges.is_none(){
        //             print_and_fail("Only one <bridges> block is allowed.".to_string());
        //         }
        //         bridges = Some(node);
        //     }
        //     if node.tag().name() == "links"{
        //         if !links.is_none(){
        //             print_and_fail("Only one <links> block is allowed.".to_string());
        //         }
        //         links = Some(node);
        //     }
        //     if node.tag().name() == "dynamic"{
        //         if !dynamic.is_none(){
        //             print_and_fail("Only one <dynamic> block is allowed.".to_string());
        //         }
        //         dynamic = Some(node);

        //     }
        // }

        if services.is_none(){
            print_and_fail("No services declared in topology".to_string());
        }
        self.parse_services(services.unwrap(),dynamic);

        if !bridges.is_none(){
            self.parse_bridges(bridges.unwrap());
        }
        if links.is_none(){
            print_and_fail("No links declared in topology".to_string());
        }
        self.parse_links(links.unwrap());


    }


    pub fn parse_services(&mut self,services:&Element,dynamic:Option<&Element>){
        for service in services.children(){
            // if !service.is_element() {
            //     continue;
            // }
            if !(service.tag().name() == "service"){
                print_and_fail(format!("Invalid tag inside <services> {}", service.tag().name()));
            }
            if self.mode == "container"{
                if service.get_attr("name").is_none() || service.get_attr("image").is_none(){
                    println!("{}",service.to_string().unwrap());
                    print_and_fail("A service needs a name and an image attribute.".to_string());
                }
            }
            if self.mode == "baremetal"{
                if service.get_attr("name").is_none(){
                    print_and_fail("A service needs a name".to_string());
                }
            }
            let mut paths:Vec<String> = vec![];
            if !service.get_attr("activepaths").is_none(){
                paths = self.process_active_paths(service.get_attr("activepaths").unwrap());

            }

            // let mut command = "";

            // if service.has_get_attribute("command"){
            //     command = service.get_attribute("command").unwrap();
            // }


            let mut shared = false;

            if !service.get_attr("share").is_none(){
                shared = service.get_attr("share").unwrap() == "true";
            }


            let mut supervisor = false;

            let mut supervisor_port = 0;
            if !service.get_attr("supervisor").is_none(){
                supervisor = true;

                if !service.get_attr("port").is_none(){
                    supervisor_port = service.get_attr("port").unwrap().parse().unwrap();
                }
            }


            let mut reuse = true;

            if !service.get_attr("reuse").is_none(){
                reuse = service.get_attr("reuse").unwrap() == "true";
            }

            let mut replicas = 1;

            if !service.get_attr("replicas").is_none(){
                replicas = service.get_attr("replicas").unwrap().parse().unwrap();
            }

            replicas = self.calculate_required_replicas(dynamic,service,replicas,reuse);


            for _i in 0..replicas{

                if self.mode == "container"{
                    let tag = service.get_attr("name").unwrap().to_string();

                    self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_service(tag,shared,reuse,replicas,None,paths.clone());
                }

                if self.mode == "baremetal"{
                    let tag = service.get_attr("name").unwrap().to_string();
                    let ip = service.get_attr("ip");

                    if ip.is_none(){

                    }
                    else{
                        self.ips.push(ip.unwrap().to_string());
                        let ip = IpAddr::from_str(&ip.unwrap().to_string()).unwrap();
                        match ip{
                            IpAddr::V4(ipv4)=>{
                                self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_service(tag,shared,reuse,replicas,Some(convert_to_int(ipv4.octets())),paths.clone());
                            },
                            IpAddr::V6(_ipv6) => print_and_fail("Only ipv6 allowed for now".to_string()),
                    }
                    }

                }

                if supervisor{
                    let tag = service.get_attr("name").unwrap().to_string();
                    self.state.lock().unwrap().get_current_graph().lock().unwrap().set_dashboard(tag,supervisor_port);

                    if self.mode == "baremetal"{
                        let controller_ip = service.get_attr("controller_ip");
                        if controller_ip.is_none(){
                            print_and_fail("Controller needs to have an ip".to_string());
                        }else{
                            self.controller_ip = controller_ip.unwrap().to_string();
                        }
                    }
                }
            }
        }

    }

    pub fn process_active_paths(&mut self,activepaths:&str) -> Vec<String>{

        let activepaths = activepaths.replace("[","");
        let activepaths = activepaths.replace("]","");

        let activepaths = activepaths.split(",");

        let mut vector_paths = vec![];
        for path in activepaths{
            let path = path.replace("'","");
            vector_paths.push(path.to_string());
        }
        return vector_paths;

    }

    pub fn calculate_required_replicas(&mut self,dynamic:Option<&Element>,service:&Element,replicas:u32,reuse:bool) ->u32{

        if dynamic.is_none(){
            return replicas;
        }

        //first we collect the join/leave/crash/disconnect/reconnect events
        //so we can later sort them and calculate the required replicas

        let mut events = vec![];

        let join_event = 1.0;
        let leave_event = 2.0;
        let crash_event = 3.0;
        let disconnect_event = 4.0;
        let reconnect_event = 5.0;

        let time = 0;

        let amount = 1;

        let event_type = 2;

        let mut has_joins = false;

        for event in dynamic.unwrap().children(){
            // if !event.is_element(){
            //     continue;
            // }
            if event.tag().name() != "schedule"{
                print_and_fail("Only <schedule> is allowed inside <dynamic>".to_string());
            }

            if !event.get_attr("name").is_none() && !event.get_attr("time").is_none() && !event.get_attr("action").is_none(){

                if event.get_attr("name").unwrap() !=service.get_attr("name").unwrap(){
                    continue;
                }
                //missing check on time
                let event_time:f32  = event.get_attr("time").unwrap().parse().unwrap();

                if event_time.is_nan(){
                    print_and_fail("time get_attribute must be a valid real number".to_string());
                }

                let mut event_amount:f32  = 1.0;

                if !event.get_attr("amount").is_none(){
                    event_amount = event.get_attr("amount").unwrap().parse().unwrap();

                    if event_amount.is_nan(){
                        print_and_fail("amount get_attribute must be an integer >= 1".to_string());
                    }
                }

                //parse action

                if event.get_attr("action").unwrap() == "join"{
                    has_joins = true;
                    let mut event_entry = vec![];
                    event_entry.push(event_time);
                    event_entry.push(event_amount);
                    event_entry.push(join_event);
                    events.push(event_entry);


                }
                if event.get_attr("action").unwrap()  == "leave"{
                    let mut event_entry = vec![];
                    event_entry.push(event_time);
                    event_entry.push(event_amount);
                    event_entry.push(leave_event);
                    events.push(event_entry);

                }
                if event.get_attr("action").unwrap()  == "crash"{
                    let mut event_entry = vec![];
                    event_entry.push(event_time);
                    event_entry.push(event_amount);
                    event_entry.push(crash_event);
                    events.push(event_entry);

                }
                if event.get_attr("action").unwrap()  == "disconnect"{
                    let mut event_entry = vec![];
                    event_entry.push(event_time);
                    event_entry.push(event_amount);
                    event_entry.push(disconnect_event);
                    events.push(event_entry);

                }
                if event.get_attr("action").unwrap()  == "reconnect"{
                    let mut event_entry = vec![];
                    event_entry.push(event_time);
                    event_entry.push(event_amount);
                    event_entry.push(reconnect_event);
                    events.push(event_entry);

                }
            }
        }

        if !has_joins{
            return replicas;
        }

        events.sort_by(|a,b| a[time].partial_cmp(&b[time]).unwrap());

        let mut max_replicas = 0.0;

        let mut cumulative_replicas = 0.0;

        let mut disconnected = 0.0;

        let mut current_replicas = 0.0;
        for event in events{

            if event[event_type] == join_event{
                current_replicas += event[amount];
                cumulative_replicas+= event[amount];
            }

            if event[event_type] == leave_event || event[event_type] == crash_event{
                current_replicas -= event[amount];
            }

            if event[event_type] == disconnect_event{
                disconnected += event[amount];
                if event[amount] > current_replicas{
                    print_and_fail(format!("Dynamic section for {} disconnects more replicas than are joined at second {:.1}",service.get_attr("name").unwrap(),event[time]));
                }
            }

            if event[event_type] == reconnect_event{
                disconnected-= event[amount];

                if event[amount] > disconnected{
                    print_and_fail(format!("Dynamic section for {} reconnects more replicas than are joined at second {:.1}",service.get_attr("name").unwrap(),event[time]));

                }
            }

            if current_replicas < 0.0{
                print_and_fail(format!("Dynamic section for {} causes a negative number of replicas at second {:.1}",service.get_attr("name").unwrap(),event[time]));

            }
            if current_replicas > max_replicas{
                max_replicas = current_replicas;
            }
        }

        if reuse{
            return max_replicas as u32;
        }
        else{
            return cumulative_replicas as u32;
        }
    }

    pub fn parse_bridges(&mut self,bridges:&Element){

        for bridge in bridges.children(){
            // if !bridge.is_element(){
            //     continue;
            // }
            if bridge.tag().name() != "bridge"{
                print_and_fail(format!("Invalid tag inside <bridges>: {}",bridge.tag().name()));
            }

            if bridge.get_attr("name").is_none(){
                print_and_fail("A bridge needs to have a tag".to_string())
            }

            self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_bridge(bridge.get_attr("name").unwrap().to_string(),None);
        }
    }

    pub fn parse_links(&mut self, links:&Element){
        for link in links.children(){

            // if !link.is_element() {
            //     continue;
            // }

            let source = link.get_attr("origin").unwrap().to_string();

            let destination = link.get_attr("dest").unwrap().to_string();

            // if !link.is_element(){
            //     continue;
            // }
            if link.tag().name() != "link"{
                print_and_fail(format!("Invalid tag inside <link> {}", link.tag().name()));
            }

            if self.mode == "container"{
                if link.get_attr("origin").is_none() || link.get_attr("dest").is_none() || link.get_attr("latency").is_none() || link.get_attr("upload").is_none() || link.get_attr("network").is_none(){
                    print_and_fail("Incomplete network description".to_string());
                }
            }

            if self.mode == "baremetal"{
                if link.get_attr("origin").is_none() || link.get_attr("dest").is_none() || link.get_attr("latency").is_none() || link.get_attr("upload").is_none(){
                    print_and_fail("Incomplete network description".to_string());
                }
            }

            let source_node = self.state.lock().unwrap().get_current_graph().lock().unwrap().get_nodes(source.clone())[0].clone();

            let destination_node = self.state.lock().unwrap().get_current_graph().lock().unwrap().get_nodes(destination.clone())[0].clone();

            let source_node_shared_link = source_node.lock().unwrap().shared;
            let destination_node_shared_link = destination_node.lock().unwrap().shared;

            // let mut network = "";
            // if self.mode == "container"{
            //     network = link.get_attribute("network").unwrap();
            // }
            // if self.mode == "baremetal"{
            //     network = "baremetal";
            // }

            let mut jitter:f32  = 0.0;
            if !link.get_attr("jitter").is_none(){
                jitter = link.get_attr("jitter").unwrap().parse().unwrap();
            }

            let mut drop:f32  = 0.0;
            if !link.get_attr("drop").is_none(){
                drop = link.get_attr("drop").unwrap().parse().unwrap();
            }

            let bidirectional = !link.get_attr("download").is_none();

            let both_shared = source_node_shared_link && destination_node_shared_link;

            let latency:f32  = link.get_attr("latency").unwrap().parse().unwrap();
            let upload = link.get_attr("upload").unwrap();
            let upload = self.parse_bandwidth(upload.to_string());
            let mut download = 0.0;
            if bidirectional{
                let download_str = link.get_attr("download").unwrap();
                download = self.parse_bandwidth(download_str.to_string());
            }

            if both_shared{
                let src_meta_bridge = self.create_meta_bridge().clone();
                let dst_meta_bridge = self.create_meta_bridge().clone();


               //create a link between both meta bridges
               self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_link(latency,jitter,drop,upload,src_meta_bridge.clone(),dst_meta_bridge.clone());

               if bidirectional{
                   self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_link(latency,jitter,drop,download,dst_meta_bridge.clone(),src_meta_bridge.clone());

               }

               //connect source to src meta bridge
               self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_link(0.0,0.0,0.0,upload,source.clone(),src_meta_bridge.clone());

               if bidirectional{
                self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_link(0.0,0.0,0.0,download,src_meta_bridge.clone(),source.clone());

               }
               //connect destination to dst meta bridge
               self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_link(0.0,0.0,0.0,upload,dst_meta_bridge.clone(),destination.clone());
               if bidirectional{
                self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_link(0.0,0.0,0.0,download,destination.clone(),dst_meta_bridge.clone());


               }

            }else if source_node_shared_link{
                let meta_bridge = self.create_meta_bridge();

                //create a link between meta bridge and destination
                self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_link(latency,jitter,drop,upload,meta_bridge.clone(),destination.clone());
                if bidirectional{
                    self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_link(latency,jitter,drop,download,destination.clone(),meta_bridge.clone());

                }

                //connect origin to meta bridge
                self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_link(0.0,0.0,0.0,upload,source.clone(),meta_bridge.clone());


                if bidirectional{
                    self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_link(0.0,0.0,0.0,download,meta_bridge.clone(),source.clone());


                }
            }else if destination_node_shared_link{

                let meta_bridge = self.create_meta_bridge();
                //create a link between origin and meta bridge
                self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_link(latency,jitter,drop,upload,source.clone(),meta_bridge.clone());

                if bidirectional{
                    self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_link(latency,jitter,drop,download,meta_bridge.clone(),source.clone());

                }

                //connect meta bridge to destination
                self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_link(0.0,0.0,0.0,upload,meta_bridge.clone(),destination.clone());

                if bidirectional{
                    self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_link(0.0,0.0,0.0,download,destination.clone(),meta_bridge.clone());

                }
            }else{
                self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_link(latency,jitter,drop,upload,source.clone(),destination.clone());

                if bidirectional{
                    self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_link(latency,jitter,drop,download,destination.clone(),source.clone());

                }
            }


        }
    }


    pub fn create_meta_bridge(&mut self) -> String{
        let charset = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
        let string = generate(5, charset);

        self.state.lock().unwrap().get_current_graph().lock().unwrap().insert_bridge(string.clone(),None);

        return string.clone();

    }

    pub fn parse_bandwidth(&mut self, bandwidth:String) -> f32 {

        let bandwidth_regex = Regex::new(r"([0-9]+)([KMG])bps").unwrap();

        if bandwidth_regex.is_match(&bandwidth){
            let captures = bandwidth_regex.captures(&bandwidth).unwrap();
            let base:f32  = captures.get(1).unwrap().as_str().parse().unwrap();
            let multiplier = captures.get(2).unwrap().as_str();
            if multiplier == "K"{
                return base*1000.0;
            }
            if multiplier == "M"{
                return base*1000.0*1000.0;
            }if multiplier == "G"{
                return base*1000.0*1000.0*1000.0
            }

        }else{
            //print and fail
            return 0.0;
        }
        return 0.0;

    }

    pub fn parse_schedule(&mut self,scheduler:Arc<Mutex<EventScheduler>>,root:Element){

        let mut scheduler = scheduler.lock().unwrap();

        let mut dynamic = None;

        for node in root.children(){
            // if !node.is_element(){
            //     continue;
            // }
            if node.tag().name() == "dynamic"{
                if !dynamic.is_none(){
                    print_and_fail("Only one <dynamic> block is allowed.".to_string());
                }
                dynamic = Some(node);

            }
        }

        let root = self.state.lock().unwrap().get_current_graph().lock().unwrap().graph_root.as_ref().unwrap().clone();
        let mut first_join = -1.0;
        let mut first_leave = INFINITY;

        if dynamic.is_none(){
            scheduler.schedule_join(0.0);
            return;
        }

        let mut rng = Pcg64::seed_from_u64(12345);

        let mut replicas = vec![];

        for _i in 0..root.lock().unwrap().replicas.clone(){

            let mut element = vec![];

            element.push(false);
            element.push(false);
            element.push(false);

            replicas.push(element);
        }

        let joined = 0;
        let disconnected = 1;
        let used = 2;

        for event in dynamic.unwrap().children(){
            // if !event.is_element() {
            //     continue;
            // }

            if !(event.tag().name() == "schedule"){
                print_and_fail(format!("Only <schedule> is allowed inside <dynamic> {} ",event.tag().name().to_string()));
            }

            let mut time = 0.0;

            if !event.get_attr("time").is_none(){
                time = event.get_attr("time").unwrap().parse().unwrap();

                if time < 0.0 {
                    print_and_fail("time get_attribute must be a positive number".to_string());
                }
            }

            if !event.get_attr("name").is_none() && !event.get_attr("action").is_none(){
                let node_tag = event.get_attr("name").unwrap().to_string();

                let mut bridge_tags = vec![];
                for (tag,_bridges) in self.state.lock().unwrap().get_current_graph().lock().unwrap().bridges_by_name.iter(){
                    bridge_tags.push(tag.clone());
                }

                if bridge_tags.contains(&node_tag){
                    if event.get_attr("action").unwrap() == "join"{
                        scheduler.schedule_bridge_join(time,node_tag.to_string())
                    }

                    if event.get_attr("action").unwrap() == "leave"{
                        scheduler.schedule_bridge_leave(time,node_tag.to_string())
                    }

                }

                if node_tag != root.lock().unwrap().hostname{
                    continue;
                }

                let mut amount:u32 = 1;

                if !event.get_attr("amount").is_none(){
                    amount = event.get_attr("amount").unwrap().parse().unwrap();
                }

                let event_type = event.get_attr("action").unwrap().to_string();

                if event_type == "join"{
                    for _i in 0..amount{
                        let mut available;

                        let mut id:usize;

                        loop{

                            id = rng.gen_range(0..root.lock().unwrap().replicas) as usize;

                            available = !replicas[id][joined];

                            if !root.lock().unwrap().reuse{
                                available = available && !replicas[id][used];
                            }
                            if available{
                                break;
                            }

                        }

                        //mark the state
                        replicas[id][joined] = true;

                        if !root.lock().unwrap().reuse{
                            replicas[id][used] = true;

                        }

                        //if it is us
                        if root.lock().unwrap().replica_id == id{
                            scheduler.schedule_join(time);
                        }

                        if first_join < 0.0{
                            first_join  = time;
                        }
                    }
                }

                if event_type == "leave" || event_type == "crash"{
                    for _i in 0..amount{
                        let mut up;

                        let mut id:usize;

                        loop{

                            id = rng.gen_range(0..root.lock().unwrap().replicas) as usize;

                            up = replicas[id][joined];

                            if up{
                                break;
                            }


                        }

                        replicas[id][joined] = false;


                        if root.lock().unwrap().replica_id == id{

                            if event_type == "leave"{
                                scheduler.schedule_leave(time);
                            }

                            if event_type == "crash"{
                                scheduler.schedule_crash(time);

                            }
                        }

                        if first_leave > time{
                            first_leave = time;
                        }
                    }


                }

                if event_type == "reconnect"{
                    for _i in 0..amount{
                        let mut disconnected_bool;

                        let mut id;

                        loop{

                            id = rng.gen_range(0..root.lock().unwrap().replicas) as usize;

                            disconnected_bool = replicas[id][disconnected];

                            if disconnected_bool{
                                break;
                            }


                        }

                        replicas[id][disconnected] = false;
                        if root.lock().unwrap().replica_id == id{
                            scheduler.schedule_reconnect(time);
                        }
                    }
                }

                if event_type == "disconnect"{
                    for _i in 0..amount{
                        let mut connected;

                        let mut id;

                        loop{

                            id = rng.gen_range(0..root.lock().unwrap().replicas) as usize;

                            connected = replicas[id][disconnected] && replicas[id][disconnected];

                            if connected{
                                break;
                            }


                        }

                        replicas[id][disconnected] = true;

                        if root.lock().unwrap().replica_id == id{
                            scheduler.schedule_disconnect(time);
                        }
                    }
                }

            }

            if !event.get_attr("origin").is_none() && !event.get_attr("dest").is_none() && !event.get_attr("time").is_none(){
                let origin = event.get_attr("origin").unwrap().to_string();
                let destination = event.get_attr("dest").unwrap().to_string();

                if !event.get_attr("action").is_none(){
                    let event_type = event.get_attr("action").unwrap().to_string();

                    if event_type == "leave"{
                        scheduler.schedule_link_leave(time,origin,destination);
                    }

                    if event_type == "join"{
                        let origin = event.get_attr("origin").unwrap().to_string();
                        let destination = event.get_attr("dest").unwrap().to_string();

                        let link_existed = scheduler.schedule_link_join(time,origin.clone(),destination.clone());

                        if link_existed{
                            continue;
                        }

                        else{

                            let bandwidth= event.get_attr("upload").unwrap().to_string();

                            let latency:f32  = event.get_attr("latency").unwrap().parse().unwrap();

                            let mut drop:f32  = 0.0;

                            if !event.get_attr("drop").is_none(){
                                drop = event.get_attr("drop").unwrap().parse().unwrap();
                            }

                            let mut jitter:f32  = 0.0;

                            if !event.get_attr("jitter").is_none(){
                                jitter = event.get_attr("jitter").unwrap().parse().unwrap();
                            }

                            scheduler.schedule_new_link(time,origin.clone(),destination.clone(),latency,jitter,drop,self.parse_bandwidth(bandwidth));


                            if !event.get_attr("download").is_none(){

                                let bandwidth = event.get_attr("download").unwrap().to_string();
                                scheduler.schedule_new_link(time,destination.clone(),origin.clone(),latency,jitter,drop,self.parse_bandwidth(bandwidth));
                            }
                        }

                    }
                }else{
                    let mut bandwidth = -1.0;

                    if !event.get_attr("upload").is_none(){
                        bandwidth = self.parse_bandwidth(event.get_attr("upload").unwrap().to_string());
                    }

                    let mut latency = -1.0;

                    if !event.get_attr("latency").is_none(){
                        latency = event.get_attr("latency").unwrap().parse().unwrap();
                    }

                    let mut drop = -1.0;

                    if !event.get_attr("drop").is_none(){
                        drop = event.get_attr("drop").unwrap().parse().unwrap();
                    }

                    let mut jitter = -1.0;
                    if !event.get_attr("jitter").is_none(){
                        jitter = event.get_attr("jitter").unwrap().parse().unwrap();
                    }

                    scheduler.schedule_link_change(time,origin.clone(),destination.clone(),latency,jitter,drop,bandwidth);

                }

            }

        }

    }

}