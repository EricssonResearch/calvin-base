#!/bin/sh

HOSTS="lund-infob lund-rfid lund-cam-sensehat"
HOSTS="$HOSTS sthlm-infob sthlm-rfid sthlm-cam-sensehat sthlm-switch"

for host in $HOSTS; do
    ssh pi@$host 'rm -rf /home/pi/runtime-config'
    scp -r runtime-config/ pi@$host:/home/pi
    scp calvin.service pi@$host:/home/pi/runtime-config/
    #ssh pi@$host 'sudo systemctl disable calvin'
    #ssh pi@$host 'sudo rm /etc/systemd/system/calvin.service'
    #ssh pi@$host 'sudo cp /home/pi/runtime-config/calvin.service /etc/systemd/system/'
    #ssh pi@$host 'sudo systemctl enable calvin'
    #ssh pi@$host 'sudo systemctl start calvin'
done

