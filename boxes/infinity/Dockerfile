FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bind9 \
        bind9-utils \
        build-essential \
        gcc \
        libpcap-dev \
        net-tools \
        nginx \
        openssh-server \
        php-cli \
        php-zip \
        procps \
        python3 \
        python3-dev \
        python3-pip \
        python-is-python3 \
        schedtool \
        sudo \
        supervisor \
    && pip3 install --no-cache-dir pcapy-ng \
    && mkdir -p /run/sshd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

COPY . /root/infinity

RUN chmod +x /root/infinity/docker/bootstrap.sh /root/infinity/docker/entrypoint.sh /root/infinity/docker/reset-state.sh \
    && /root/infinity/docker/bootstrap.sh

EXPOSE 22/tcp 53/tcp 53/udp 80/tcp 7171/tcp 8338/tcp

ENTRYPOINT ["/root/infinity/docker/entrypoint.sh"]
