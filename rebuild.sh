#!/bin/sh

pwdesktop=nope
pwlaptop=nope

########### reset kubernetes ########################################################################

# sudo swapoff --a && \
# sudo kubeadm reset && \
# sudo iptables -F && sudo iptables -t nat -F && sudo iptables -t mangle -F && sudo iptables -X && \
# sudo sysctl net.bridge.bridge-nf-call-iptables=1 && \
# sudo kubeadm init --token-ttl=0 && \
# mkdir -p $HOME/.kube && \
# sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config && \
# sudo chown $(id -u):$(id -g) $HOME/.kube/config && \
# kubectl apply -f "https://cloud.weave.works/k8s/net?k8s-version=$(kubectl version | base64 | tr -d '\n')" && \
# kubectl taint nodes --all node-role.kubernetes.io/master-


###############################################################################################

echo $pwdesktop | sudo -S systemctl restart docker

docker stack rm top
docker rm $(docker ps -aq)


###############################################################################################

# mkdir -p ~/Documents/NEED/Aeron/usr/lib && \
# mkdir -p ~/Documents/NEED/Aeron/binaries && \
# yes | cp -rpf ~/Documents/aeron4need/cppbuild/Release/binaries/aeronmd ~/Documents/NEED/Aeron/binaries/ && \
# yes | cp -rpf ~/Documents/aeron4need/cppbuild/Release/binaries/AeronStat ~/Documents/NEED/Aeron/binaries/ && \
# yes | cp -rpf ~/Documents/aeron4need/cppbuild/Release/lib ~/Documents/NEED/Aeron/  && \
# yes | cp -rpf /usr/lib/libbsd.so.0.9.1  ~/Documents/NEED/Aeron/usr/lib/libbsd.so.0.9.1  && \
# yes | cp -rpf /usr/lib/libbsd.so.0  ~/Documents/NEED/Aeron/usr/lib/libbsd.so.0  && \
# tar -zcvf Aeron.tar.gz Aeron  && \
# rm -rf Aeron/


######################################################################################################

cd ~/Documents/NEED/

pip3 wheel --no-deps . . && \
echo $pwdesktop | sudo -S pip3 install --force-reinstall need-2.0-py3-none-any.whl && \
docker build --rm -t need:2.0 .
# docker build --no-cache --rm -t need:2.0 .


#################################################################################################

# docker build --rm -t warpenguin.no-ip.org/alpineclient:1.0 ~/Documents/NEED_Images/samples_need_2_0/alpineclient && \
# docker build --rm -t warpenguin.no-ip.org/alpineserver:1.0 ~/Documents/NEED_Images/samples_need_2_0/alpineserver && \
# docker build --rm -t warpenguin.no-ip.org/logger:1.0 ~/Documents/NEED_Images/samples_need_2_0/logger && \
# docker build --rm -t warpenguin.no-ip.org/dashboard:1.0 ~/Documents/NEED_Images/samples_need_2_0/dashboard && \
# docker build --rm -t warpenguin.no-ip.org/pingclient:vm ~/Documents/NEED_Images/samples_need_2_0/pingclient


# sudo docker build --rm -t warpenguin.no-ip.org/alpineclient:1.0 ~/NEED_Images/samples_need_2_0/alpineclient && \
# sudo docker build --rm -t warpenguin.no-ip.org/alpineserver:1.0 ~//NEED_Images/samples_need_2_0/alpineserver && \
# sudo docker build --rm -t warpenguin.no-ip.org/logger:1.0 ~/NEED_Images/samples_need_2_0/logger && \
# sudo docker build --rm -t warpenguin.no-ip.org/dashboard:1.0 ~//NEED_Images/samples_need_2_0/dashboard && \
# sudo docker build --rm -t warpenguin.no-ip.org/pingclient:vm ~/Documents/NEED_Images/samples_need_2_0/pingclient


#################################################################################################

# cd ~/Documents/NEED/
# 
NEEDdeploymentGenerator examples/topology5.xml -k > topology5.yaml
# NEEDdeploymentGenerator examples/topology100.xml -s > topology100.yaml && \
# NEEDdeploymentGenerator examples/topology200.xml -s > topology200.yaml && \
# NEEDdeploymentGenerator examples/topology400.xml -s > topology400.yaml
# NEEDdeploymentGenerator examples/simple_dynamic.xml -s > simple_dynamic.yaml
# NEEDdeploymentGenerator examples/topology_dynamic.xml -s > topology_dynamic.yaml
# NEEDdeploymentGenerator examples/topology_ring32.xml -s > topology_ring32.yaml
# NEEDdeploymentGenerator examples/topology_ring64.xml -s > topology_ring64.yaml
# NEEDdeploymentGenerator examples/topology_ring128.xml -s > topology_ring128.yaml


########################################################################################

# docker tag need:2.0 localhost:5000/need && \
# docker push localhost:5000/need && \
# docker tag localhost:5000/need need:2.0
# 
# echo -e "\e[92mpass for jet: \e[0m"
# ssh -t daedalus@192.168.2.234 "docker pull leviathan:5000/need && docker tag leviathan:5000/need need:2.0 && echo $pwlaptop | sudo -S systemctl restart docker"


########################################################################################

# rsync -rav -e ssh --exclude='.git*' --exclude='need/TCAL*' --exclude='rebuild.sh' --exclude='.idea' /home/daedalus/Documents/NEED ubuntu@eiger-4.maas:/home/ubuntu/ && \
# rsync -rav -e ssh --exclude='.git*' --exclude='need/TCAL*' --exclude='rebuild.sh' --exclude='.idea' /home/daedalus/Documents/NEED ubuntu@eiger-5.maas:/home/ubuntu/ && \
# rsync -rav -e ssh --exclude='.git*' --exclude='need/TCAL*' --exclude='rebuild.sh' --exclude='.idea' /home/daedalus/Documents/NEED ubuntu@eiger-6.maas:/home/ubuntu/ && \
# rsync -rav -e ssh --exclude='.git*' --exclude='need/TCAL*' --exclude='rebuild.sh' --exclude='.idea' /home/daedalus/Documents/NEED ubuntu@eiger-7.maas:/home/ubuntu/


# rsync -rav -e ssh ubuntu@eiger-4.maas:/tmp/eval /home/daedalus/Documents/benches/scalefree/ && \
# rsync -rav -e ssh ubuntu@eiger-5.maas:/tmp/eval /home/daedalus/Documents/benches/scalefree/ && \
# rsync -rav -e ssh ubuntu@eiger-6.maas:/tmp/eval /home/daedalus/Documents/benches/scalefree/ && \
# rsync -rav -e ssh ubuntu@eiger-7.maas:/tmp/eval /home/daedalus/Documents/benches/scalefree/

########################################################################################

# docker run -d -p 5000:5000 --restart=always --name registry registry:2  && \
# docker swarm init && \
# docker network create --driver=overlay --subnet=10.1.0.0/16 test_overlay


# docker pull leviathan:5000/need && docker tag leviathan:5000/need need:2.0


# docker service rm $(docker service ls -q)

# docker volume rm $(docker volume ls -qf dangling=true)
# docker volume ls -qf dangling=true | xargs -r docker volume rm

# sudo pip install --ignore-installed PyYAML


########################################################################################

# sudo kubeadm reset && \
# sudo iptables -F && sudo iptables -t nat -F && sudo iptables -t mangle -F && sudo iptables -X && \
# sudo swapoff --a && \
# sudo sysctl net.bridge.bridge-nf-call-iptables=1 && \
# sudo kubeadm init --token-ttl=0 && \
# mkdir -p $HOME/.kube && \
# sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config && \
# sudo chown $(id -u):$(id -g) $HOME/.kube/config
# 
# kubectl apply -f "https://cloud.weave.works/k8s/net?k8s-version=$(kubectl version | base64 | tr -d '\n')&env.IPALLOC_RANGE=10.2.0.0/24"
# kubectl taint nodes --all node-role.kubernetes.io/master-
# 
# 
# 
# sudo kubeadm reset && \
# sudo iptables -F && sudo iptables -t nat -F && sudo iptables -t mangle -F && sudo iptables -X && \
# sudo sysctl net.bridge.bridge-nf-call-iptables=1 && \
# sudo swapoff --a
# sudo kubeadm join 172.28.1.234:6443 --token qqikvl.11o8fjbcbz20f2s9     --discovery-token-ca-cert-hash sha256:58bc57e0743042cc3f0260ad4f508deaa66a07149298ba75837feec76fe15bd9
