## Step-by-step installation

### Prerequisites <a name="pre">
Regardless of what orchestration method you choose, you will need to have `docker` correctly installed and running on your nodes.
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
export DOCKER_BUILDKIT=1
docker build --rm -f dockerfiles/Kollaps -t kollaps:2.0 .
docker build -f dockerfiles/DeploymentGenerator -t kollaps-deployment-generator:2.0 .
```
Now you are ready to test [some applications](../examples/).

### Installation from Source <a name="source">

You need a machine running **Linux** with a recent version of **Docker** installed, and **Python 3**.
To run experiments, you need to build the **Kollaps tools** to generate runnable deployment files.

**Installing the Kollaps tools:**

Execute in the root folder (where this README is found):
```
pip3 wheel --no-deps . .
pip3 install kollaps-2.0-py3-none-any.whl
```
This installs the following tools:
- `KollapsDeploymentGenerator` that translate Kollaps topology descriptions into Docker Swarm Compose files or Kubernetes Manifest files on your local machine.
- `ThunderstormTranslator` command, which lets you declare an experiment in a language with higher-level concepts which are then translated into XML topology descriptions.
Note that the examples below assume both tools are in your PATH, which might require restarting your shell.

The rest of the procedure to test applications is described [here](../examples/).