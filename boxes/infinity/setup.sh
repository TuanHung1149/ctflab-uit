#!/bin/bash

# stop execute on error
set -e

# check root privilege
if [ "$EUID" -ne 0 ]
then
    echo "Please run as root."
    exit
fi


flags=()

while IFS= read -r line; do
  flags+=("$line")
done < flags.txt

# setup flag
sed -i -E "s/INF01\{\w*\}/${flags[0]}/" ./chall1/server.py
sed -i -E "s/INF02\{\w*\}/${flags[1]}/" ./chall2/zones/db.unk.infinity.insec
echo "${flags[2]}" > ./chall3/tinyfilemanager/infinity.txt
echo "${flags[3]}" > ./chall4/flag.txt
echo "${flags[4]}" > ./chall5/flag.txt
echo "${flags[5]}" > ./chall6/flag.txt
echo "${flags[6]}" > ./chall7/flag.txt

# create link to python3
if ! which python >& /dev/null;
then
    ln -s /usr/bin/python3 /usr/bin/python
fi

# setup for user ltn0tbug
# ln -fs /dev/null /home/ltn0tbug/.bash_history
# echo -e "E&QvWiA8kJ\nE&QvWiA8kJ" | passwd ltn0tbug 2>/dev/null
# usermod -c 'Nobody' ltn0tbug

# setup working var
SPATH="/opt"
RUSER="root"

SUSER_CHALL4="taylor"
SUSER_CHALL5="brown"
SUSER_CHALL6="john"

declare -A CREDS
CREDS[$SUSER_CHALL4]="lekkerding" 
CREDS[$SUSER_CHALL5]="AI56JSPUac43v7MWkXdG" 
CREDS[$SUSER_CHALL6]="S6V1frkRJLo40GKuglzp" 
# Setup user

# create user if not exist
for user_name in "${!CREDS[@]}"
do
    if ! cat /etc/passwd | grep "$user_name:" >& /dev/null;
    then 
            repass=$(perl -e 'print crypt($ARGV[0], "fs8ktf")' "${CREDS[$user_name]}")
            useradd -m -s /bin/bash -p "$repass" "$user_name"
            if [ $? -eq 0 ]
            then
                    echo "$user_name has been added to system."
                    ln -fs /dev/null /home/$user_name/.bash_history
            else
                    echo "Failed to add the user: $user_name."
                    exit 1
            fi
    fi
done

usermod -c 'TinyFileManager Administrator' $SUSER_CHALL4
usermod -c 'MalTrail Administrator' $SUSER_CHALL5
usermod -c 'Information Asset Manager' $SUSER_CHALL6





# install dns service
DEBIAN_FRONTEND=noninteractive apt install bind9 bind9utils bind9-doc -y

# install maltrail service
DEBIAN_FRONTEND=noninteractive apt install git python3-dev python3-pip python-is-python3 libpcap-dev build-essential procps schedtool -y
sudo -u $SUSER_CHALL5 pip3 install pcapy-ng

# install docker
if ! which docker >& /dev/null;
then
    echo "Install docker..."
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    DEBIAN_FRONTEND=noninteractive apt install apt-transport-https ca-certificates curl gnupg lsb-release -y
    DEBIAN_FRONTEND=noninteractive apt update
    DEBIAN_FRONTEND=noninteractive apt install docker-ce docker-ce-cli containerd.io -y
fi

# install docker-compose
if ! which docker-compose >& /dev/null;
then
    echo "Install docker-compose..."
    curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi



# setup challenge 1
echo "[+] Setting challenge 1"
cp -r ./chall1 $SPATH
chmod -R 750 $SPATH/chall1
cat <<EOF > chall1.service
[Unit]
Description=Start Bot killer service

[Service]
User=${RUSER}
ExecStart=bash -c 'cd ${SPATH}/chall1 && python -u ./server.py'
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
EOF

cp chall1.service /etc/systemd/system
systemctl enable chall1.service

# setup challenge 2
echo "[+] Setting challenge 2"
cp -r ./chall2/* /etc/bind
systemctl restart bind9

# setup challenge 3
echo "[+] Setting challenge 3"
cp -r ./chall3 $SPATH
chmod -R 750 $SPATH/chall3
cd $SPATH/chall3
docker-compose build
cat <<EOF > chall3.service
[Unit]
Description=Start Tiny File Manager web application

[Service]
User=${RUSER}
ExecStart=bash -c 'cd ${SPATH}/chall3 && docker-compose up'
Restart=always

[Install]
WantedBy=multi-user.target
EOF

cp chall3.service /etc/systemd/system
systemctl enable chall3.service
cd /root/infinity

# setup challenge 4
echo "[+] Setting challenge 4"
cp ./chall4/flag.txt /home/$SUSER_CHALL4/user.txt
chown $RUSER:$SUSER_CHALL4 /home/$SUSER_CHALL4/user.txt

# setup challenge 5
echo "[+] Setting challenge 5"
cp -r ./chall5 $SPATH
chmod -R 750 $SPATH/chall5
chown -R $RUSER:$SUSER_CHALL5 $SPATH/chall5
cat <<EOF > chall5-server.service
[Unit]
Description=Maltrail. Server of malicious traffic detection system

[Service]
User=${SUSER_CHALL5}
ExecStart=bash -c 'cd ${SPATH}/chall5 && python ./server.py'
Restart=always

[Install]
WantedBy=multi-user.target
EOF

cp chall5-server.service /etc/systemd/system
systemctl enable chall5-server.service

# setup challenge 6
echo "[+] Setting challenge 6"

cp ./chall6/flag.txt /home/$SUSER_CHALL6
cp ./chall6/getinfo.sh /home/$SUSER_CHALL6
chown $RUSER:$SUSER_CHALL6 /home/$SUSER_CHALL6/flag.txt
chmod 750 /home/$SUSER_CHALL6/getinfo.sh

sed -E "s/\[name\]/$SUSER_CHALL6/" ./chall6/sysinfo.c > /tmp/sysinfo.c
gcc /tmp/sysinfo.c -o /usr/bin/sysinfo
rm /tmp/sysinfo.c
chown $RUSER:$SUSER_CHALL5 /usr/bin/sysinfo
chmod 4750 /usr/bin/sysinfo
touch -r /usr/bin/bash /usr/bin/sysinfo

# setup challenge 7
echo "[+] Setting challenge 7"

if ! cat  /etc/sudoers | grep "$SUSER_CHALL6 ALL=(ALL) NOPASSWD" >& /dev/null;
then
    command="$SUSER_CHALL6 ALL=(ALL) NOPASSWD: $SPATH/chall7/rootnow"
    sed -i -E "s#root\sALL=\(ALL:ALL\)\sALL#root ALL=(ALL:ALL) ALL\n$command#" /etc/sudoers
fi

# Verify the sudoers file for syntax errors
if visudo -c; then
  echo "Sudoers file syntax is OK. Changes applied."
else
  echo "Sudoers file syntax error. Changes not applied."
  exit 1
fi

cp -r ./chall7 $SPATH
mv $SPATH/chall7/flag.txt /root/root.txt
gcc  $SPATH/chall7/rootnow.c -fno-stack-protector -o $SPATH/chall7/rootnow
chown -R $RUSER:$SUSER_CHALL6 $SPATH/chall7
chmod -R 750 $SPATH/chall7
chmod 700 $SPATH/chall7/rootnow.c



# cleanup
chmod +x /root/infinity/cleanup.sh
crontab <<EOF
*/5 * * * * /root/infinity/cleanup.sh
EOF

#enable all service
#systemctl daemon-reload
#systemctl restart chall1.service chall3.service chall5.service
#reboot