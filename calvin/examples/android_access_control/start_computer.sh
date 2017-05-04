#!/bin/bash

HOST=$1
CONFIG_FILE="config/calvin.conf_computer"
ATTR_FILE="attributes/computer.attr"
export CALVIN_GLOBAL_STORAGE_TYPE=\"local\"

csruntime --host $HOST --port 5000 --controlport 5001 --dht-network-filter access_control --attr-file $ATTR_FILE 
