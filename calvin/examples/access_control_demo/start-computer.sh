#!/bin/sh

HOST=$1
ATTRIBUTE_FILE="RuntimeAttributes/computer.attr"

CALVIN_GLOBAL_STORAGE_TYPE=\"local\" \
csruntime --host $HOST --attr-file $ATTRIBUTE_FILE
