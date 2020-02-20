# Kollaps
Decentralized container based network emulator


This README is a quick introduction to run experiments with Kollaps and Thunderstorm.
Kollaps is the decentralized network emulator while Thunderstorm is the high-level language to specify experiments.
For further reference and details, check out the [Kollaps Wiki](https://github.com/miguelammatos/Kollaps/wiki)

## Prerequisites
- Clone this repo with:
```
$git clone --branch master --depth 1 --recurse-submodules https://github.com/miguelammatos/Kollaps.git
```
- You need a machine running **Linux** with a recent version of **Docker** installed, and **Python 3**.
- To run experiments, you need to build the **Kollaps tools** to generate runnable deployment files and the  **Kollaps image** as detailed below.
- You also need to build the **Docker images** for the applications in your experiment. We provide some example images along with our example experiments.
- Kollaps experiments rely on a container orchestrator. At the moment, **Docker Swarm** and **Kubernetes** are supported. We describe the workflow for both of these in detail below.

### Installing the Kollaps tools
Execute in the root folder (where this README is found):
```
$ pip3 wheel --no-deps . .
$ pip3 install kollaps-1.0-py3-none-any.whl
```
This installs the following tools:
- `KollapsDeploymentGenerator` that translate Kollaps topology descriptions into Docker Swarm Compose files or Kubernetes Manifest files on your local machine.
- `ThunderstormTranslator` command, which lets you declare an experiment in a language with higher-level concepts which are then translated into XML topology descriptions.
- Note that the examples below assume both tools are in your PATH, which might require restarting your shell.

### Building the Kollaps image
You also need to build the Kollaps Docker image. To do so, execute in this folder:
```
$ docker build --rm -t kollaps:1.0 .
```

And also build the dashboard image, which allows to control the experiments.

```
$ cd images/dashboard/
$ docker build --rm -t kollaps/dashboard:1.0 .
```

### Building the application images

With the Kollaps tools and Kollaps images built, the next step is to build the images of the application under testing and define the network topology.
For simplicity, we provide multiple examples in the *examples* directory.

We will detail the iPerf3 experiment found in the *examples/iperf3* directory.

```
$ cd examples/iperf3/
```

To build each image, `cd` into its respective directory and execute:
```
$ docker build -t <Tag> .
```
as follows:

|folder|Tag|
|------|---|
|iperf3-client|  kollaps/iperf3-client:1.0 |
|iperf3-server|  kollaps/iperf3-server:1.0 |



The next step is to specify the topology.

#### Generating a deployment file

Use the provided `KollapsDeploymentGenerator` to transform an XML experiment specification into either a Docker Compose file or a Kubernetes Manifest file.

This assumes a working Docker Swarm or Kubernetes environment.
See [here](Orchestrators.md) for brief setup instructions.

The file *examples/iperf3/topology.xml* is provided as an example.
This example assumes the existence of a network named *kollaps_network*.
Create one (see [here](Orchestrators.md)) or update the xml file accordingly.

```

$ KollapsDeploymentGenerator topology.xml <orchestrator> > experiment.yaml
```
The orchestrator flag can be `-s` for Docker Swarm or `-k` for Kubernetes.

On either orchestrator, this command must be run on a Manager/Master node so that the KollapsDeploymentGenerator can gather information regarding the cluster state and pass it to the bootstrappers as environment variables.
This avoids all nodes requiring both Manager/Master status and full knowledge of the containers running on the cluster before the experiment can be started.

Note that this must be run from the folder in which the `topology` file sits, or a parent directory.
The resulting Compse/Manifest YAML file is directly deployable in Docker Swarm or Kubernetes and can be further customised as needed.

### Deploying an experiment

To deploy the generated file on Docker Swarm:

```
$ docker stack deploy -c experiment.yaml experiment
```

(Where "experiment" is an arbitrary name for the stack you are deploying)

To deploy the generated file in Kubernetes:

```
$ kubectl apply -f experiment.yaml
```

### Interacting with an experiment

Your main ways of interacting with the experiment are starting and stopping it and monitoring its progress.
You can also `exec` into the containers as needed but we do not detail this here.

The easiest way to interact with the experiments is through the *dashboard* through a web browser.
However, the dashboard was designed with the CLI in mind and can be interacted with through a terminal based browser like w3m or simply through HTTP GET requests with a basic tool such as curl.
The dashboard is available by default on *<dashboardIP:8088>*.

After deploying the Compose/Manifest file, the containers are started up and establish a connection to the Dashboard. As soon as all containers are shown as **ready**, you can **start** the experiment. Click **start** or `curl <dashboard IP>:8088/start` to start the experiment. This will launch the applications inside the containers (by invoking the respective entrypoints).

After this point the experiment will run, following the schedule in the topology description file, if any.
You can observe/measure the performance of the application using the usual tools.
In the iPerf example we are using, some coarse grained information is available under */var/log/* in each container.

#### On Swarm

On Swarm, the Dashboard is accessible on http://127.0.0.1:8088.

#### On Kubernetes

On Kubernetes, there is no port mapping from the container to the host. To find the allocated IP address of the dashboard, run `$kubectl get pods -o wide` and find the dashboard pod. Copy the IP address shown and open `<IP>:8088` in your browser.

### Safely remove an experiment

Clicking "stop" will stop the applications and ensure a clean shutdown of the experiment. On the command line, `curl http://<Dashboard IP>:8088/stop`.

On Swarm, remove the containers with:
```
$ docker stack rm experiment
```
(where experiment is the name you gave the deployment).

On Kubernetes:
```
$ kubectl delete -f experiment.yaml
```
