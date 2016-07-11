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
    printf -- "\nNote: This script assumes a debian/ubuntu based system, such as Raspberry Pi\n"
    exit $1
}

while getopts "pb:sweu" opt
do
    case $opt in
      b) INSTALL_BRANCH="$OPTARG";;
      s) INSTALL_STARTUP=yes;;
      w) INSTALL_WEB=yes;;
      e) INSTALL_RPI_DEPS=yes;;
      u) INSTALL_NON_RPI_DEPS=yes;;
      p) REPLACE_PIP=yes;;
      ?) 
          usage 0
          ;;
	esac
done

shift $(($OPTIND - 1))

# Getting started with sudo...
sudo echo This will install Calvin and dependencies

# install essential pre-requisites

sudo apt-get update > /dev/null 2>&1

if test $? -ne 0; then
    echo "apt-get update failed"
    usage 1
fi

echo Installing python prerequisites
sudo apt-get install -y python python-dev build-essential git libssl-dev libffi-dev > /dev/null 2>&1

if test $? -ne 0; then
    echo "apt-get install failed"
    usage 1
fi

if test "$REPLACE_PIP" = "yes"; then
    echo Replacing pip with latest version
    # As of this writing, the python-pip and python-requests packages in Debian Jessie are
    # out of sync. Remove the default and install a newer version - this is less than ideal.
    sudo apt-get remove -y python-pip > /dev/null 2>&1
    curl --silent https://bootstrap.pypa.io/get-pip.py -o - | sudo -H python > /dev/null 2>&1
fi

if test "$INSTALL_RPI_DEPS" = "yes"; then
    echo Installing sense-hat and dependencies
    sudo apt-get install -y sense-hat > /dev/null 2>&1
    echo Installing RPi.GPIO and mfrc522
    sudo -H pip install RPi.GPIO > /dev/null 2>&1
    sudo -H pip install -e git+https://github.com/lthiery/SPI-Py#egg=SPI-Py-1.0 > /dev/null 2>&1
    sudo -H pip install -e git+https://github.com/olaan/MFRC522-Python#egg=mfrc522 > /dev/null 2>&1
fi

if test "$INSTALL_NON_RPI_DEPS" = "yes"; then
    echo Installing pygame
    sudo apt-get install -y python-pygame > /dev/null 2>&1
    echo Installing opencv
    sudo apt-get install -y python-opencv > /dev/null 2>&1
    echo Installing tweepy
    sudo -H pip install tweepy > /dev/null 2>&1
fi


# install calvin
echo Downloading and installing Calvin
# clone from github
git clone -b $INSTALL_BRANCH https://www.github.com/EricssonResearch/calvin-base

# install dependencies

echo Installing Calvin dependencies
cd calvin-base
sudo -H pip install -r requirements.txt -r test-requirements.txt > /dev/null 2>&1

# install calvin
sudo -H pip install -e . > /dev/null 2>&1

# Calvin should now be installed, proceed with other stuff

if [ "$INSTALL_STARTUP" = yes ]; then

echo Installing startup scripts
# install mdns
sudo apt-get install -y libnss-mdns > /dev/null 2>&1

# create calvin startup script

sudo sh -c "cat > /etc/init.d/calvin.sh" <<'EOF'
#!/bin/sh
# /etc/init.d/calvin

### BEGIN INIT INFO
# Provides: calvin
# Required-Start: $network $remote_fs $syslog
# Required-Stop: $network $remote_fs $syslog
# Default-Start: 2 3 4 5
# Default-Stop: 0 1 6
# Short-Description: Start a calvin runtime with default settings
# Description: start/stop calvin at boot/shutdown (from http://www.stuffaboutcode.com/)
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

# register script with startup
sudo chmod 755 /etc/init.d/calvin.sh
sudo update-rc.d calvin.sh defaults
fi # INSTALL_STARTUP

if test "$INSTALL_WEB" = "yes" ; then
# create csweb startup script
echo Installing csweb startup scripts
sudo sh -c "cat > /etc/init.d/csweb.sh" <<'EOF'
#!/bin/sh
# /etc/init.d/csweb

### BEGIN INIT INFO
# Provides: csweb
# Required-Start: $network $remote_fs $syslog
# Required-Stop: $network $remote_fs $syslog
# Default-Start: 2 3 4 5
# Default-Stop: 0 1 6
# Short-Description: Start web interface for calvin system
# Description: start/stop csweb at boot/shutdown (from http://www.stuffaboutcode.com/)
### END INIT INFO

case "$1" in
    start)
        echo "Starting csweb"
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

# register script with startup
sudo chmod 755 /etc/init.d/csweb.sh
sudo update-rc.d csweb.sh defaults
fi # INSTALL_WEB

echo "==="
echo "Installed calvin and necessary dependencies"
[ "$INSTALL_STARTUP" = "yes" ] && echo "Installed calvin to run at startup"
[ "$INSTALL_WEB" = "yes" ] && echo "Installed calvin web interface to run at startup"
[ "$INSTALL_RPI_DEPS" = "yes" ] && echo "Installed raspberry pi example dependencies"
[ "$INSTALL_NON_RPI_DEPS" = "yes" ] && echo "Installed example dependencies"
# done

echo "Done. Good luck."
