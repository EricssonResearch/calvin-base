# A simple application for access control using Calvin

This is an example of an simple application controlling a door lock written using CalvinScript.

## Overview

The scenario is:

1. Person x pushes a button to trigger a doorbell
2. A camera takes a picture of person x, the picture is shown and if a face is found in the image the doorbell sounds
3. Person y pushes a button to unlock the door

The devices used to mimic this scenario is:

- Laptop (192.168.0.111 in this example) running a Calvin node.
- Raspberry PI (192.168.0.146 in this example) running a Calvin node and with a push button connected to GPIO pin 16 (used to trigger the camera)
- Raspberry PI (192.168.0.134 in this example) running a Calvin node with a push button connected to GPIO pin 16 (used to unlock the door) and a speaker connected to the 3.5mm jack (acting as the doorbell)
- One network camera used get an image of the person at the door
- One Philips Hue lamp representing the state of the doorlock (green light=unlocked, red light=locked)

`doorlock.calvin` contains the Calvin script.

## Running the example

In the doorlock example folder on 192.168.0.111, add a file named calvin.conf with the following content to blacklist gpio actors on the laptop:

    {
      "global": {
        "capabilities_blacklist" : ["calvinsys.io.gpiohandler"]
      }
    }

Start a Calvin runtime on both Raspberry Pis with their respective IP addresses:

    doorlock$ csruntime --host IP_ADDRESS --keep-alive

Next, on 192.168.0.111 deploy the application and connect the runtimes:

    doorlock$ csruntime doorlock.calvin --host 192.168.0.111 --keep-alive &
    doorlock$ cscontrol http://192.168.0.111:5001 nodes add calvinip://192.168.0.146:5000
    doorlock$ cscontrol http://192.168.0.111:5001 nodes add calvinip://192.168.0.134:5000

Next, start the web server and migrate actor `button_1` to Raspberry PI with ip 192.168.0.146 and `button_2` and `bell` to Raspberry PI with ip 192.168.0.136:

    doorlock$ csweb

Next, push the button on Raspberry PI with ip 192.168.0.146 and a picture should be shown and if a face was detected in the image the doorbell should trigger. Then, push button on Raspberry PI with ip 192.168.0.134 to unlock the door (lamp should turn green).