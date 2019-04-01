#!/bin/sh


########### reset kubernetes ########################################################################


# sudo swapoff --a && \
# sudo kubeadm reset && \
# sudo sysctl net.bridge.bridge-nf-call-iptables=1 && \
# sudo kubeadm init --token-ttl=0 && \
# mkdir -p $HOME/.kube && \
# sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config && \
# sudo chown $(id -u):$(id -g) $HOME/.kube/config && \
# kubectl apply -f "https://cloud.weave.works/k8s/net?k8s-version=$(kubectl version | base64 | tr -d '\n')" && \
# kubectl taint nodes --all node-role.kubernetes.io/master-



######################################################################################################

# sudo docker stack rm top
# sudo docker rm $(docker ps -aq)
# 
# 
# yes | cp -rpf ~/Documents/aeron4need/cppbuild/Release/binaries/ ~/Documents/NEED/Aeron/
# yes | cp -rpf ~/Documents/aeron4need/cppbuild/Release/lib/ ~/Documents/NEED/Aeron/
# yes | cp -rpf /usr/lib/libbsd.so.0.9.1  ~/Documents/NEED/Aeron/usr/lib/libbsd.so.0.9.1
# yes | cp -rpf /usr/lib/libbsd.so.0  ~/Documents/NEED/Aeron/usr/lib/libbsd.so.0

# tar -zcvf Aeron.tar.gz Aeron



######################################################################################################

cd ~/Documents/NEED/

pip3 wheel --no-deps . .
sudo pip3 install --force-reinstall need-2.0-py3-none-any.whl


sudo docker build --rm -t need:2.0 .
# docker build --no-cache --rm -t need:2.0 .

NEEDdeploymentGenerator examples/topology5.xml -k > topology5.yaml
NEEDdeploymentGenerator examples/topology100.xml -k > topology100.yaml
NEEDdeploymentGenerator examples/simple_dynamic.xml -k > simple_dynamic.yaml


cd /home/derp/Documents/NEED_Images/samples_need_2_0/

cd alpineclient/
sudo docker build --rm -t warpenguin.no-ip.org/alpineclient:1.0 .
cd ..

cd alpineserver/
sudo docker build --rm -t warpenguin.no-ip.org/alpineserver:1.0 .
cd ..

cd logger/
chmod 400 id_rsa.NEED
sudo docker build --rm -t warpenguin.no-ip.org/logger:1.0 .
cd ..

cd dashboard/
chmod 400 id_rsa.NEED
sudo docker build --rm -t warpenguin.no-ip.org/dashboard:1.0 .
cd ..



# docker tag need:2.0 localhost:5000/need && \
# docker push localhost:5000/need
# docker tag localhost:5000/need need:2.0





########################################################################################

# docker tag warpenguin.no-ip.org/dashboard:1.0 localhost:5000/warpenguin.no-ip.org/dashboard && \
# docker push localhost:5000/warpenguin.no-ip.org/dashboard
# docker tag localhost:5000/warpenguin.no-ip.org/dashboard warpenguin.no-ip.org/dashboard:1.0


# docker pull leviathan:5000/need && \
# docker tag leviathan:5000/need need:2.0 && \
# docker pull leviathan:5000/warpenguin.no-ip.org/dashboard && \
# docker tag leviathan:5000/warpenguin.no-ip.org/dashboard warpenguin.no-ip.org/dashboard:1.0

# ssh daedalus@jet docker pull leviathan:5000/need && docker tag leviathan:5000/need need:2.0

# docker stack rm __deployed_name__

# docker rm $(docker ps -aq)

# docker service rm $(docker service ls -q)

# docker volume rm $(docker volume ls -qf dangling=true)
# docker volume ls -qf dangling=true | xargs -r docker volume rm


