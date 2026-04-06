#!/usr/bin/env bash

set -euo pipefail

mkdir -p /opt/chall3/tinyfilemanager/data
rm -rf /opt/chall3/tinyfilemanager/data/*

if [[ ! -f /home/taylor/user.txt ]]; then
  cp /root/infinity/chall4/flag.txt /home/taylor/user.txt
  chown root:taylor /home/taylor/user.txt
fi

if [[ ! -f /opt/chall5/flag.txt ]]; then
  cp /root/infinity/chall5/flag.txt /opt/chall5/flag.txt
  chown root:brown /opt/chall5/flag.txt
  chmod 640 /opt/chall5/flag.txt
fi

if [[ ! -f /home/john/flag.txt ]]; then
  cp /root/infinity/chall6/flag.txt /home/john/flag.txt
  chown root:john /home/john/flag.txt
fi

if [[ ! -f /home/john/getinfo.sh ]]; then
  cp /root/infinity/chall6/getinfo.sh /home/john/getinfo.sh
  chown root:john /home/john/getinfo.sh
  chmod 750 /home/john/getinfo.sh
fi
