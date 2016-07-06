#!/bin/sh
HOST=$1

if test -z $HOST; then
    echo no host ip supplied
    exit 1
fi

./test_system.sh -i erctcalvin/calvin:local -c -e $HOST -t proxy
./test_system.sh -n -e $HOST -t -c proxy
./test_system.sh -i erctcalvin/calvin:local -c -e $HOST -t dht
./test_system.sh -n -e $HOST -t -c dht
