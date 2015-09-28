#!/bin/bash

set -x

pushd `dirname $0` > /dev/null
SCRIPTDIR=`pwd`
popd > /dev/null

if [ -f "test_func.sh" ]; then
	source "test_func.sh"
elif [ -f "$SCRIPTDIR/test_func.sh" ]; then
	source "$SCRIPTDIR/test_func.sh"
else
	echo "Cant find test_func.sh help me!!"
	exit -1
fi

virtualenv venv

GIT_COMMIT=$1
shift
MYIP=$1
shift
PURPOSE=$1
shift
ANSWER_PORT=$1
shift
DHT_NETWORK_FILTER=$1
shift
MASTER_IP=$1
shift
DEBUG_FLAGS=$*

PORT=$RANDOM
STOP=0

PORT=$(get_random_port)
CONTROL_PORT=$(get_random_port)

# Test run
source venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python calvin/Tools/csruntime.py --dht-network-filter=$DHT_NETWORK_FILTER --host $MYIP --controlport $CONTROL_PORT --port $PORT $DEBUG_FLAGS --keep-alive --attr "{\"indexed_public\": {\"node_name\": {\"organization\": \"com.ericsson\", \"purpose\": \"$PURPOSE\"}}}" &
CSRUNTIME_PID=$!

# Tell other side we are done
sleep 1

RET=1

# Master can do other stuff lets try in 120 sec
for a in $(seq $((60*4))); do
	kill -0 $CSRUNTIME_PID 2> /dev/null
	if [ $? -eq 0 ]; then
		# Started inform other side
		echo "$MYIP:$PORT" | /bin/netcat -w 1 $MASTER_IP $ANSWER_PORT
		if [ $? -eq 0 ]; then
			RET=0
			break
		fi
	else
		# Died inform other side
		echo "FALSE" | /bin/netcat -w 1 $MASTER_IP $ANSWER_PORT
		if [ $? -eq 0 ]; then
			# Lets die
			RET=1
			break
		fi
	fi
	sleep .5
done

# All ok lets wait fo rit to finnish with timeout
if [ $RET -eq 0 ]; then
	for a in $(seq $((60*5)))
	do
		kill -0 $CSRUNTIME_PID 2> /dev/null || break
		sleep 1
	done
fi


# Try killing it
kill -0 $CSRUNTIME_PID 2> /dev/null && kill $CSRUNTIME_PID
sleep 1
kill -0 $CSRUNTIME_PID 2> /dev/null && kill -9 $CSRUNTIME_PID
rm -fr $TEST_DIR
