use docker_api::ExecContainerOpts;
use futures::StreamExt;
use subprocess::PopenConfig;
use subprocess::Popen;
use subprocess::Redirection;

static mut COMMAND_STRING:Option<String> = None;


pub async fn start_experiment(id:String){

    get_command_string(id.clone()).await;
    let docker = docker_api::Docker::unix("/var/run/docker.sock");

    let container = docker.containers().get(id);

    let command_string;
    unsafe{
        command_string= COMMAND_STRING.as_ref().unwrap().clone().
        as_mut_str().replace('"',"\"").as_mut_str().replace("'","\\'");
    }


    let mut args = vec![];

    args.push("/bin/sh");
    args.push("-c");

    let mut command;
    command = format!("echo{}",command_string);

    command = format!("{} > /tmp/Kollaps_hang",command);

    args.push(&command);
    

    let opts = ExecContainerOpts::builder()
        .cmd(args)
        .attach_stdout(true)
        .attach_stderr(true)
        .build();
    
    let mut stream = container.exec(&opts);

    //run command
    stream.next().await;
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

    println!("COMMAND_STRING is {}", command_string.clone());

}

//Kill every process in the namespace of the container
pub fn stop_experiment(pid:u32){
    Popen::create(&["nsenter", "-t", &pid.to_string(),"-p","-m","/bin/sh","-c","kill -2 -1"], PopenConfig {
        stdout: Redirection::Pipe, ..Default::default()
    }).unwrap();

}