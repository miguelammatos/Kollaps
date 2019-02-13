#!/bin/sh

pip wheel --no-deps . .

sudo pip install --force-reinstall need-1.1-py3-none-any.whl

docker build --rm -t need:1.1 .


rm *.yaml

NEEDdeploymentGenerator examples/topology5.xml -s > topology5.yaml
NEEDdeploymentGenerator examples/topology5_losses.xml -s > topology5_losses.yaml
NEEDdeploymentGenerator examples/topology100.xml -s > topology100.yaml
NEEDdeploymentGenerator examples/topology_dynamic_links.xml -s > topology_dynamic_links.yaml
NEEDdeploymentGenerator examples/topology_dynamic_replicas.xml -s > topology_dynamic_replicas.yaml
NEEDdeploymentGenerator examples/topology_ping.xml -s > topology_ping.yaml

NEEDdeploymentGenerator examples/topology5.xml -k > ktopology5.yaml
NEEDdeploymentGenerator examples/topology5_losses.xml -k > ktopology5_losses.yaml
NEEDdeploymentGenerator examples/topology100.xml -k > ktopology100.yaml
NEEDdeploymentGenerator examples/topology_dynamic_links.xml -k > ktopology_dynamic_links.yaml
NEEDdeploymentGenerator examples/topology_dynamic_replicas.xml -k > ktopology_dynamic_replicas.yaml
NEEDdeploymentGenerator examples/topology_ping.xml -k > ktopology_ping.yaml


cd ../NEED_Images/samples_need_1_1/

cd alpineclient/
docker build -t <warpenguin.no-ip.org/alpineclient:1.0> .
cd ..

cd alpineserver/
docker build -t warpenguin.no-ip.org/alpineserver:1.0 .
cd ..

cd dashboard/
chmod 400 id_rsa.NEED
docker build -t warpenguin.no-ip.org/dashboard:1.0 .
cd ..

cd logger/
chmod 400 id_rsa.NEED
docker build -t warpenguin.no-ip.org/logger:1.0 .
cd ..



