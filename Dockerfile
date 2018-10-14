FROM alpine:3.8

RUN apk update && \
    apk add --no-cache python3 
           
RUN pip3 install --upgrade pip; \
    pip3 install docker pex

WORKDIR /

ADD ./ /

RUN mkdir -p /opt/NEED/;\
    pex -o /opt/NEED/NEED.pex -D ./NEED dnspython need --python=python3 --not-zip-safe -m need.emucore:main


ENTRYPOINT ["/usr/bin/python3", "/bootstrapper.py"]

CMD ["netsim", "/emucore.py"]
