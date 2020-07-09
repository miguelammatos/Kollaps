## Kollaps: Decentralized Container Based Network Emulator

This README is a quick introduction to get up and running with Kollaps and Thunderstorm.
Kollaps is the decentralized network emulator while Thunderstorm is the high-level language to specify experiments.

#### Videos

A series of videos about Kollaps and Thunderstorm is available [here](https://www.youtube.com/playlist?list=PL23ipsN00zBWMWsTcpkc6B0lAH5pfIwCa).
Check the technical presentations we did at [Eurosys'20](https://youtu.be/Gqvi4WQro2I) and the tutorial presentation at [DISCOTEC'20](https://youtu.be/j5vqLQjtyQo).

*The tutorial below can also be followed in a step-by-step guides available [here](https://youtu.be/GMFvWBTZJ1M) and [here](https://youtu.be/zA18Y9SC2xs).*



#### Paper
Check below for a quick introduction on how to get Kollaps running - more details are available in the [Wiki](https://github.com/miguelammatos/Kollaps/wiki).

The paper describing the system in detail is available [here](https://dl.acm.org/doi/abs/10.1145/3342195.3387540).
If you cite Kollaps you can use the BibTeX below:
```
@inproceedings{10.1145/3342195.3387540,
author = {Gouveia, Paulo and Neves, Jo\~{a}o and Segarra, Carlos and Liechti, Luca and Issa, Shady and Schiavoni, Valerio and Matos, Miguel},
title = {Kollaps: Decentralized and Dynamic Topology Emulation},
year = {2020},
isbn = {9781450368827},
publisher = {Association for Computing Machinery},
address = {New York, NY, USA},
url = {https://doi.org/10.1145/3342195.3387540},
doi = {10.1145/3342195.3387540},
booktitle = {Proceedings of the Fifteenth European Conference on Computer Systems},
articleno = {Article 23},
numpages = {16},
keywords = {emulation, dynamic network topology, experimental reproducibility, distributed systems, containers},
location = {Heraklion, Greece},
series = {EuroSys ’20}
}
```

### Table of Contents:
0. [Prerequisites](#pre)
1. [Installation using Docker images](#docker-install)
2. [Installation from source](#source)

### Prerequisites <a name="pre">
Regardless of what installation method you choose, you will need to have `docker` correctly installed and running on your nodes.
To do so, we recommend following Docker's instructions. Check the official instructions for [Ubuntu](https://docs.docker.com/install/linux/docker-ce/ubuntu/) and [macOS](https://docs.docker.com/docker-for-mac/install/).

Secondly, you just need to clone this repository and its dependencies:
```
git clone --branch master --depth 1 --recurse-submodules https://github.com/miguelammatos/Kollaps.git
```

Lastly, you will need to set-up your container orchestrator of choice.
Currently we support both **Docker Swarm** and **Kubernetes**.
It is important to properly define the environment, follow the instructions from [this file](Orchestrators.md).
    
### Installation Using Docker <a name="docker-install">

This is the recommended and quickest way to get Kollaps running. It only requires to build the two Docker images, as follows:
```
docker build --rm -f dockerfiles/Kollaps -t kollaps:1.0 .
docker build -f dockerfiles/DeploymentGenerator -t kollaps-deployment-generator:1.0 .
```
Now you are ready to test [some applications](examples/).

### Installation from Source <a name="source">

You need a machine running **Linux** with a recent version of **Docker** installed, and **Python 3**.
To run experiments, you need to build the **Kollaps tools** to generate runnable deployment files.

**Installing the Kollaps tools:**

Execute in the root folder (where this README is found):
```
$ pip3 wheel --no-deps . .
$ pip3 install kollaps-1.0-py3-none-any.whl
```
This installs the following tools:
- `KollapsDeploymentGenerator` that translate Kollaps topology descriptions into Docker Swarm Compose files or Kubernetes Manifest files on your local machine.
- `ThunderstormTranslator` command, which lets you declare an experiment in a language with higher-level concepts which are then translated into XML topology descriptions.
Note that the examples below assume both tools are in your PATH, which might require restarting your shell.

The rest of the procedure to test applications is described [here](examples/).
