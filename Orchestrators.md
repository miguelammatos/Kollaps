##Orchestrators

### Setting up Docker Swarm

To create a Swarm, execute on one machine:
```
$docker swarm init
```
This gives you a join command like this: `docker swarm join --token <token> <IP>:<port>`.
If you want to run experiments on a multi-node cluster, execute this command on all the other nodes. Promote each of them to manager like this: `docker node promote <node name>`.
The experiments in the examples folder require the existence of an attachable network named "kollaps_network".
To create it, run:
```
docker network create --driver=overlay --subnet=10.1.0.0/24 kollaps_network
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
