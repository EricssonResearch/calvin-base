#!/bin/sh

# This file is a wrapper around the csruntime command. It is intended
# to be used inside a container (docker, mostly) and waits for three 
# files to be created in the working directory:
#  - calvin-ip   : The external ip of the runtime
#  - control-uri : The external control uri of the runtime
#  - internal-ip : The ip of the container

# Wait for outside to give us an external uri
while [ ! -f ./calvin-ip ] ; do
    echo "Waiting...";
    sleep 1;
done

while [ ! -f ./control-uri ] ; do
    echo "Waiting...";
    sleep 1;
done

while [ ! -f ./internal-ip ] ; do
    echo "Waiting...";
    sleep 1;
done


# The control URI - copied first, should be there
CONTROL_URI=$(cat ./control-uri)

# The calvinip URI
EXTERNAL_URI=$(cat ./calvin-ip)

# The internal IP
CONTAINER_IP=$(cat ./internal-ip)

echo "External uri: " $EXTERNAL_URI
echo "Control uri: " $CONTROL_URI
echo "Internal ip: " $CONTAINER_IP

echo "START RUNTIME"
csruntime --host $CONTAINER_IP --external $EXTERNAL_URI --external-control $CONTROL_URI $@
echo "END RUNTIME"
