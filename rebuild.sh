#!/bin/sh

pip wheel --no-deps . .

sudo pip install --force-reinstall need-2.0-py3-none-any.whl

docker build --rm -t need:2.0 .

NEEDdeploymentGenerator examples/topology5.xml > topology5.yaml


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




# (cd ../NEED_Images/samples_need_1_1/alpineclient/ && docker build -t warpenguin.no-ip.org/alpineclient:1.0 .)

# docker stack rm __deployed_name__
# docker rm $(docker ps -aq)

