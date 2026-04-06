SPATH="/opt"
RUSER="root"

SUSER_CHALL4="taylor"
SUSER_CHALL5="brown"
SUSER_CHALL6="john"


CON_ID=$(docker ps | grep manager | cut -d ' ' -f 1)
docker exec $CON_ID sh -c "rm -r ./data/*"

if [[ ! -f "/home/$SUSER_CHALL4/user.txt" ]];
then
    cp ./chall4/flag.txt /home/$SUSER_CHALL4/user.txt
    chown $RUSER:$SUSER_CHALL4 /home/$SUSER_CHALL4/user.txt
fi

if [[ ! -f "/opt/chall5/flag.txt" ]];
then
    cp /root/infinity/chall5/flag.txt /opt/chall5/
    chown $SUSER_CHALL5:$SUSER_CHALL5 /opt/chall5/flag.txt
fi

if [[ ! -f "/home/$SUSER_CHALL6/flag.txt" || ! -f "/home/$SUSER_CHALL6/getinfo.sh" ]];
then
    cp /root/infinity/chall6/flag.txt /home/$SUSER_CHALL6
    chown $RUSER:$SUSER_CHALL6 /home/$SUSER_CHALL6/flag.txt

    cp /root/infinity/chall6/getinfo.sh /home/$SUSER_CHALL6
    chown $RUSER:$SUSER_CHALL6 /home/$SUSER_CHALL6/getinfo.sh
    chmod 754 /home/$SUSER_CHALL6/getinfo.sh
fi
