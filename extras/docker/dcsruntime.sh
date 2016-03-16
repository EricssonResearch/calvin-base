#!/bin/sh

usage() {
	echo "Usage: $(basename $0) \n\
    -i <image>[:<tag>   : Docker image (and tag) to use
    -l                  : Limit docker CPU and memory\n\
    -p                  : Make the proxy node\n\
    -s                  : Run privileged
    -g                  : Enable Raspberry Pi gpio (implies -s)
    -m <storage-proxy>  : address of proxy\n\
    -e <external-ip>    : external IP to use\n\
    -n <name>           : Name of docker and attribute of csruntime\n\
     <args to csruntime>"
}

PROXY=""
ARGS=""
NAME=""
LIMIT=""
ENV=""

while getopts "sglpe:m:i:o:n:-:" opt; do
	case $opt in
        s)
            ENV="$ENV --privileged"
            ;;
        g)
            ENV="$ENV -e CALVIN_GLOBAL_GPIO_PLUGIN=\"platform/raspberry_pi/rpigpio_impl\""
            ENV="$ENV --device /dev/ttyAMA0:/dev/ttyAMA0 --device /dev/mem:/dev/mem --privileged"
            ;;
        i) 
            TAG=$OPTARG
            ;;
		l)
			LIMIT=yes
			;;
		p)
			# This is the proxy to use
			PROXY=yes
			;;
		e)
			EXTERNAL_IP=$OPTARG
			;;
		m) 
			CALVIN_MASTER=$OPTARG
			;;
		n) 
			NAME=$OPTARG
			;;

		-) 
			VAL=${!OPTIND}
			ARGS+=" --$OPTARG ${!OPTIND}"
			OPTIND=$(( $OPTIND + 1))
			;;
		\?)
			usage;
			exit 1
			;;
	esac
done

shift $((OPTIND-1))

if [ -z "$TAG" ]; then
    TAG="erctcalvin/calvin"
fi

echo "image: " $TAG
echo "master:" $CALVIN_MASTER
echo "external:" $EXTERNAL_IP
echo "name:" $NAME
echo "args: " $ARGS

if [ -z "$NAME" ]; then
	echo "Error: No name supplied";
	exit 1;
fi

if [ -z "$EXTERNAL_IP" ]; then
	echo "Error: Externally visible IP required";
	exit 1;
fi

if [ -z "$PROXY" -a -z "$CALVIN_MASTER" ]; then
	echo "Non-proxy runtimes require master of the form 'calvinip://<uri>:<port>'"
	exit 1
fi

# Ensure no docker with that name already running
if [ $(docker ps -a | grep -c "$NAME" ) -eq 1 ]; then
	echo "Container \"$NAME\" already exists";
	exit 1;
fi

# Should be an option, really
# docker pull erctcalvin/calvin-test:demo


if [ "$PROXY" ]; then
	ENV="$ENV -e CALVIN_GLOBAL_STORAGE_TYPE=\"local\" -p 5001:5001 -p 5000:5000"
fi

# When not control or proxy try to exit and not catch fatal errors
if [ -z "$PROXY" -a -z "$CONTROL" ]; then
	ENV="$ENV -e CALVIN_GLOBAL_EXIT_ON_EXCEPTION=true "
fi

if [ "$CALVIN_MASTER" ]; then
	ENV="$ENV -e CALVIN_GLOBAL_STORAGE_TYPE=\"proxy\" "
	ENV="$ENV -e CALVIN_GLOBAL_STORAGE_PROXY=\"$CALVIN_MASTER\""
fi

if [ "$LIMIT" ]; then 
	ENV="$ENV --cpu-quota=83000 --cpu-period=1000000 -m=512m"
fi

DOCKER_ID=$(docker run $ENV \
    --name $NAME \
    -d -t -P --entrypoint ./docker-runtime.sh $TAG --name $NAME "$ARGS")

echo "ENV:"  $ENV
PORT=$(docker port $DOCKER_ID 5000/tcp)
CONTROLPORT=$(docker port $DOCKER_ID 5001/tcp)

INTERNAL_IP=$(docker inspect --format '{{ .NetworkSettings.IPAddress }}' $DOCKER_ID)

echo $INTERNAL_IP > /tmp/$DOCKER_ID.ip
docker cp /tmp/$DOCKER_ID.ip $DOCKER_ID:/calvin-base/internal-ip

echo http://$EXTERNAL_IP:${CONTROLPORT#*:} > /tmp/$DOCKER_ID.control
docker cp /tmp/$DOCKER_ID.control $DOCKER_ID:/calvin-base/control-uri

echo calvinip://$EXTERNAL_IP:${PORT#*:} > /tmp/$DOCKER_ID.calvinip
docker cp /tmp/$DOCKER_ID.calvinip $DOCKER_ID:/calvin-base/calvin-ip

# Save the proxy control uri for future reference
test "$PROXY"x != ""x && cp /tmp/$DOCKER_ID.control /tmp/calvin-proxy.control
test "$PROXY"x != ""x && cp /tmp/$DOCKER_ID.calvinip /tmp/calvin-ip.control
