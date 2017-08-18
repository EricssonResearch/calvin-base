#!/bin/bash
cd ~
echo ----update----
sudo apt-get update
echo ----upgrade----
sudo apt-get upgrade -y
echo ----install vim----
sudo apt-get install -y vim
echo ----install python-dev----
sudo apt-get install -y python-dev
echo ----install libssl-dev----
sudo apt-get install -y libssl-dev
echo ----install libffi-dev----
sudo apt-get install -y libffi-dev
echo ----install ntpdate----
sudo apt-get install -y ntpdate
echo ----upgrade pip----
sudo apt-get remove -y python-pip
sudo easy_install pip
echo ----update six----
sudo pip install --upgrade six
