# Kollaps
Decentralized container based network emulator

Clone this repo with:
```
$git clone --branch master --depth 1 --recurse-submodules https://github.com/miguelammatos/Kollaps.git
```
This readme is a quick introduction to get Kollaps running. 
For further reference and details, check out the [Kollaps Wiki](https://github.com/miguelammatos/Kollaps/wiki)

## Prerequisites
- You need a machine running **Linux** with a recent version of **Docker** installed, and **Python 3**.
- To run experiments, build the **Kollaps image**. Also install the **Python packages** in order to generate runnable deployment files (both in this repository).
- You also need tho build the **Docker images** for the applications in your experiment. We provide some example images along with our example experiments.
- Kollaps experiments rely on a container orchestrator. At the moment, **Docker Swarm** and **Kubernetes** are supported. We describe the workflow for both of these in detail below.

### Installing the Python packages
Execute in this folder:
```
$pip wheel --no-deps . .
$pip install kollaps-1.0-py3-none-any.whl
```
Installing the python package will give you access to the `KollapsDeploymentGenerator` command to translate Kollaps topology descriptions into Docker Swarm Compose files or Kubernetes Manifest files on your local machine. It will also give you access to the `ThunderstormTranslator` command, which lets you declare an experiment in a language with higher-level concepts; these are then translated into XML topology descriptions.

### Building the Kollaps image
You also need to build the Kollaps Docker image. To do so, execute in this folder:
```
$docker build --rm -t kollaps:1.0 .
```

### Building the application images
Some simple experiment examples are available in the examples folder.

These experiments use images that are available in https://github.com/joaoneves792/NEED_Images

Before proceeding, you should build all the images in the folder "samples/" of the above repository.

To avoid changing the XML example files, the images should be built with the following tags:

|folder|Tag|
|------|---|
|alpineclient|  warpenguin.no-ip.org/alpineclient:1.0 |
|alpineserver|  warpenguin.no-ip.org/alpineserver:1.0 |
|dashboard|     warpenguin.no-ip.org/dashboard:1.0 |
|logger|        warpenguin.no-ip.org/logger:1.0 |

To build each image, `cd` into its respective folder and execute:
```
$docker build -t <Tag> .
```
These example use the overlay driver, but ipvlan/macvlan networks are also supported.

### Setting up Docker Swarm

To create a Swarm, execute on one machine:
```
$docker swarm init
```
This gives you a join command like this: `docker swarm join --token <token> <IP>:<port>`.
If you want to run experiments on a multi-node cluster, execute this command on all the other nodes. Promote each of them to manager like this: `docker node promote <node name>`.
The experiments in the examples folder require the existence of an attachable network named "test_overlay".
To create it, run:
```
docker network create --driver=overlay --subnet=10.1.0.0/24 test_overlay
```
(Make sure to define a subnet that does not collide with other networks on your setup.)

### Setting up Kubernetes

Sources: https://serverfault.com/a/684792; https://gist.github.com/alexellis/fdbc90de7691a1b9edb545c17da2d975

First, disable swap on your system: find swap volumes with `cat /proc/swaps`. Then, turn off swap:

```
$sudo swapoff --a
```

Comment out any of the volumes found before in `/etc/fstab` and reboot your system.

Then, install Kubernetes:

```
$curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add - && \
echo "deb http://apt.kubernetes.io/ kubernetes-xenial main" | sudo tee /etc/apt/sources.list.d/kubernetes.list && \
sudo apt-get update -q && \
sudo apt-get install -qy kubeadm
```

Do this on all nodes.

#### The Kubernetes master node

Only on the master node, execute:

```
$sudo sysctl net.bridge.bridge-nf-call-iptables=1
$sudo kubeadm init --token-ttl=0
```

The `kubeadm init` command tells you to execute the following statements:

```
$mkdir -p $HOME/.kube && \
sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config && \
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

It also gives you a join command like this: `sudo kubeadm join <IP>:<PORT> --token <TOKEN> --discovery-token-ca-cert-hash sha256:<HASH>`. Use this on the worker nodes to join the cluster.

Next (only on the master again), install the Weavenet CNI plugin with a custom IP range:

```
$kubectl apply -f "https://cloud.weave.works/k8s/net?k8s-version=$(kubectl version | base64 | tr -d '\n')&env.IPALLOC_RANGE=10.2.0.0/24"
```
Note that we also successfully tested the Calico CNI plugin.

If you want to run pods on the master node, un-taint it:

```
$kubectl taint nodes --all node-role.kubernetes.io/master-
```

### Generating a deployment file

Use the provided `KollapsDeploymentGenerator` to transform an XML experiment specification into either a Docker Compose file or a Kubernetes Manifest file.
Syntax:
```
$KollapsDeploymentGenerator topology5.xml <Orchestrator flag> > topology5.yaml
```
The orchestrator flag can be `-s` for Swarm or `-k` for Kubernetes. Default: Swarm. 

On either orchestrator, this command must be run on a Manager/Master node so that the KollapsDeploymentGenerator can gather information regarding the cluster state and pass it to the bootstrappers as environment variables. 
This avoids all nodes requiring both Manager/Master status and full knowledge of the containers running on the cluster before the experiment can be started.

Note that this must be run from the folder in which the `topology` file sits, or a parent directory.

### Deploying an experiment

On Swarm, deploy the generated file like so:

```
$docker stack deploy -c topology5.yaml 5
```

(Where 5 is an arbitrary name for the stack you are deploying)

On Kubernetes, like so:

```
$kubectl apply -f topology5.yaml
```

### Interacting with an experiment

Your main ways of interacting with the experiment are starting and stopping it and monitoring its progress. `exec`ing into the containers is not described in detail here.

It is easiest to interact with the Dashboard through a conventional browser, but it was designed to work even when that is not an option. You can also use a terminal based browser like w3m or simply issue HTTP GET requests with a basic tool such as curl.

After deploying the Compose/Manifest file, the containers are started up and establish a connection to the Dashboard. As soon as all containers are shown as **ready**, you can **start** the experiment. Click **start** or `curl <dashboard IP>:8088/start` to start the experiment. This will launch the applications inside the containers.

#### On Swarm

On Swarm, the Dashboard is accessible on http://127.0.0.1:8088.

#### On Kubernetes

On Kubernetes, there is no port mapping from the container to the host. To find the allocated IP address of the dashboard, run `$kubectl get pods -o wide` and find the dashboard pod. Copy the IP address shown and open `<IP>:8088` in your browser.

### Safely remove an experiment

Clicking "stop" will stop the applications and ensure a clean shutdown of NEED. On the command line, `curl http://<Dashboard IP>:8088/stop`.

On Swarm, remove the containers with:
```
$docker stack rm 5
```
(Where 5 is the name you gave the deployment).

On Kubernetes:
```
$kubectl delete -f topology5.yaml
```

#### Note

Removing the containers without cleanly stopping the experiment can potentially trigger a kernel memory corruption bug, leading to system instability!

If you have started an experiment (services report as "running" on the dashboard), always stop it through the dashboard/on the command line before removing the containers.
