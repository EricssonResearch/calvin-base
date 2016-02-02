# Access Control Demo

This example is based on a demonstration we have frequently done with Calvin.
The idea is to show how one can easily, step-by-step, build an application with
increasing complexity, with limited effort.

## Setup

The example assumes the following devices:

 - A computer to server as 'server'
 - Two Raspberry Pi's 
 - One Philips-Hue Smart Light 
 - One IP Camera

Install the required components by running the install.sh script in the
Components-folder. (This assumes a compatible shell such as bash/zsh/ash.)

### Device specifics

The computer and the two Raspberry Pi's should have Calvin installed on them,
of course. The Raspberry Pi's should have one button each, connecting pins 1
and 16 (3.3v and GPIO 23 in BCM mode.) All devices should have PyGame installed
to handle images and audio in the demo.

The computer should also have OpenCV installed, with python-bindings. This may
or may not be easy to achieve.

The Hue is, by default, using ip "192.168.0.101", user "newdeveloper" and light
number "1". Change these to reflect your settings if necessary.

The IP Camera is by default an Axis Communications camera with ip
"192.168.0.137" with username "root" and password "pass". Consult your camera's
documentation if this does not match your setup.

## Running

Start calvin on the computer and on the Raspberry Pi's using the accompanying
scripts if you are on a computer with a compatible shell, such as
bash/zsh/ash. Instructions for other platforms forthcoming, but slowly. The
scripts should be given the IP address of the respective devices as arguments.

Start 'csweb' and log onto one of the devices - preferrably the "server"
device. If all is well, there should be three devices listed. If not, reload
the page a few times. If it still will not load, consult troubleshooting below.

Click "deploy" and select one of the scripts in the Script-folder. Got to the
"Applications" view and select your application from the drop-down meny inspect
it. Click "migrate" and select the corresponding deployment script (ending with
.deployjson) in the same folder as the script. Apply the script to migrate
actors to their respective devices.

## Troubleshooting

If the devices cannot find eachother, there may be network issues, and a simple
readme-file is not the place to try to slay such a diverse beast, but we can
offer one possible solution that may, or may not, help.

Edit the scripts, and remove the commented out sections to try the example
without the full feature set. This turns off Calvin's internal registry, which
is not strictly needed when running this small demonstration. Make sure to add
the ip address of the device serving as 'computer' in the demo to the indoor
and outdoor device startup script.
