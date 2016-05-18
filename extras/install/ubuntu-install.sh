#!/bin/sh

while getopts "b:" n
do
	case $n in
	  b) branch="$OPTARG";;
	  ?) printf "Usage: %s [-b master/develop]\n" $0
	     exit 0;;
	esac
done

if [ -z "$branch" ]; then
	branch="master"
fi
shift $(($OPTIND - 1))

apt-get update
apt-get install -y python python-dev build-essential git libssl-dev libffi-dev
apt-get remove python-pip
curl https://bootstrap.pypa.io/ez_setup.py -o - | python
easy_install -U pip
git clone -b $branch https://www.github.com/EricssonResearch/calvin-base
cd calvin-base
pip install -r requirements.txt -r test-requirements.txt
pip install --upgrade pyasn1 setuptools six
pip install -e .
