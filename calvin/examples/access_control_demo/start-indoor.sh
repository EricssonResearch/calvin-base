#!/bin/sh
SERVER_IP="<server ip>"

HOST=$1
ATTRIBUTE_FILE="RuntimeAttributes/indoor_device.attr"

CALVIN_GLOBAL_STORAGE_TYPE=\"proxy\" \
CALVIN_GLOBAL_STORAGE_PROXY=\"calvinip://$SERVER_IP:5000\" \
csruntime --host $HOST --attr-file $ATTRIBUTE_FILE
