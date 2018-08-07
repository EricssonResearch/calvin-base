#!/bin/sh

usage() {
    echo "Usage: $(basename $0) <docker container>\n\
    -f : follow log\n\
    -b : add docker id banner\n\
    -1 : last line of log\n"
    exit 1
}

CMD=cat

while getopts "1fh" opt; do
	case $opt in
		h) 
            usage
            ;;
        f) 
            CMD="tail -f"
            shift
            ;; 
        b)
            BANNER=yes
            shift
            ;;
        1)
            CMD="tail -1"
            shift
            ;;
	esac
done

DOCKER_ID=$1

if test -z $DOCKER_ID; then
    echo "Error: no docker id given"
    exit 1
fi

if test "$BANNER" = "yes"; then
    echo ::::::::::::::::
    echo $DOCKER_ID 
    echo ::::::::::::::::
fi
docker exec $DOCKER_ID $CMD /calvin-base/calvin.log
