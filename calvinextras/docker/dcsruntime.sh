#!/bin/sh


# Defaults
IMAGE=erctcalvin/calvin:master
REGISTRY_TYPE=\"dht\"
REGISTRY_PROXY=""
NAME_OPT=""
CONTROLPORT_OPT="5001"
PORT_OPT="5000"

usage() {
	echo "Usage: $(basename $0) \n\
    -i <image>[:<tag>]   : Calvin image (and tag) to use [$IMAGE]\n\
    -e <external-ip>     : External IP to use\n\
    -n <name>            : Name of container & runtime\n\
    -c <port>            : Port to use for control uri\n\
    -p <port>            : Port to use for runtime to runtime communication\n\
    -l                   : Use local registry (non-distributed)
    -r <ip>:<port>       : Use runtime calvinip://<ip>:<port> as registry
    -v                   : Verbose output
    -d                   : dry run, do not start Calvin
     <args to csruntime>\n"
     exit 1
}

while getopts "dlr:c:p:he:i:n:-:v" opt; do
	case $opt in
        d)
            DRYRUN=yes
            ;;
        l)
            REGISTRY_TYPE=\"local\"
            ;;
        r)
            REGISTRY_TYPE=\"proxy\"
            REGISTRY_PROXY=\"calvinip://$OPTARG\"
            ;;
        p)
            PORT_OPT="$OPTARG:5000"
            ;;
        c)
            CONTROLPORT_OPT="$OPTARG:5001"
            ;;
        i)
            IMAGE=$OPTARG
            ;;
	e)
		EXTERNAL_IP=$OPTARG
		;;
	n) 
		NAME=$OPTARG
		;;
        v)
            VERBOSE=yes
            ;;
	h)
	    usage;
	    ;;
	-)
		ARGS=$ARGS" --$OPTARG"
		;;
	esac
done

CALVIN_ENV=" -e CALVIN_GLOBAL_STORAGE_TYPE=$REGISTRY_TYPE"

if test -n "$REGISTRY_PROXY"; then
    CALVIN_ENV=$CALVIN_ENV" -e CALVIN_GLOBAL_STORAGE_PROXY=$REGISTRY_PROXY"
fi

if test -n "$NAME"; then
	NAME_OPT="--name $NAME"
fi

DOCKER_ID=$(docker run $CALVIN_ENV $NAME_OPT -d -it -p $PORT_OPT -p $CONTROLPORT_OPT --entrypoint /bin/sh $IMAGE) || exit 1

PORT=$(docker port $DOCKER_ID 5000/tcp)
CONTROLPORT=$(docker port $DOCKER_ID 5001/tcp)
INTERNAL_IP=$(docker inspect --format '{{ .NetworkSettings.IPAddress}}' $DOCKER_ID)

if test -z "$EXTERNAL_IP"; then
	# If not external ip given, warn, use internal
    printf "Warning: Using internal ip $INTERNAL_IP\n"
	EXTERNAL_IP=$INTERNAL_IP
fi

EXTERNAL_CONTROL=http://$EXTERNAL_IP:${CONTROLPORT#*:} # Strip address 0.0.0.0: from control port
EXTERNAL_CALVINIP=calvinip://$EXTERNAL_IP:${PORT#*:} # Strip address 0.0.0.0: from port

# If no name option given, use docker name for runtime
if test -z "$NAME"; then
	# Strip prefix '/' from name
	NAME=$(docker inspect  --format '{{ .Name }}' $DOCKER_ID)
	NAME=${NAME#*/}
fi

if test x"$VERBOSE" = x"yes"; then
    echo "Name: $NAME, image: $IMAGE"
    echo "External ip: $EXTERNAL_IP"
    echo "Internal ip: $INTERNAL_IP"
    echo "External control uri: $EXTERNAL_CONTROL"
    echo "External control ip : $EXTERNAL_CALVINIP"
    echo "Registry type: $REGISTRY_TYPE"
    if test -n "$REGISTRY_PROXY"; then
        echo "Registry proxy: $REGISTRY_PROXY"
    fi
fi

if test x"$DRYRUN" != x"yes"; then
    CMD="csruntime --host $INTERNAL_IP --external $EXTERNAL_CALVINIP --external-control $EXTERNAL_CONTROL \
        --name $NAME --logfile /calvin-base/calvin.log $ARGS"
    docker exec -d $DOCKER_ID sh -c "$CMD"
else
    docker kill $DOCKER_ID
    docker rm $DOCKER_ID
fi
