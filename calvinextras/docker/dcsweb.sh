#!/bin/sh

# Defaults
PORT="8000"
IMAGE="erctcalvin/calvin:master"
FLAGS="-it" # Run interactive w/ tty

usage() {
	echo "Usage: $(basename $0) \n\
    -i <image>[:<tag>]   : Docker image (and tag) to use [$IMAGE]\n\
    -p <port>            : Port to use [$PORT]\n\
    -d                   : Detach and run in background\n"
    exit 1
}


while getopts "i:p:hd" opt; do
	case $opt in
        p)
            PORT="$OPTARG"
            ;;
        i)
            IMAGE=$OPTARG
            ;;
        d)
            FLAGS=-d
            ;;
		h)
			usage;
			;;
	esac
done

docker run -p $PORT:8000 $FLAGS --entrypoint csweb $IMAGE

