FROM alpine:3.9

RUN apk add --no-cache bind-tools \
                 bash \
                 iperf3

ADD ./start.sh /

ENTRYPOINT ["/bin/bash", "/start.sh"]
