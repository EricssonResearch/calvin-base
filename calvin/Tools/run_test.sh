#!/bin/bash

[ ! -z "$TESTSCRIPT_DEBUG" ] && set -x

SCRIPTNAME=$(basename $0)
pushd `dirname $0` > /dev/null
SCRIPTDIR=`pwd`
popd > /dev/null

if [ -f test_func.sh ]; then
	source test_func.sh
elif [ -f "$SCRIPTDIR/test_func.sh" ]; then
	source "$SCRIPTDIR/test_func.sh" ]
else
	echo "Cant find test_func.sh help me!!"
	exit -1
fi

SCRIPT="$0"
MASTER="local"
SSHKEY=~/.ssh/id_rsa

[ -z "$UUID" ] && UUID=$(which uuid)
[ -z "$UUID" ] && UUID=$(which uuidgen)


function display_usage() {
cat << EOF
usage: $0 [options] <ip:s>...

ENV variables:
TESTSCRIPT_DEBUG=1		Enables tracing of scripts.
UUID='echo "1234"'      	Set DHT filter and purpose

Options:
  -h,--help        		Show help options.
  -m,--master <ip-address> 	Will push there and exeute from there(proxy), for cloud solutions.
  -i,--keyfile <ssh keyfile> 	Set the ssh key to use for access the machines.
  -s,--stop <git commit> 	Only for internal master use
  --loglevel <argument> 	Arguments are pushed to the csruntimes.
  -t, --test	   		Needs atleast two ips to work properly.
  -k, --kill <id> 		The UUID used to start the nodes Kills remote running nodes
  --setup <keyfile> 		Sets the ssh key at the hosts
  -v				Print version info.

 Args:
  <ip:s>		Ip numbers to the host to start runtimes at.
EOF
}

while [[ $# > 0 ]]
do
key="$1"

case $key in
    -m|--master)
    MASTER="$2"
    shift # past argument
    ;;
    -i|--keyfile)
    SSHKEY=$2
    shift # past argument
    ;;
    -s|--stop)
    MASTER="local"
    GIT_COMMIT=$2
    shift # past argument
    shift # past argument
    break
    ;;
    --loglevel)
    LOG_LEVEL=$2
    shift
     ;;
    -t|--test)
    RUN_TEST="1"
    ;;
    -k|--kill)
    KILL="$2"
    shift
    ;;
    -h|--help)
    display_usage
    exit 0
    ;;
    --setup)
    SEND_KEYFILE="$2"
    shift
    ;;
    *)
    # unknown option
    break
    ;;
esac
shift # past argument or value
done

IPS=$*

if [ ! -z "$SEND_KEYFILE" ]; then

	RET=0
	for node in $IPS
	do
		if ! cat $SEND_KEYFILE | ssh $node -i $SSHKEY "mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys"; then
			echo "Problem sending key to $node"
			RET=$((RET+1))
		fi
	done
	exit $RET
fi

if [ ! -z "$KILL" ]; then
	RET=0
	for node in $IPS
	do
		if ! ssh -i $SSHKEY $node "pkill -f $KILL"; then
			echo "Problem killing runtime at $node"
			RET=$((RET+1))
		fi
		RET=$((RET+?))
	done
	if ! pkill -f $KILL; then
		echo "Problem killing local runtime"
		RET=$((RET+1))
	fi
	exit $RET
fi

if [ "$MASTER" != "local" ]; then
	# Push us to master and send everything
	MRTEMPDIR=$(remote_tempdir $MASTER $SSHKEY)
	pushgit $SSHKEY $MASTER $MRTEMPDIR
	#pushfile $SSHKEY
	# Execute us remote
	[ ! -z "$RUN_TEST" ] && RUN_TEST="-t"
	ssh -i $SSHKEY $MASTER "cd $MRTEMPDIR && bash $MRTEMPDIR/calvin/Tools/$SCRIPTNAME $RUN_TEST -s $(git_head) $IPS"
	exit $?
else
	# We are master run tests here
	if [ -z "$GIT_COMMIT" ]; then
		# Go to top if we are in git
		cd $(git rev-parse --show-toplevel)
	fi
	# We arume top already
fi

DEF_IF=$(netstat -nr | grep -E "^default|^0.0.0.0" | awk '{print $NF}' )
[ -z "$MYIP" ] && MYIP=$(ifconfig $DEF_IF | grep 'inet ' | sed 's/addr://' | awk '{ print $2}')

DEBUG_FLAGS="--loglevel=calvin.tests=DEBUG --loglevel=calvin.runtime.south.storage.twistedimpl.dht:DEBUG --loglevel=calvin.runtime.north.storage:DEBUG $LOG_LEVEL"

export CALVIN_TEST_UUID=$($UUID)
export CALVIN_GLOBAL_DHT_NETWORK_FILTER=\"$($UUID)\"
[ -z "$GIT_COMMIT" ] && GIT_COMMIT=$(git_head)

declare -a NODES
CNT=0
RET=0

echo -ne "Starting nodes "
for node in $IPS
do
	PORT=$(get_random_port)
	PORT_DHT=$(get_random_port)

	# Do this in parallell and wait later
	sh -c "$SCRIPTDIR/setup_node.sh $GIT_COMMIT $node $CALVIN_TEST_UUID $PORT $CALVIN_GLOBAL_DHT_NETWORK_FILTER $MYIP $SSHKEY $DEBUG_FLAGS 2>&1 | tee $node-log.txt > /dev/null" &
	PID=$!
	NODES[$CNT]="$node;$PORT;$PID"
	CNT=$((CNT+1))
	echo -ne "."
done
echo

echo -ne "Wating for nodes to start "
CNT=0
declare -a CALVIN_NODES
for node in ${NODES[@]}
do
	IFS=';' read -a INFO <<< "$node"

	kill -0 ${INFO[2]} 2> /dev/null
	if [ $? -ne 0 ]; then
		echo "Calvin node at ${INFO[0]} did not start correctly"
		RET=1
		break
	fi

	# Wait for it to start
	CALVIN_TEST_NODE=$(nc -l ${INFO[1]})
	if [ "$CALVIN_TEST_NODE" == "FALSE" ]; then
		echo "Calvin node at ${INFO[0]} did not start correctly"
		RET=1
		break
	fi
	CNT=$((CNT+1))
	CALVIN_NODES[$CNT]=$CALVIN_TEST_NODE
	echo -ne "."
done
echo

if [ $RET -ne 0 ]; then
	for node in ${NODES[@]}
	do
		IFS=';' read -a INFO <<< "$node"
		kill ${INFO[2]} 2> /dev/null
	done
	exit $RET

fi

sleep 1

if [ -z "$RUN_TEST" ]; then
	echo "Started nodes:"
	CNT=0
	for node in ${NODES[@]}
	do
		IFS=';' read -a INFO <<< "$node"
		echo "${CALVIN_NODES[2]} pid ${INFO[2]}"
		CNT=$((CNT+1))
	done
	echo "To kill all use:"
	echo $0 -k $CALVIN_GLOBAL_DHT_NETWORK_FILTER $IPS
else
	echo "Running tests"
	export CALVIN_TEST_IP=$MYIP

	virtualenv venv > /dev/null
	source venv/bin/activate > /dev/null
	pip install -q pytest-cov > >(tee local-node-installlog.txt)
	pip install -q -r requirements.txt > >(tee -a local-node-installlog.txt)
	pip install -q -r test-requirements.txt > >(tee -a local-node-installlog.txt)
	py.test -sv --cov=calvin $DEBUG_FLAGS --cov-report xml calvin --junitxml=results.xml 2> >(tee local-node-stderr.txt > /dev/null) > >(tee local-node-stdout.txt)
	deactivate
fi
