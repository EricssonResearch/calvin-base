#!/bin/bash

HOST=$1
STORAGE=$2
export CALVIN_GLOBAL_STORAGE_TYPE=\"proxy\"
export CALVIN_GLOBAL_STORAGE_PROXY=\"$STORAGE\"

ATTR_FILE="attributes/raspberry.attr"

csruntime --host $HOST --port 5000 --controlport 5001 --dht-network-filter access_control --attr-file $ATTR_FILE 

