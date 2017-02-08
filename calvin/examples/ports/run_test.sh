#!/bin/sh

TEST=$1

[ -z $TEST ] && TEST=alternate

CALVIN_GLOBAL_STORAGE_TYPE='"local"'\
    csruntime --host localhost --port 5000 --controlport 5001 --name runtime-0 &
echo $! > runtime.pids
CALVIN_GLOBAL_STORAGE_TYPE='"proxy"' CALVIN_GLOBAL_STORAGE_PROXY='"calvinip://localhost:5000"'\
    csruntime --host localhost --port 5002 --controlport 5003 --name runtime-1 &
echo $! >> runtime.pids

sleep 2

cscontrol http://localhost:5001 deploy $TEST.calvin --reqs $TEST.deployjson


sleep 5
for pid in $(cat runtime.pids); do
    kill $pid
done