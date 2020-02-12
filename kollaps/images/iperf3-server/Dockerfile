FROM alpine:3.9

RUN apk add --no-cache bind-tools \
                 bash \
                 iperf3 \
                 tcpdump


# RUN sysctl net.core.rmem_max=2097152 && \
#    sysctl net.core.wmem_max=2097152
ADD ./server.sh /

#if you don't need tcpdump, just pass ["/usr/bin/iperf3", "-s"] as arguments to ENTRYPOINT
#on k8s, fetch the captures with get_captures.sh

ENTRYPOINT ["/bin/bash", "/server.sh"]
