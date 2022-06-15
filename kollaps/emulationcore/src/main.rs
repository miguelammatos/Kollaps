use std::env;
mod state;
mod graph;
mod elements;
mod emulation;
mod xmlgraphparser;
mod aux;
mod eventscheduler;
mod docker;
mod emulationcore;
mod communication;
use crate::emulationcore::EmulationCore;
use tokio::runtime;

fn main(){

    if env::args().len() == 4{
        container_deployment();
    }else{
        baremental_deployment();
    }
}

fn container_deployment(){
    let id = env::args()
        .nth(1)
        .unwrap();
    
    let pid = env::args()
        .nth(2)
        .unwrap();

    let orchestrator = env::args()
        .nth(3)
        .unwrap();

    
    let pid = pid.parse::<u32>().unwrap();

    println!("Started EC with ID {}",id.clone());
    let mut ec = EmulationCore::new(id.clone(),pid,orchestrator);
    ec.init();

    let basic_rt = runtime::Builder::new_multi_thread().worker_threads(1).enable_all().build().unwrap();
    basic_rt.block_on(async move{ec.emulation_loop().await});

    println!("STOPPED EC with ID {}",id.clone());

}

fn baremental_deployment(){

    println!("Started EC");
    let topology_file = env::args().nth(1).unwrap();

    let cm_file = env::args().nth(2).unwrap();

    let networkdevice = env::args().nth(3).unwrap();

    let mut ec = EmulationCore::new("".to_string(),0,"baremetal".to_string());

    ec.set_topology_file(topology_file);

    ec.set_cm_file(cm_file);

    ec.set_network_device(networkdevice);

    ec.init_baremetal();

    let basic_rt = runtime::Builder::new_multi_thread().worker_threads(1).enable_all().build().unwrap();
    basic_rt.block_on(async move{ec.emulation_loop().await});
    println!("STOPPED EMULATION");

}
