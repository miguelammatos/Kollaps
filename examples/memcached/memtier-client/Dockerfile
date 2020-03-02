FROM alpine:3.9

RUN apk add --no-cache \
                bind-tools \
	        bash \
		libstdc++ \ 
		libressl \
		libevent

ADD ./memtier_benchmark /                  
ADD ./client.sh /

ENTRYPOINT ["/bin/bash", "/client.sh"]
