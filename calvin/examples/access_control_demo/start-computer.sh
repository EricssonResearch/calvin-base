#!/bin/sh

HOST=$1
ATTRIBUTE_FILE="RuntimeAttributes/computer.attr"

# GLOBAL_STORAGE_START=false \
csruntime --host $HOST --attr-file $ATTRIBUTE_FILE
