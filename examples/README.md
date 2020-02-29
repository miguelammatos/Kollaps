## Kollaps Example Applications

This folder contains several example images to illustrate the usage of Kollaps.

### Table of Contents:
1. [Basic usage](#basic-usage)
    * [Generating a topology file](#topology)
    * [Building an application](#app)
    * [Deploying an experiment](#deploy)
    * [Interacting with a running experiment](#interacting)
    * [Safely stopping an experiment](#stop)
2. [Available Applications](#available-apps)
    * [iPerf3](#iperf3)
    * [Redis](#redis)


### 1. Basic Usage: <a name="basic-usage"/>

We provide two convenience scripts in order to generate the required images for each application together with their deployment file.
Note that you will need to have the `kollaps` and `kollapsdeploymentgenerator` images available, to build them follow the instructions in the [main repository](https://github.com/miguelammatos/Kollaps).

#### Generating a topology file: <a name="topology"/>

Inside each application's folder, you will find a sample `topology.xml` that specifies the topology to be emulated.
Feel free to modify those at will, in particular, if you are interested in experimenting with different network shapes, modify the `<bridges>` and `links` section.
The `<dynamic>` section can be used to simulate dynamic behavious of the experiment.

Once you are content with your topology file, you can generate the `.yaml` required for the deployment using the following command for **Docker Swarm** deployments:
```
./KollapsDeploymentGenerator ./<app_name>/topology.xml -s <your_experiment_name>.yaml
```

Or the following one for **Kubernetes** (note that we just change the flag):
```
./KollapsDeploymentGenerator ./<app_name>/topology.xml -k <your_experiment_name>.yaml
```

#### Building an application: <a name="app"/>

Now you are ready to build the service images to launch and emulate your application with Kollaps.
In order to build the images run:
```
./KollapsAppBuilder <app_name>
```
where the supported app names are `iperf3` and `redis` which we describe in more detail [below](#available-apps).

#### Deploying an experiment: <a name="deploy"/>

Lastly, you just need to deploy the experiment.

If you are using **Docker Swarm** as orchestrator:
```
docker stack deploy <your_experiment_name>.yaml <deployment_name>
```

If you are using **Kubernetes**:
```
kubectl apply -f experiment.yaml
```

#### Interacting with a running experiment: <a name="interacting"/>

The easiest way to interact with the experiments is through the *dashboard* through a web browser.
You can also `exec` into the containers as needed but we do not detail this here.

After deploying the Compose/Manifest file, the containers are started up and establish a connection to the Dashboard.
As soon as all containers are shown as **ready**, you can **start** the experiment.
Click **start** or `curl <dashboard IP>:8088/start` to start the experiment. 

After this point the experiment will run, following the schedule in the topology description file, if any.
You can observe/measure the performance of the application using the usual tools.

On Swarm, the Dashboard is accessible on `http://127.0.0.1:8088`.

On Kubernetes, there is no port mapping from the container to the host. To find the allocated IP address of the dashboard, run `$kubectl get pods -o wide` and find the dashboard pod. Copy the IP address shown and open `<IP>:8088` in your browser.

#### Safely stopping an experiment: <a name="stop"/>

Clicking "stop" will stop the applications and ensure a clean shutdown of the experiment. On the command line, `curl http://<Dashboard IP>:8088/stop`.

On Swarm, remove the containers with:
```
$ docker stack rm <deployment_name>
```

On Kubernetes:
```
$ kubectl delete -f <your_experiment_name>.yaml
```

### 2. Available Applications: <a name="iperf3"/>

Currently we have two available sample applications, feel free to PR for more.

#### iPerf3: <a name="iperf3"/>

In this experiment (in the default setting) we set up three [iPerf3](https://iperf.fr/) clients which will connect to three different iPerf3 servers. Each client will try to saturate the bandwidth for 100 seconds and stop.

Check the shell scripts under the *iperf3-client* and *iperf3-server* directory for further details.

#### Redis: <a name="redis"/>

redis: experiment that uses the Redis database
