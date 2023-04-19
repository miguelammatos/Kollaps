## Orchestrators

### Setting up Docker Swarm

To create a Swarm, execute on one machine:
```
docker swarm init
```
This gives you a join command like this: `docker swarm join --token <token> <IP>:<port>`.
If you want to run experiments on a multi-node cluster, execute this command on all the other nodes. Promote each of them to manager like this: `docker node promote <node name>`.
The experiments in the examples folder require the existence of an attachable network named "kollaps_network".
To create it, run:
```
docker network create --driver=overlay --subnet=10.1.0.0/24 kollaps_network
```
(Make sure to define a subnet that does not collide with other networks on your setup.)


### Setting up Baremetal

To create a baremetal deployment, a specific topology file has to be created, steps are described [here](https://github.com/miguelammatos/kollaps-private/wiki/Baremetal-experiments#topology-description)

After creating the topology file which has to be named topology.xml, you must put the baremetal folder (Kollaps/baremetal) in the directories specified in the .xml on the remote machines

After setting up the remote machines, we must setup the Dashboard container, for the container to have ssh access to the remote machines we must put the ~/.ssh/ folder in the baremetal/ directory.

```
cp -R ~/.ssh/ baremetal/
```

Now lets build the container with
```
docker build -f dockerfiles/Dashboard -t dashboard:2.0 .
```

And now you are ready to emulate network states on your remote machines, start the Dashboard with

```
docker run -d --network host dashboard:2.0
```

When you are finished run

```
docker stop #NAME or #ID of container
```

The Dashboard will be available at 0.0.0.0:8088

The dashboard has small differences in baremetal, the commands description can be seen [here](https://github.com/miguelammatos/kollaps-private/wiki/Baremetal-experiments#dashboard)

If in the remote machines the network devices have names different than eth0, please change it in the start.sh script located inside the baremetal folder.

### Setting up Kubernetes

Sources: https://serverfault.com/a/684792; https://gist.github.com/alexellis/

Do not forget docker being installed is always necessary!
First, disable swap on your system: find swap volumes with `cat /proc/swaps`. Then, turn off swap:

```
sudo swapoff --a
```

Comment out any of the volumes found before in `/etc/fstab` and reboot your system.

Then, install Kubernetes:

```
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add - && \
echo "deb http://apt.kubernetes.io/ kubernetes-xenial main" | sudo tee /etc/apt/sources.list.d/kubernetes.list && \
sudo apt-get update -q && \
sudo apt-get install -qy kubeadm
```

Do this on all nodes.

#### The Kubernetes master node

Only on the master node, execute:

```
sudo sysctl net.bridge.bridge-nf-call-iptables=1
sudo kubeadm init --token-ttl=0
```
If you have the error 
[ERROR CRI]: container runtime is not running: output: time="2023-04-17T12:35:13Z" level=fatal msg="validate service connection: CRI v1 runtime API is not implemented for endpoint \"unix:///var/run/containerd/containerd.sock\": rpc error: code = Unimplemented desc = unknown service runtime.v1.RuntimeService"

This is a possible solution

```
rm /etc/containerd/config.toml
systemctl restart containerd
```

The `kubeadm init` command tells you to execute the following statements:

```
mkdir -p $HOME/.kube && \
sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config && \
sudo chown $(id -u):$(id -g) $HOME/.kube/config
cp $HOME/.kube/config kube/config
```

It also gives you a join command like this: `sudo kubeadm join <IP>:<PORT> --token <TOKEN> --discovery-token-ca-cert-hash sha256:<HASH>`. Use this on the worker nodes to join the cluster.

Next (only on the master again), install the Weavenet CNI plugin with a custom IP range:

```
kubectl apply -f https://github.com/weaveworks/weave/releases/download/v2.8.1/weave-daemonset-k8s.yaml
```
Note that we also successfully tested the Calico CNI plugin.

If you want to run pods on the master node, un-taint it:

```
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
```


#### Setting up minikube

To use local docker images, we use minikube install it with:

```
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

```

Start minikube with:

```
minikube start
```

And to load the Kollaps image into minikube run

```
eval $(minikube docker-env)  
docker build --rm -f dockerfiles/Kollaps -t kollaps:2.0 .
minikube docker-env --unset
```

Finally rebuild the Deployment Generator

```
docker build -f dockerfiles/DeploymentGenerator -t kollaps-deployment-generator:2.0 .
```

