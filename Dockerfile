FROM base/archlinux:latest
#Yes we are using archlinux
#Crazy right? Why not debian or ubuntu or alpine?
#1st pacman is a lot faster than all the others, so faster image builds
#2nd alpine uses busybox which is buggy
#3rd we actually get less packet loss with arch than with any other distros

WORKDIR /

RUN pacman -Sy --noconfirm \
    python \
    python-pip \
    make \
    flex \
    bison \
    pkgconf \
    iptables \
    gcc

#RUN git clone --branch master --depth 1 --recurse-submodules git@NEED:joaoneves792/NEED.git ;\
ADD ./ /NEED/

RUN make -C /NEED/pid1 &&\
    cp /NEED/pid1/pid1 /usr/bin/pid1 &&\
    make -C /NEED/need/TCAL -j8 &&\
    pip3 --no-cache-dir install dnspython docker wheel &&\
    pip3 --no-cache-dir wheel --no-deps -w /NEED /NEED &&\
    pip3 --no-cache-dir install /NEED/need-1.1-py3-none-any.whl &&\
    rm -rf /NEED &&\
    pip3 --no-cache-dir uninstall -y setuptools wheel pip &&\
    pacman -R --noconfirm make gcc flex bison pkgconf &&\
    pacman -Scc --noconfirm

ENTRYPOINT ["/usr/bin/pid1", "/usr/bin/python3", "-m", "need.bootstrapper"]
