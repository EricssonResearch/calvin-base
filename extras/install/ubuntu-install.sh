#!/bin/sh

while getopts "b:sw" n
do
	case $n in
	  b) branch="$OPTARG";;
	  s) runtime_start=yes;;
	  w) web_start=yes;;
	  ?) printf -- "Usage: %s [-b master/develop] -s -w\n" $0
         printf -- "-b\tselect branch of calvin to install\n"
         printf -- "-s\trun calvin at startup\n"
		 printf -- "-w\trun web interface at startup\n"
	     exit 0;;
	esac
done

if [ -z "$branch" ]; then
	branch="master"
fi
shift $(($OPTIND - 1))

# install pre-requisites
apt-get update
apt-get install -y python python-dev build-essential git libssl-dev libffi-dev
# there is an issue with python-pip, pip and python-requests and requests on some systems
# just in case this is one, we remove python-pip and install it using easy_install
apt-get remove python-pip
curl https://bootstrap.pypa.io/ez_setup.py -o - | python
easy_install -U pip
# get calvin
git clone -b $branch https://www.github.com/EricssonResearch/calvin-base
# and install it system-wide (but make it editable)
cd calvin-base
pip install -r requirements.txt -r test-requirements.txt
# some packages requires upgrades
pip install --upgrade pyasn1 setuptools six
pip install -e .

# Calvin should now be installed, proceed with other stuff

# install mdns
apt-get install -y libnss-mdns

if [ x"$runtime_start" = xyes ]; then
# create calvin startup script
(cat <<'EOF'
#! /bin/sh
# /etc/init.d/calvin

### BEGIN INIT INFO
# Provides: calvin
# Required-Start: $network $remote_fs $syslog
# Required-Stop: $network $remote_fs $syslog
# Default-Start: 2 3 4 5
# Default-Stop: 0 1 6
# Short-Description: Simple script to start a program at boot
# Description: A simple script from www.stuffaboutcode.com which will start / stop a program a boot / shutdown.
### END INIT INFO

# If you want a command to always run, put it here

# Carry out specific functions when asked to by the system
case "$1" in
start)
echo "Starting calvin"
# run application you want to start
/usr/local/bin/csruntime --host $(hostname -I) &
;;
stop)
echo "Stopping calvin"
# kill application you want to stop
killall csruntime
;;
*)
echo "Usage: /etc/init.d/calvin.sh {start|stop}"
exit 1
;;
esac

exit 0
EOF
) > /etc/init.d/calvin.sh

# register script with startup
chmod 755 /etc/init.d/calvin.sh
update-rc.d calvin.sh defaults

fi

if [ x"$web_start" = xyes ]; then
# create csweb startup script
(cat <<'EOF'
#! /bin/sh
# /etc/init.d/csweb

### BEGIN INIT INFO
# Provides: csweb
# Required-Start: $network $remote_fs $syslog
# Required-Stop: $network $remote_fs $syslog
# Default-Start: 2 3 4 5
# Default-Stop: 0 1 6
# Short-Description: Simple script to start a program at boot
# Description: A simple script from www.stuffaboutcode.com which will start / stop a program a boot / shutdown.
### END INIT INFO

# If you want a command to always run, put it here

# Carry out specific functions when asked to by the system
case "$1" in
start)
echo "Starting calvin"
# run application you want to start
/usr/local/bin/csweb -p 80 &
;;
stop)
echo "Stopping csweb"
# kill application you want to stop
killall csweb
;;
*)
echo "Usage: /etc/init.d/csweb.sh {start|stop}"
exit 1
;;
esac

exit 0
EOF
) > /etc/init.d/csweb.sh

# register script with startup
chmod 755 /etc/init.d/csweb.sh
update-rc.d csweb.sh defaults

fi

[ x$runtime_start = xyes ] && echo "Installed calvin at startup"
[ x$web_start = xyes ] && echo "Installed calvin web interface at startup"
# done
echo "Done. You're on your own."