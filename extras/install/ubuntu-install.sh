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
sudo apt-get update
sudo apt-get install -y python python-dev build-essential git libssl-dev libffi-dev

# As of this writing, the python-pip and python-requests packages in Debian Jessie are
# out of sync. Remove athe default and install a newer version - this is less than ideal.
sudo apt-get remove -y python-pip
curl https://bootstrap.pypa.io/get-pip.py -o - | sudo python

# Get calvin
git clone -b $branch https://www.github.com/EricssonResearch/calvin-base
# and install it and its dependencies
cd calvin-base
sudo -H pip install -r requirements.txt -r test-requirements.txt

# Install it editable
sudo pip install -e .

# Calvin should now be installed, proceed with other stuff

if [ x"$runtime_start" = xyes ]; then

# install mdns
sudo apt-get install -y libnss-mdns

# create calvin startup script
(sudo cat <<'EOF'
#! /bin/sh
# /etc/init.d/calvin

### BEGIN INIT INFO
# Provides: calvin
# Required-Start: $network $remote_fs $syslog
# Required-Stop: $network $remote_fs $syslog
# Default-Start: 2 3 4 5
# Default-Stop: 0 1 6
# Short-Description: Start a calvin runtime with default settings
# Description: A simple script from www.stuffaboutcode.com which will start / stop a program a boot / shutdown.
### END INIT INFO

case "$1" in
start)
echo "Starting calvin"
/usr/local/bin/csruntime --host $(hostname -I) &
;;
stop)
echo "Stopping calvin"
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
sudo chmod 755 /etc/init.d/calvin.sh
sudo update-rc.d calvin.sh defaults
fi # runtime start

if [ x"$web_start" = xyes ]; then
# create csweb startup script
(sudo cat <<'EOF'
#! /bin/sh
# /etc/init.d/csweb

### BEGIN INIT INFO
# Provides: csweb
# Required-Start: $network $remote_fs $syslog
# Required-Stop: $network $remote_fs $syslog
# Default-Start: 2 3 4 5
# Default-Stop: 0 1 6
# Short-Description: Start web interface for calvin system
# Description: A simple script from www.stuffaboutcode.com which will start / stop a program a boot / shutdown.
### END INIT INFO

case "$1" in
start)
echo "Starting calvin"
# run application you want to start
/usr/local/bin/csweb -p 80 &
;;
stop)
echo "Stopping csweb"
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
sudo chmod 755 /etc/init.d/csweb.sh
sudo update-rc.d csweb.sh defaults
fi # web start

[ x$runtime_start = xyes ] && echo "Installed calvin at startup"
[ x$web_start = xyes ] && echo "Installed calvin web interface at startup"
# done
echo "Done. You're on your own."
