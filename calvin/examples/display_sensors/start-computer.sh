#!/bin/sh

HOST=$1

CALVIN_GLOBAL_STORAGE_TYPE=\"local\" \
csruntime --host $HOST --name "server"
