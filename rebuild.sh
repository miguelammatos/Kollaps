#!/bin/sh


docker stack rm 5
docker rm $(docker ps -aq)


cd ~/Documents/aeron4need/
# ./cppbuild/cppbuild

yes | cp -rpf ~/Documents/aeron4need/cppbuild/Release/ ~/Documents/NEED/Aeron/
yes | cp -rpf /usr/lib/libbsd.so.0.9.1  ~/Documents/NEED/Aeron/usr/lib/libbsd.so.0.9.1
yes | cp -rpf /usr/lib/libbsd.so.0  ~/Documents/NEED/Aeron/usr/lib/libbsd.so.0



cd ~/Documents/NEED/

pip wheel --no-deps . .
sudo pip install --force-reinstall need-2.0-py3-none-any.whl


docker build --rm -t need:2.0 .

NEEDdeploymentGenerator examples/topology5.xml > topology5.yaml
NEEDdeploymentGenerator examples/topology100.xml > topology100.yaml


cd ../NEED_Images/samples_need_1_1/

cd alpineclient/
docker build -t warpenguin.no-ip.org/alpineclient:1.0 .
cd ..

cd alpineserver/
docker build -t warpenguin.no-ip.org/alpineserver:1.0 .
cd ..

cd logger/
chmod 400 id_rsa.NEED
docker build -t warpenguin.no-ip.org/logger:1.0 .
cd ..

cd dashboard/
chmod 400 id_rsa.NEED
docker build -t warpenguin.no-ip.org/dashboard:1.0 .
cd ..



docker tag need:2.0 localhost:5000/need && \
docker push localhost:5000/need
docker tag localhost:5000/need need:2.0

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


