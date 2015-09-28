#!/bin/bash

[ ! -z "$TESTSCRIPT_DEBUG" ] && set -x

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

# params
GIT_COMMIT=$1
shift
IP=$1
shift
CALVIN_TEST_UUID=$1
shift
TEST_PORT=$1
shift
CALVIN_GLOBAL_DHT_NETWORK_FILTER=$1
shift
MASTER_IP=$1
shift
SSH_ID=$1
shift
DEBUG_FLAGS=$* 

REMOTE_TEMP_DIR=$(remote_tempdir $IP $SSH_ID)

# Push to remote 
pushgit $SSH_ID $IP $REMOTE_TEMP_DIR || exit -1

# launch peer1
ssh -i $SSH_ID $IP "cd $REMOTE_TEMP_DIR && calvin/Tools/start_calvin2.sh $GIT_COMMIT ${IP#*@} $CALVIN_TEST_UUID $TEST_PORT $CALVIN_GLOBAL_DHT_NETWORK_FILTER $MASTER_IP $DEBUG_FLAGS"
