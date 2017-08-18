# Image

Remove paritions using disks program,

Write to SD-card;

SD-card: `$sudo dd if=~/Downloads/hypriot-rpi-20151115-132854.img of=/dev/sdc bs=4M;`

microSD-card: `$sudo dd if=~/Downloads/hypriot-rpi-20151115-132854.img of=/dev/sde bs=4M;`

Insert card into RPi, login with pi:raspberry (pirate:hypriot for hypriotOS 1.0).

# change hostname

`sudo vim /etc/hosts` change name at 127.0.1.1, `sudo nano /etc/hostname` same as in hosts file

# set date

`sudo date -s "9 SEP 2016 11:02:00"`

alternatively, setup Ericsson ntp
sudo apt-get install ntpdate

`sudo /etc/init.d/ntp stop`
`sudo ntpdate -s ntp1.ericsson.se`

add 
`server ntp1.ericsson.se` and `server ntp2.ericsson.se` to `/etc/ntp.conf`

`sudo /etc/init.d/ntp start`

# install calvin runtime

run the install.sh script

# RFID runtime setup

See <http://helloraspberrypi.blogspot.se/2015/10/raspberry-pi-2-mfrc522-python-to-read.html> for information on how to connect pins.

`$ sudo raspi-config`, advanced options -> enable SPI

SPI: `sudo pip install -e git+<https://github.com/lthiery/SPI-Py#egg=SPI-Py-1.0>`

MFRC522: `sudo pip install -e git+<https://github.com/olaan/MFRC522-Python#egg=mfrc522>`

# adafruit 16*2 LCD runtime setup (without plate)

`sudo pip install adafruit-CharLCD`

# PiCam runtime

`sudo pip install pycam`

#OpenCV on runtime to show video stream (python-sense-hat does not exist for ELX)

`sudo apt-get install -y --no-install-recommends gcc g++ python2.7 python-dev libffi-dev libssl-dev python-smbus wget ca-certificates git python-sense-hat python-pygame python-opencv`

# Calvin configuration files

In the calvinconfigtemplate, configurations for the different runtimes are listed, remove everything unrelated to that specific runtime and rename to calvin.conf

# Regenerate certificates

Run script: `setup_demo/generate_certificate.sh`

#Update users database

`curl -X PUT -H "Content-Type: application/json" -d '{"users_db": [{"username": "passenger", "attributes": {"age": "11", "last_name": "Pettersson", "first_name": "Peter", "address": "Petersgatan 1", "groups":["passenger"]}, "password": "pass1"}, {"username": "conductor1", "attributes": {"age": "22", "last_name": "Ceciliasdotter", "first_name": "Cecilia", "groups": ["employee", "conductor","Lund"], "address": "Elinsgatan 2"}, "password": "pass2"}, {"username": "conductor2", "attributes": {"age": "33", "last_name": "Carl", "first_name": "Carlsson","groups": ["employee", "conductor","Stockholm"]}, "password": "pass4"}, {"username": "train driver", "attributes": {"age": "44", "last_name": "Tinasdotter", "first_name": "Tina", "groups":["employee","train driver"]}, "password": "pass4"}]}' http://192.168.1.131:5001/authentication/users_db`

# Start demo
Turn of ELX firewall

`sudo service firewalld stop`

Start csweb on ELX machine on port 8000

`csweb`

Access in browswer `http://192.168.1.131:8000`

-ELX (runs proxy storage):
`csruntime -n 192.168.1.138 -p 5000 -c 5001 --attr-file runtime_attributes/ELX.json`

-Lund_InfoBoard:
`sudo -H CALVIN_CONFIG_PATH=$(pwd) csruntime -n 192.168.1.146 -p 5000 -c 5001 --attr-file runtime_attributes/Lund_InfoBoard.json`

-Lund_Camera_Sensehat:
`sudo -H CALVIN_CONFIG_PATH=$(pwd) csruntime -n 192.168.1.144 -p 5000 -c 5001 --attr-file runtime_attributes/Lund_Camera_Sensehat.json`

-Lund_RFID:
`sudo -H CALVIN_CONFIG_PATH=$(pwd) csruntime -n 192.168.1.112 -p 5000 -c 5001 --attr-file runtime_attributes/Lund_RFID.json`

-Sthlm_InfoBoard:
`sudo -H CALVIN_CONFIG_PATH=$(pwd) csruntime -n 192.168.1.114 -p 5000 -c 5001 --attr-file runtime_attributes/Sthlm_InfoBoard.json`

-Sthlm_Camera_Sensehat:
`sudo -H CALVIN_CONFIG_PATH=$(pwd) csruntime -n 192.168.1.130 -p 5000 -c 5001 --attr-file runtime_attributes/Sthlm_Camera_Sensehat.json`

-Sthlm_RFID:
`sudo -H CALVIN_CONFIG_PATH=$(pwd) csruntime -n 192.168.1.140 -p 5000 -c 5001 --attr-file runtime_attributes/Sthlm_RFID.json`

-Servo:
`sudo -H CALVIN_CONFIG_PATH=$(pwd) csruntime -n 192.168.1.128 -p 5000 -c 5001 --attr-file runtime_attributes/Servo.json`

#Debugging errors

`csruntime -n 192.168.1.138 -p 5000 -c 5001 --attr-file runtime_attributes/ELX.json --loglevel DEBUG --loglevel calvin.runtime.north.scheduler:ERROR  --loglevel calvin.calvin.runtime.north.storage:ERROR --loglevel calvin.calvin.runtime.south.plugins.transports.calvinip.twisted.twisted_transport --logfile log.txt`

#deploy script:
 
`cscontrol http://192.168.1.138:5001 deploy --credentials '{"SJ":{"username":"user1","password":"pass1"}}' --reqs test1.deployjson test1.calvin `


#Policy Administration Point

`git clone ssh://kloker.ld.sw.ericsson.se/repos/CalvinGUI.git`

Checkout branch develop

Start web server in CalvinGUI folder:

`python -m SimpleHTTPServer 8080`
