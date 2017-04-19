#!/bin/sh

#Defaults

PORT="8000"
IMAGE="erctcalvin/calvin:master"

usage() {
	echo "Usage: $(basename $0) \n\
    -i <image>[:<tag>]   : Docker image (and tag) to use [$IMAGE]\n\
    -p <port>            : Port to use [$PORT]\n"
     exit 1
}


while getopts "i:p:h" opt; do
	case $opt in
        p)
            PORT="$OPTARG"
            ;;
        i)
            IMAGE=$OPTARG
            ;;
		h)
			usage;
			;;
	esac
done

docker run -p $PORT:8000 --entrypoint csweb $IMAGE

