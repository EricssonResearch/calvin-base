#!/bin/sh
SERVER_IP="<server ip>"

HOST=$1

CALVIN_GLOBAL_STORAGE_TYPE=\"proxy\" \
CALVIN_GLOBAL_STORAGE_PROXY=\"calvinip://$SERVER_IP:5000\" \
csruntime --host $HOST --name "lcd"
