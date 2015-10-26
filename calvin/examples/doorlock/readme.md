# A simple application for access control using Calvin

This is an example of an simple application controlling a door lock written using CalvinScript.

## Overview

The scenario is:

1. Person x pushes a button to trigger a doorbell
2. A camera takes a picture of person x, the picture is shown and if a face is found in the image the doorbell sounds
3. Person y pushes a button to unlock the door

The devices used to mimic this scenario is:

- Laptop, with hostname "laptop" and ip address 192.168.0.111 in this example, running a Calvin node.
- Raspberry PI, with hostname "raspi3" and ip address 192.168.0.146 in this example, running a Calvin node and with a push button connected to GPIO pin 16 (used to trigger the camera)
- Raspberry PI, with hostname "raspi2" and ip address 192.168.0.134 in this example, running a Calvin node with a push button connected to GPIO pin 16 (used to unlock the door) and a speaker connected to the 3.5mm jack (acting as the doorbell)
- One network camera used get an image of the person at the door
- One Philips Hue lamp representing the state of the doorlock (green light=unlocked, red light=locked)

`doorlock.calvin` contains the Calvin script and 'doorlock.deployjson' contains the deployment requirements.

## Running the example

In the doorlock example folder on the laptop, add a file named calvin.conf with the following content to blacklist gpio actors on the laptop:

    {
      "global": {
        "capabilities_blacklist" : ["calvinsys.io.gpiohandler"]
      }
    }

Start a Calvin runtime on the laptop and both the Raspberry Pis with their respective IP_ADDRESS and HOSTNAME:

    doorlock$ csruntime --host IP_ADDRESS --keep-alive --attr '{"indexed_public": {"node_name": {"organization": "com.ericsson", "name": "HOSTNAME"}}}'

Next, on the laptop deploy the application and apply the deployment requirements:

    doorlock$ cscontrol http://192.168.0.111:5001 deploy doorlock.calvin --reqs doorlock.deployjson

Next, on the laptop start a calvin web server:

    doorlock$ csweb

Next, verify the actor deployment by opening a web browser go to http://192.168.0.111:8000 (In the Connect dialog, enter "http://192.168.0.111:5001" in the Control URI field and "node/attribute/node_name/com.ericsson" as the Peers index search field).

Next, push the button on raspi3 and a picture should be shown and if a face was detected in the image the doorbell should trigger. Then, push button on raspi2 to unlock the door (lamp should turn green).