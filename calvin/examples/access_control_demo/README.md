# Access Control Demo

This example is based on a demonstration we have frequently done with Calvin.
The idea is to show how one can easily, step-by-step, build an application with
increasing complexity, with limited effort.

## Setup

### Hardware
The example assumes the following devices:

- A computer to serve as 'server'
- Two Raspberry Pi's 
- One Philips-Hue Smart Light 
- One Web Camera

The Philips Hue is used in the `part_2.calvin script` as well as in the CalvinGUI
manual. However, should no Philips Hue be available, there´s a substitute script
`part_2_no_hue.calvin` available to use instead. In this script the lock status
will be printed to the terminal instead of controlling the lamp.

### Installation

- Install the required components by running the `install_components.sh` script:

        § ./install_components.sh

- Rename the relevant config file on each device to calvin.conf, i.e. on the
rasparry pis, rename the file `calvin.conf_raspberry` and on the computer, rename
the file `calvin.conf_server`.

- Edit the indoor and outdoor start-scripts by adding the ip address of the device
serving as `server`.

- The computer and the two Raspberry Pi's should have Calvin installed on them,
of course. The Raspberry Pi's should have one button each, connecting pins 1
and 16 (3.3v and GPIO 23 in BCM mode.) All devices should have PyGame installed
to handle images and audio in the demo.

- The computer should also have OpenCV installed, with python-bindings. This may
or may not be easy to achieve.

- The Hue is, by default, using ip "192.168.0.101", user "newdeveloper" and light
number "1". Change these settings in the script `part_2.calvin` to reflect your
settings.

- For camera, the first available webcam found will be used.



## Running

- Start calvin on the computer and on the Raspberry Pi's using the accompanying
scripts.
- The scripts should be given the IP address of the respective devices as arguments.
- In addition, make sure to run the start script from the directory where the
`calvin.conf` file is placed.

- Start `csweb` and log onto one of the devices - preferably the `server`
device. If all is well, there should be three devices listed. If not, reload
the page a few times.

- Click `deploy` and select one of the scripts in the Script-folder.
- Go to the `Applications` view and select your application from the drop-down menu
to inspect it.
