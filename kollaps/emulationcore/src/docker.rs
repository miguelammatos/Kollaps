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

//use docker_api::Exec;
use docker_api::ExecContainerOpts;
use futures::StreamExt;
use subprocess::PopenConfig;
use subprocess::Popen;
use subprocess::Redirection;
//use docker_api::opts::ExecCreateOpts;

static mut COMMAND_STRING:Option<String> = None;


pub async fn start_experiment(id:String){

    get_command_string(id.clone()).await;

    let docker = docker_api::Docker::unix("/var/run/docker.sock");

    let container = docker.containers().get(id);

    let command_string;
    unsafe{
        if COMMAND_STRING.as_ref().is_none() || COMMAND_STRING.as_ref().unwrap().is_empty(){
            println!("Leaving start experiment nothing to do");
            return
        }
        command_string= COMMAND_STRING.as_ref().unwrap().clone().
        as_mut_str().replace('"',"\"").as_mut_str().replace("'","\\'");
    }


    let mut args = vec![];

    args.push("/bin/sh");
    args.push("-c");
 
    args.push(&command_string);
    

    let opts = ExecContainerOpts::builder()
        .cmd(args)
        .attach_stdout(true)
        .attach_stderr(true)
        .build();
    
    let mut stream = container.exec(&opts);

    //run command
    stream.next().await;

    // // Create Opts with specified command
    // let opts = ExecCreateOpts::builder()
    //     .command(args)
    //     .attach_stdout(true)
    //     .attach_stderr(true)
    //     .build();

    // let exec = Exec::create(docker, &container.id(), &opts).await;


    // println!("CREATED EXEC");

    // let mut stream = exec.as_ref().unwrap().start().next().await;

    // println!("EXEC RUNNING");

    // println!("{:#?}", exec.as_ref().unwrap().inspect().await);

    // println!("RUNNING COMMAND");
}
//Retrieve the command to run
pub async fn get_command_string(id:String){
    let docker = docker_api::Docker::unix("/var/run/docker.sock");

    let container = docker.containers().get(id);
    
    let mut command_string = "".to_string();
    match container.inspect().await {
        Ok(container) => {
            let container_config = container.config.unwrap();

            let image = container_config.image;

            let docker_image = docker.images().get(image);

            let mut command = vec![];
            match docker_image.inspect().await{
                Ok(image) =>{
                    let image_config = image.config;

                    let entrypoint = image_config.entrypoint;

                    if entrypoint.is_none(){
                        return
                    }

                    if container_config.cmd.is_none(){
                        if !image_config.cmd.is_none(){
                            command.extend(image_config.cmd.as_ref().unwrap());
                        }
                    }

                    else if container_config.cmd.as_ref().unwrap().len() == 0{
                        if !image_config.cmd.is_none(){
                            command.extend(image_config.cmd.as_ref().unwrap());
                        }
                    }else{
                        command.extend(container_config.cmd.as_ref().unwrap());
                    }
                    
                    for string in entrypoint.unwrap(){
                        command_string = format!("{} {}",command_string,string);
                    }
                    for string in command{
                        command_string = format!("{} {}",command_string,string);
                    }
                    

                    
                },
                Err(e) => eprintln!("Error: {}", e),
            }
        },
        Err(e) => eprintln!("Error: {}", e),
    };

    unsafe{
        COMMAND_STRING = Some(command_string.clone());
    }

}

//Kill every process in the namespace of the container
pub fn stop_experiment(pid:u32){
    Popen::create(&["nsenter", "-t", &pid.to_string(),"-p","-m","/bin/sh","-c","kill -2 -1"], PopenConfig {
        stdout: Redirection::Pipe, ..Default::default()
    }).unwrap();

}