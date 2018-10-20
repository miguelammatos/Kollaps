FROM base/archlinux:latest


WORKDIR /

ADD ./ /NEED/

#RUN git clone --branch master --depth 1 --recurse-submodules git@NEED:joaoneves792/NEED.git ;\
RUN pacman -Sy --noconfirm \
    python \
    python-pip \
    make \
    flex \
    bison \
    pkgconf \
    gcc &&\
    make -C /NEED/need/TCAL -j16 &&\
    pip3 --no-cache-dir install dnspython docker wheel &&\
    pip3 --no-cache-dir wheel --no-deps -w /NEED /NEED &&\
    pip3 --no-cache-dir install /NEED/need-1.1-py3-none-any.whl &&\
    rm -rf /NEED &&\
    pip3 --no-cache-dir uninstall -y setuptools wheel pip &&\
    pacman -R --noconfirm make gcc flex bison pkgconf &&\
    pacman -Scc --noconfirm

ENTRYPOINT ["/usr/bin/python3", "/usr/bin/NEEDbootstrapper"]
