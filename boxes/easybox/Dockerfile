FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server supervisor nano curl net-tools \
    && mkdir -p /run/sshd /var/log/supervisor \
    && rm -rf /var/lib/apt/lists/*

# Create user
RUN useradd -m -s /bin/bash hacker && echo "hacker:hacker123" | chpasswd
RUN echo "KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256" >> /etc/ssh/sshd_config

# Hide flag
RUN echo "FLAG01{placeholder}" > /home/hacker/user.txt && chown hacker:hacker /home/hacker/user.txt
RUN echo "FLAG02{placeholder}" > /root/root.txt

COPY docker/supervisord.conf /etc/supervisor/conf.d/easybox.conf
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/entrypoint.sh"]
