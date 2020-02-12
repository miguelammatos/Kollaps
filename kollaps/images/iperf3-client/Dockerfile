FROM alpine:3.9

RUN apk add --no-cache \
                bind-tools \
	            bash \
                iperf3 \
                tcpdump
                   
ADD ./client.sh /

# RUN sysctl net.core.rmem_max=2097152 && \
#    sysctl net.core.wmem_max=2097152

ENTRYPOINT ["/bin/bash", "/client.sh"]
