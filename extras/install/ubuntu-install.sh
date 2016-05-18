#!/bin/sh
apt-get update
apt-get install -y python python-dev build-essential git libssl-dev libffi-dev
apt-get remove python-pip
curl https://bootstrap.pypa.io/ez_setup.py -o - | python
easy_install -U pip
git clone https://www.github.com/EricssonResearch/calvin-base
cd calvin-base
pip install -r requirements.txt -r test-requirements.txt
pip install --upgrade pyasn1 setuptools six
pip install -e .