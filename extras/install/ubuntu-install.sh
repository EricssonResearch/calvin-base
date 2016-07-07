#!/bin/sh

INSTALL_STARTUP=no
INSTALL_WEB=no
INSTALL_RPI_DEPS=no
INSTALL_NON_RPI_DEPS=no
INSTALL_BRANCH=master
REPLACE_PIP=no

usage() {
    printf -- "Usage: %s [-b master/develop] -sweu\n" $0
    printf -- "\t-b\tselect branch of calvin to install [%s]\n" $INSTALL_BRANCH
    printf -- "\t-s\trun calvin at startup [%s]\n" $INSTALL_STARTUP
	printf -- "\t-w\trun web interface at startup [%s]\n" $INSTALL_WEB 
    printf -- "\t-e\tinstall raspberry pi example dependencies [%s]\n" $INSTALL_RPI_DEPS
    printf -- "\t-u\tinstall non-raspberry pi example dependencies [%s]\n" $INSTALL_NON_RPI_DEPS
    printf -- "\t-p\treplace python-pip (may solve some installation issues) [%s]\n" $REPLACE_PIP
    exit 0
}

while getopts "b:sweu" n
do
	case $n in
	  b) INSTALL_BRANCH="$OPTARG";;
	  s) INSTALL_STARTUP=yes;;
	  w) INSTALL_WEB=yes;;
      e) INSTALL_RPI_DEPS=yes;;
      u) INSTALL_NON_RPI_DEPS=yes;;
      p) REPLACE_PIP=yes;;
	  ?) 
          usage
          ;;
	esac
done

shift $(($OPTIND - 1))

# install essential pre-requisites

sudo apt-get update
sudo apt-get install -y python python-dev build-essential git libssl-dev libffi-dev

if test "$REPLACE_PIP"="yes"; then
    # As of this writing, the python-pip and python-requests packages in Debian Jessie are
    # out of sync. Remove the default and install a newer version - this is less than ideal.
    sudo apt-get remove -y python-pip
    curl https://bootstrap.pypa.io/get-pip.py -o - | sudo python
fi

if test "$INSTALL_RPI_DEPS"="yes"; then
    sudo apt-get install sense-hat
    pip install -r rpi-requirements.txt
fi

if test "$INSTALL_NON_RPI_DEPS"="yes"; then
    sudo apt-get install python-pygame
    sudo apt-get install python-opencv
    pip install -r ex-requirements.txt
fi


# install calvin

# clone from github
git clone -b $branch https://www.github.com/EricssonResearch/calvin-base

# install dependencies
cd calvin-base
sudo -H pip install -r requirements.txt -r test-requirements.txt

# install calvin
sudo pip install -e .

# Calvin should now be installed, proceed with other stuff

if [ x"$INSTALL_STARTUP" = xyes ]; then

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
fi # INSTALL_STARTUP

if test "$INSTALL_WEB"="yes" ]; then
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
fi # INSTALL_WEB

[ "$INSTALL_STARTUP"="yes" ] && echo "Installed calvin at startup"
[ "$INSTALL_WEB"="yes" ] && echo "Installed calvin web interface at startup"
# done
echo "Done. You're on your own."
