# NEED

# How to use

1. Create a docker swarm network (only overlay and macvlan have been tested) (check cluster-deployments/ansible/network for a playbook for configuring a swarm macvlan network on a cluster)

2. Write a topology file or use one from the tests folder. (The network attribute of all the links must correspond to an existing docker swarm network configuration.) (All the links must use the same network, this is due to a current limitation of TCAL)

## Building the images

3. Build the privilegedbootstrapper image (in cluster-deployments/docker/tc/bootstrapper) it must be tagged: warpenguin.no-ip.org/privilegedbootstrapper:1.3

4. Build the dashboard image (located in cluster-deployments/docker/need/dashboard) it can have any tag as long as it matches the one used in the topology xml file.

Optional (build images for iperf client and server)

4.1 Build the service image (located in cluster-deployments/docker/need/service) it must have the tag warpenguin.no-ip.org/service:1.0 (because the client image depends on this one)

4.2 Build the client image (located in cluster-deployments/docker/need/client) the tag should match the one used in the xml topology file

4.3 Build the server image (located in cluster-deployments/docker/need/server), this image depends on the client image so make sure the Dockerfile entry FROM uses the client image previously built.

## Deploying an experiment

5. cd into this repository's folder and execute: 
```bash
$ ./deploymentGenerator.py topology_file.xml > output_file.yaml
```
  (Notice the output redirection, the deployment generator writes the deployment to the standard output, and a brief description or errors to the standard error)
  
6. execute:
```bash
$ docker stack deploy -c deployment_file.yaml arbitrary_name_for_the_stack
```
  
7. Access to the dashboard is required to start and stop the experiments.
   Once the dashboard container has started the dashboard should be available on http://(ip of any machine in the Swarm):8088
 
8. Wait until all services on the dashboard show their status is "Ready"

9. Click the START link on the top right

## Finishing an experiment

10. At any time you can stop an experiment by clicking the STOP link on the top right of the dashboard.

11. Once all services show their status as "Down" you can remove the containers by executing:
```bash
$ docker stack rm name_of_the_stack
```
  
# VERY IMPORTANT NOTICE!!!

Due to a bug in the linux kernel DO NOT remove the containers before all services show up on the dashboard as "Down"

Doing so can cause corruption of the Host's kernel and lead to kernel panics or unspecified behaviour!!!

If for some reason this situation occurs, reboot the machine immediatelly.

It is possible that after rebooting the docker network used for deploying the experiments becomes unusable (no containers can be attached to it, and it can't be deleted)
To fix it you must stop the docker daemon and delete the following file:
/var/lib/docker/network/files/local-kv.db 
And then restart the docker daemon. (This will delete all network configurations on that host)
