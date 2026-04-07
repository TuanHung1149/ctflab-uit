#!/usr/bin/env bash

set -euo pipefail

cd /root/infinity

if [ -f ./.env ]; then
  set -a
  . ./.env
  set +a
fi

: "${BOX_TITLE:=Nebula Nexus}"
: "${BASE_DOMAIN:=nebula.lab}"
: "${TXT_SUBDOMAIN:=unk}"
: "${FILE_SUBDOMAIN:=inffile123}"
export BOX_TITLE BASE_DOMAIN TXT_SUBDOMAIN FILE_SUBDOMAIN

mapfile -t flags < flags.txt

printf '%s\n' "${flags[2]}" > ./chall3/tinyfilemanager/infinity.txt
printf '%s\n' "${flags[3]}" > ./chall4/flag.txt
printf '%s\n' "${flags[4]}" > ./chall5/flag.txt
printf '%s\n' "${flags[5]}" > ./chall6/flag.txt
printf '%s\n' "${flags[6]}" > ./chall7/flag.txt

declare -A creds=(
  [taylor]="lekkerding"
  [brown]="AI56JSPUac43v7MWkXdG"
  [john]="S6V1frkRJLo40GKuglzp"
)

for user_name in "${!creds[@]}"; do
  if ! id -u "$user_name" >/dev/null 2>&1; then
    useradd -m -s /bin/bash "$user_name"
    echo "${user_name}:${creds[$user_name]}" | chpasswd
    ln -fs /dev/null "/home/${user_name}/.bash_history"
  else
    echo "${user_name}:${creds[$user_name]}" | chpasswd
  fi
done

usermod -c 'TinyFileManager Administrator' taylor
usermod -c 'MalTrail Administrator' brown
usermod -c 'Information Asset Manager' john

mkdir -p /opt
cp -r ./chall1 /opt/chall1
cp -r ./chall3 /opt/chall3
cp -r ./chall5 /opt/chall5
cp -r ./chall7 /opt/chall7
mkdir -p /opt/chall3/tinyfilemanager/data

python3 - <<'PY'
from pathlib import Path
import os
base_domain = os.environ["BASE_DOMAIN"]
flag = Path("/root/infinity/flags.txt").read_text().splitlines()[0].strip()
path = Path("/opt/chall1/server.py")
text = path.read_text()
text = text.replace('FLAG = "INF01{XXXXXXXX}"', f'FLAG = "{flag}"')
text = text.replace("[infinity.insec]", f"[{base_domain}]")
path.write_text(text)
PY

cp ./chall4/flag.txt /home/taylor/user.txt
chown root:taylor /home/taylor/user.txt

cp ./chall6/flag.txt /home/john/flag.txt
cp ./chall6/getinfo.sh /home/john/getinfo.sh
chown root:john /home/john/flag.txt /home/john/getinfo.sh
chmod 750 /home/john/getinfo.sh

sed -E "s/\[name\]/john/g" ./chall6/sysinfo.c > /tmp/sysinfo.c
gcc /tmp/sysinfo.c -o /usr/local/bin/sysinfo
rm -f /tmp/sysinfo.c
chown root:brown /usr/local/bin/sysinfo
chmod 4750 /usr/local/bin/sysinfo
touch -r /usr/bin/bash /usr/local/bin/sysinfo

gcc /opt/chall7/rootnow.c -fno-stack-protector -o /opt/chall7/rootnow
mv /opt/chall7/flag.txt /root/root.txt
chown -R root:john /opt/chall7
chmod -R 750 /opt/chall7
chmod 700 /opt/chall7/rootnow.c

if ! grep -q '^john ALL=(ALL) NOPASSWD: /opt/chall7/rootnow$' /etc/sudoers; then
  printf '\njohn ALL=(ALL) NOPASSWD: /opt/chall7/rootnow\n' >> /etc/sudoers
fi
visudo -c

mkdir -p /etc/bind/zones
cat > /etc/bind/named.conf.local <<EOF
zone "${BASE_DOMAIN}" {
    type primary;
    file "/etc/bind/zones/db.${BASE_DOMAIN}";
    allow-transfer {any;};
};

zone "${TXT_SUBDOMAIN}.${BASE_DOMAIN}" {
    type primary;
    file "/etc/bind/zones/db.${TXT_SUBDOMAIN}.${BASE_DOMAIN}";
    allow-transfer {none;};
};
EOF

cat > /etc/bind/zones/db.${BASE_DOMAIN} <<EOF
\$TTL    604800
@       IN      SOA     ns1.${BASE_DOMAIN}. admin.${BASE_DOMAIN}. (
                  3
             604800
              86400
            2419200
             604800 )
;
     IN      NS      ns1.${BASE_DOMAIN}.
     IN      NS      ns2.${BASE_DOMAIN}.

ns1.${BASE_DOMAIN}.          IN      A       10.1.1.3
ns2.${BASE_DOMAIN}.          IN      A       10.1.1.4

${TXT_SUBDOMAIN}.${BASE_DOMAIN}.        IN      A      127.0.0.1
${FILE_SUBDOMAIN}.${BASE_DOMAIN}.       IN      A      127.0.0.1
EOF

cat > /etc/bind/zones/db.${TXT_SUBDOMAIN}.${BASE_DOMAIN} <<EOF
\$TTL    604800
@       IN      SOA     ns1.${BASE_DOMAIN}. admin.${BASE_DOMAIN}. (
                  3
             604800
              86400
            2419200
             604800 )
;
     IN      NS      ns1.${BASE_DOMAIN}.
     IN      NS      ns2.${BASE_DOMAIN}.

@ 3600 IN TXT "${flags[1]}"
EOF

sed -i 's/^HTTP_ADDRESS .*/HTTP_ADDRESS 0.0.0.0/' /opt/chall5/maltrail.conf
chown -R root:brown /opt/chall5
chmod -R 750 /opt/chall5

mkdir -p /var/log/supervisor /var/log/infinity /run/named /run/sshd

# Generate SSH host keys
ssh-keygen -A

# Enable password auth for SSH
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config
echo "PermitRootLogin no" >> /etc/ssh/sshd_config

cp ./chall3/tinyfilemanager/tinyfilemanager.php /opt/chall3/tinyfilemanager/index.php
cp ./chall3/tinyfilemanager/translation.json /opt/chall3/tinyfilemanager/translation.json
cp ./chall3/tinyfilemanager/infinity.txt /opt/chall3/tinyfilemanager/infinity.txt
sed -i "s/\$root_path =.*;/\$root_path = \$_SERVER['DOCUMENT_ROOT'].'\/data';/g" /opt/chall3/tinyfilemanager/index.php
sed -i "s/\$root_url = '';/\$root_url = 'data\/';/g" /opt/chall3/tinyfilemanager/index.php
chmod 777 /opt/chall3/tinyfilemanager/data
cp ./chall3/tinyfilemanager/php-disable-function.ini /etc/php/8.1/cli/conf.d/99-disable-functions.ini

python3 - <<'PY'
from pathlib import Path
import os
replacements = {
    "__BOX_TITLE__": os.environ["BOX_TITLE"],
    "__BASE_DOMAIN__": os.environ["BASE_DOMAIN"],
    "__TXT_SUBDOMAIN__": os.environ["TXT_SUBDOMAIN"],
    "__FILE_SUBDOMAIN__": os.environ["FILE_SUBDOMAIN"],
}
for src, dst in [
    ("/root/infinity/docker/nginx/infinity.conf", "/etc/nginx/sites-available/infinity.conf"),
    ("/root/infinity/docker/nginx/landing.html", "/var/www/html/index.html"),
]:
    text = Path(src).read_text()
    for old, new in replacements.items():
        text = text.replace(old, new)
    Path(dst).write_text(text)
PY
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/infinity.conf /etc/nginx/sites-enabled/infinity.conf

install -m 644 ./docker/supervisord.conf /etc/supervisor/conf.d/infinity.conf

# Fix SSH kex for VPN compatibility
echo "KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256" >> /etc/ssh/sshd_config
