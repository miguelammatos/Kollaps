# NEED
Decentralized container based network emulator

Clone this repo with:
```
git clone --branch master --depth 1 --recurse-submodules https://github.com/joaoneves792/NEED.git
```


## Install instructions
```
$pip wheel --no-deps . .
$pip install need-1.1-py3-none-any.whl
```

## How to use
You need to build the need docker image, to do so execute on this folder:
```
docker build --rm -t need:1.1 .
```

Installing the package should give you access to the NEEDdeploymentGenerator command to translate need topology descritions into Docker Swarm Compose files.

Example:
```
NEEDdeploymentGenerator topology5.xml > topology5.yaml
```

This can then be deployed with:
```
docker stack deploy -c topology5.yaml 5
```

After the experiment is deployed, the dashboard should be accessible on http://127.0.0.1:8088
