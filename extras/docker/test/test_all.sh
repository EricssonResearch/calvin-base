#!/bin/sh
HOST=$1

if test -z $HOST; then
    echo no host ip supplied
    exit 1
fi

cd ..
./setup_system.sh -i erctcalvin/calvin:local -c -e $HOST -t proxy
./setup_system.sh cleanup
./setup_system.sh -n -e $HOST -t -c proxy
./setup_system.sh cleanup
./setup_system.sh -i erctcalvin/calvin:local -c -e $HOST -t dht
./setup_system.sh cleanup
./setup_system.sh -n -e $HOST -t -c dht
./setup_system.sh cleanup
