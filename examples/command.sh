#!/bin/bash
docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$(pwd)/$1":/topology.xml \
    -v "$(pwd)/tmp_result":/result \
    kollaps-deployment-generator:1.0 \
    ["/bin/bash", "-c", "KollapsDeploymentGenerator /topology.xml -s > /result/topology.yaml"]
