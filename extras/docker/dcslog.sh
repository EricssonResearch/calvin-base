#!/bin/sh

usage() {
    echo "Usage: $(basename $0) <docker container>\n\
    -f : follow log\n"
    exit 1
}

CMD=cat

while getopts "fh" opt; do
	case $opt in
		h) 
            usage
            ;;
        f) 
            CMD="tail -f"; 
            shift
            ;; 
	esac
done

DOCKER_ID=$1

if test -z $DOCKER_ID; then
    echo "Error: no docker id given"
    exit 1
fi

echo ::::::::::::::::
echo $DOCKER_ID 
echo ::::::::::::::::
docker exec $DOCKER_ID $CMD /calvin-base/calvin.log
