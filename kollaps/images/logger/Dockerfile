# FROM alpine:3.8
# FROM warpenguin.no-ip.org/alpineclient:1.0
FROM alpine:3.9


RUN apk update && \
    apk add --no-cache python3 \
           openssh \
           py3-dnspython \
           docker-py \
           bash
    
    
WORKDIR /

ADD ./logger.sh /
    
RUN chmod +x /logger.sh && \
    pip3 install --upgrade pip && \
    pip3 install dnspython docker kubernetes

    
# ENV PYTHONPATH="/NEED"


ENTRYPOINT ["/bin/bash", "/logger.sh"]

