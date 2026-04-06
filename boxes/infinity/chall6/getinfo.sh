#!/bin/bash
printf '%18s' "Reported date: "
echo "$(date)"
printf '%18s' "Reported usser: "
echo "$(whoami)"
echo ""
echo '---------------SYSTEM---------------'
hostnamectl | grep -v Chassis:
echo ""
echo '----------------USER----------------'
cat /etc/passwd | grep sh$ | awk -F ":" '{print "Username: "$1" ("$3")""\nPosition: "$5"\n"}'