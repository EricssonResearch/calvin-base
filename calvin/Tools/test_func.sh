#!/bin/bash

function get_random_port {
	local TEST_PORT=$RANDOM

	while true; do
		netstat -na | grep $TEST_PORT >> /dev/null
		if [ $? -ne 0 ] && [ $TEST_PORT -gt 1024 ]; then
			break
		fi
  		TEST_PORT=$RANDOM
	done
	echo $TEST_PORT
}

function remote_tempdir {
	local REMOTE=$1
	local SSHKEY=$2
	local TEMP_BASE=$3
	[ -z "$TEMP_BASE" ] && TEMP_BASE="calvin_remote_test.XXXXXXXXXXXX"
	echo $(ssh -i $SSHKEY $REMOTE "mktemp -dt $TEMP_BASE")

}

function git_head {
	echo $(git rev-parse HEAD)
}

function clone_git {
	local SSH_ID=$1
	local GIT_ID=$2
	local GIT=$3
	
	HEAD=$(git rev-parse HEAD)
	if [ $? != 0 ]; then
		git clone $2
	fi
	#git reset --hard $1
}

function pushgit {
	git rev-parse --show-toplevel > /dev/null 2> /dev/null
	if [ $? -eq 0 ]; then
		pushgit_git $1 $2 $3
	else
		pushgit_files $1 $2 $3
	fi
}

function pushgit_git {
	local SSH_ID=$1
	local REMOTE=$2
	local REMOTE_DIR=$3
	local GITDIR=$(git rev-parse --show-toplevel)
	git archive --format=tar HEAD | ssh -i $SSH_ID $REMOTE "cd $REMOTE_DIR && tar xf -"
}

function pushgit_files {
	local SSH_ID=$1
	local REMOTE=$2
	local REMOTE_DIR=$3
	# Assume right dir
	(find . -type f -print0 | rsync -e "ssh -i $SSH_ID" -ar0 --files-from=- ./ $REMOTE:$REMOTE_DIR)
}

function pushfile {
	local LFILE=$1
	local REMOTEDIR=$2
	local SSHKEY=$3
	local FILENAME=$(basename $LFILE)
	
	cat $LFILE | ssh -i $SSHKEY "mkdir -p $(REMOTEDIR); cat >> $REMOTE_DIR/$FILENAME"

}
