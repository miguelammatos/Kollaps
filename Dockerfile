# base/archlinux is deprecated; replaced with archlinux/base
FROM archlinux/base:latest

# Yes we are using archlinux
# Crazy right? Why not debian or ubuntu or alpine?
# 1st pacman is a lot faster than all the others, so faster image builds
# 2nd alpine uses busybox which is buggy
# 3rd we actually get less packet loss with arch than with any other distros

WORKDIR /

# Location of netem distribution files on archlinux
ENV TC_LIB_DIR "/usr/share/tc/"


RUN pacman -Sy --noconfirm \
    archlinux-keyring  && \
    pacman -Sy --noconfirm \
    python \
    python-pip \
    make \
    gettext \
    flex \
    bison \
    gcc \
    pkgconf \
    iptables \
    iproute2 \
    grep \
    tcpdump \
    iputils



ADD ./ /Kollaps/


# RUN sysctl net.core.rmem_max=2097152 && \
#    sysctl net.core.wmem_max=2097152

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
