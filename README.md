# Kollaps: Decentralized container based network emulator
=====


This README is a quick introduction to run experiments with Kollaps and Thunderstorm.
Kollaps is the decentralized network emulator while Thunderstorm is the high-level language to specify experiments.
For further reference and details, check out the [Kollaps Wiki](https://github.com/miguelammatos/Kollaps/wiki)

## Prerequisites
- Clone this repo with:
```
$git clone --branch master --depth 1 --recurse-submodules https://github.com/miguelammatos/Kollaps.git
```
- You need a machine running **Linux** with a recent version of **Docker** installed, and **Python 3**.
- To run experiments, you need to build the **Kollaps tools** to generate runnable deployment files and the  **Kollaps image** as detailed below.
- You also need to build the **Docker images** for the applications in your experiment. We provide some example images along with our example experiments.
- Kollaps experiments rely on a container orchestrator. At the moment, **Docker Swarm** and **Kubernetes** are supported. We describe the workflow for both of these in detail below.

### Installing the Kollaps tools
Execute in the root folder (where this README is found):
```
$ pip3 wheel --no-deps . .
$ pip3 install kollaps-1.0-py3-none-any.whl
```
This installs the following tools:
- `KollapsDeploymentGenerator` that translate Kollaps topology descriptions into Docker Swarm Compose files or Kubernetes Manifest files on your local machine.
- `ThunderstormTranslator` command, which lets you declare an experiment in a language with higher-level concepts which are then translated into XML topology descriptions.
- Note that the examples below assume both tools are in your PATH, which might require restarting your shell.

### Building the Kollaps image
You also need to build the Kollaps Docker image. To do so, execute in this folder:
```
$ docker build --rm -t kollaps:1.0 .
```
