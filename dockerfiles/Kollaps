FROM archlinux/base:latest

WORKDIR /

# Location of netem distribution files on archlinux
ENV TC_LIB_DIR "/usr/share/tc/"

RUN pacman -Sy --noconfirm \
    archlinux-keyring  && \
    pacman -Sy --noconfirm \
    bison \
    flex \
    gcc \
    gettext \
    grep \
    iproute2 \
    iputils \
    iptables \
    make \
    pkgconf \
    python \
    python-pip \
    tcpdump 

ADD ./ /Kollaps/

RUN tar -C /Kollaps/ -zxvf Kollaps/Aeron.tar.gz && \
  cp -r /Kollaps/Aeron/binaries /usr/bin/Aeron && \
    mkdir -p /home/daedalus/Documents/aeron4need/cppbuild/Release/ && \
    cp -r /Kollaps/Aeron/lib /home/daedalus/Documents/aeron4need/cppbuild/Release/lib && \
    cp /Kollaps/Aeron/usr/lib/libbsd.so.0.9.1 /usr/lib/libbsd.so.0.9.1 && \
    cp /Kollaps/Aeron/usr/lib/libbsd.so.0 /usr/lib/libbsd.so.0 && \
    rm -f Aeron.tar.gz

# LL: only added kubernetes in l.33
RUN make -C /Kollaps/pid1 && \
    cp /Kollaps/pid1/pid1 /usr/bin/pid1 && \
    make -C /Kollaps/kollaps/TCAL -j8 && \
    pip3 --no-cache-dir install wheel dnspython flask docker kubernetes netifaces && \
    pip3 --no-cache-dir wheel --no-deps -w /Kollaps /Kollaps && \
    pip3 --no-cache-dir install /Kollaps/kollaps-1.0-py3-none-any.whl && \
    rm -rf /Kollaps && \
    pip3 --no-cache-dir uninstall -y setuptools wheel pip && \
    pacman -R --noconfirm make gcc flex bison pkgconf && \
    pacman -Scc --noconfirm

ENTRYPOINT ["/usr/bin/pid1", "/usr/bin/python3", "-m", "kollaps.bootstrapper"]
