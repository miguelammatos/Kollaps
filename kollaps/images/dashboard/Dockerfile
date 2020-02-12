# FROM alpine:3.8
# FROM warpenguin.no-ip.org/alpineclient:1.0
FROM alpine:3.9


RUN apk update && \
    apk add --no-cache python3 \
           build-base \
           python3-dev \
           openssl-dev \
           libffi-dev \
           bash \
           openssh \
           tcpdump

           
WORKDIR /

ADD ./dashboard.sh /

RUN chmod +x /dashboard.sh && \
    pip3 install --upgrade pip && \
    pip3 install dnspython flask docker kubernetes


ENTRYPOINT ["/bin/bash", "/dashboard.sh"]
