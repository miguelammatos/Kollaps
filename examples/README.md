## Kollaps Example Applications
=====

This folder contains several example images to illustrate the usage of Kollaps.

=====
**Table of Contents:**
1. [Basic Usage](#basic-usage)
2. [iPerf3](#iperf)
3. [Redis](#redis)
=====

<a name="basic-usage"/>
**1. Basic Usage:**

We provide two convenience scripts in order to generate the required images for each application together with their deployment file.

Inside each application's folder, you will find a sample `topology.xml` that specifies the topology to be emulated.
Feel free to modify those at will, in particular, if you are interested in experimenting with different network shapes, modify the `<bridges>` and `links` section.
The `<dynamic>` section can be used to simulate dynamic behavious of the experiment.

Once you are content with your topology file, you can generate the `.yaml` required for the deployment using the following command for **Docker Swarm** deployments:
```
KollapsDeploymentGenerator ./<app_name>/topology.xml -s ./<app_name>/<your_experiment_name>.yaml
```

Or the following one for **Kubernetes** (note that we just change the flag):
```
KollapsDeploymentGenerator ./<app_name>/topology.xml -k ./<app_name>/<your_experiment_name>.yaml
```

Now you are ready to build the service images to launch and emulate your application with Kollaps.

<a name="basic-usage"/>
**2. iPerf3:**

In this experiment (in the default setting) we set up three [iPerf3](https://iperf.fr/) clients which will connect to three different iPerf3 servers. Each client will try to saturate the bandwidth for 100 seconds and stop.

Check the shell scripts under the *iperf3-client* and *iperf3-server* directory for further details.

In order to build the images run:


- redis: experiment that uses the Redis database
