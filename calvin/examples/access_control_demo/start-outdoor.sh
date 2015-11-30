#!/bin/sh
HOST=$1
ATTRIBUTE_FILE="RuntimeAttributes/outdoor_device.attr"

# GLOBAL_STORAGE_PROXY=<computer device ip> \
csruntime --host $HOST --attr-file $ATTRIBUTE_FILE
