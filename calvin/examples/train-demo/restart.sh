#!/bin/sh

HOSTS="lund-infob lund-rfid lund-cam-sensehat"
HOSTS="$HOSTS sthlm-infob sthlm-rfid sthlm-cam-sensehat sthlm-switch"

for host in $HOSTS; do
    echo "restarting $host"
    ssh pi@$host 'sudo systemctl restart calvin'
done

