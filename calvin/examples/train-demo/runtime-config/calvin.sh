#!/bin/sh

. /home/pi/.virtualenvs/train-demo/bin/activate
cd /home/pi/runtime-config/

rt_name=$( hostname | cut -d"." -f1 )
cd $rt_name
csruntime --host $rt_name --attr-file attributes.json