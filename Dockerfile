
# base/archlinux is deprecated; replaced with archlinux/base
FROM archlinux/base:latest

#Yes we are using archlinux
#Crazy right? Why not debian or ubuntu or alpine?
#1st pacman is a lot faster than all the others, so faster image builds
#2nd alpine uses busybox which is buggy
#3rd we actually get less packet loss with arch than with any other distros

WORKDIR /

#Location of netem distribution files on archlinux
ENV TC_LIB_DIR "/usr/share/tc/"


RUN pacman -Sy --noconfirm \
    archlinux-keyring  && \
    pacman -Sy --noconfirm \
    python \
    python-pip \
    make \
    flex \
    bison \
    pkgconf \
    iptables \
    iproute2 \
    gcc \
    grep \
    tcpdump

    
ADD ./ /NEED/


RUN tar -C /NEED/ -zxvf NEED/Aeron.tar.gz && \
	cp -r /NEED/Aeron/binaries /usr/bin/Aeron && \
    mkdir -p /home/daedalus/Documents/aeron4need/cppbuild/Release/ && \
    cp -r /NEED/Aeron/lib /home/daedalus/Documents/aeron4need/cppbuild/Release/lib && \
    cp /NEED/Aeron/usr/lib/libbsd.so.0.9.1 /usr/lib/libbsd.so.0.9.1 && \
    cp /NEED/Aeron/usr/lib/libbsd.so.0 /usr/lib/libbsd.so.0
    
RUN make -C /NEED/pid1 && \
    cp /NEED/pid1/pid1 /usr/bin/pid1 && \
    make -C /NEED/need/TCAL -j8 && \
    pip3 --no-cache-dir install wheel dnspython flask docker kubernetes && \
    pip3 --no-cache-dir wheel --no-deps -w /NEED /NEED && \
    pip3 --no-cache-dir install /NEED/need-2.0-py3-none-any.whl && \
    rm -rf /NEED && \
    pip3 --no-cache-dir uninstall -y setuptools wheel pip && \
    pacman -R --noconfirm make gcc flex bison pkgconf && \
    pacman -Scc --noconfirm

    
ENTRYPOINT ["/usr/bin/pid1", "/usr/bin/python3", "-m", "need.bootstrapper"]


#RUN git clone --branch master --depth 1 --recurse-submodules git@NEED:joaoneves792/NEED.git ;\


