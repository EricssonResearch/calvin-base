#!/bin/sh

PORT=$1

if [ -z "$PORT" ]; then
	PORT=8000
fi

docker run -p $PORT:8000 -it --entrypoint csweb erctcalvin/calvin
