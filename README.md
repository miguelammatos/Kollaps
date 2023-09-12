## Kollaps: Decentralized Container Based Network Emulator

This README is a quick introduction to get up and running with Kollaps and Thunderstorm.
Kollaps is the decentralized network emulator while Thunderstorm is the high-level language to specify experiments.
Kollaps currently only functions in machines with the Native Linux Kernel (minimium version:5.15.0) due to the usage of both eBPF and Linux traffic control.

### Documentation
For extra documentation on how to use Kollaps you can check our [website](https://kollaps.dev/).

### Contact Us
If you want to discuss or have problems using Kollaps, we have a discord channel, join us [here](https://discord.gg/cHMphzMMUZ).

### Quick Start

The easier way to get up and running with Kollaps is to clone the project, build
the docker images, and run experiments locally in a docker swarm.

When checking out the code, make sure you install the submodules as well:
```
git clone --branch master --depth 1 --recurse-submodules https://github.com/miguelammatos/Kollaps.git
cd Kollaps
```

Then build the docker images:
```
export DOCKER_BUILDKIT=1
docker build --rm -f dockerfiles/Kollaps -t kollaps:2.0 .
docker build -f dockerfiles/DeploymentGenerator -t kollaps-deployment-generator:2.0 .
```

Initialise the swarm and create an overlay network:
```
docker swarm init
docker network create --driver=overlay --subnet=10.1.0.0/24 kollaps_network
```
For topologies with more then 257 services use:
```
docker network create --driver=overlay --subnet=11.1.0.0/20 kollaps_network
```


Lastly run a simple experiment:
```
# Create topology file and experiment images
cd examples
./KollapsDeploymentGenerator ./iperf3/topology.xml -s topology.yaml
./KollapsAppBuilder iperf3

# Deploy experiment
docker stack deploy -c topology.yaml kollaps_example

# Open a browser and navigate to http://127.0.0.1:8088/
# Click `start` when all experiments are `ready`

# Remove the experiment
docker stack rm kollaps_example
```


### Cite the work

You may want to check the paper describing the system in detail which appeared
in [EUROSYS'20](https://dl.acm.org/doi/abs/10.1145/3342195.3387540).
Or cite it:
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

<!-- ### Other links

+ [Installation](./docs/install.md) - step by step installation guide.
+ [Orchestrators](./docs/orchestrators.md) - container orchestrators supported in Kollaps, and new in 2.0 Baremetal
+ [Examples](./examples/README.md) - list of example applications to test Kollaps.
+ [Videos](./docs/videos.md) - a collection of talks and tutorials.
+ [Wiki](https://github.com/miguelammatos/Kollaps/wiki) - project's wiki page. -->
