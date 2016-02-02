# Control a wireless 433MHz power outlet

This example uses a pushbutton to control a self learning wireless 433MHz power outlet.

## Hardware

- A Raspberry Pi
- A pushbutton connected to GPIO pin 22 (BCM) and the 3.3V pin on the Raspberry Pi
- A 433MHz transmitter (TX433N is used in this example) with the data pin connected to GPIO pin 17 (BCM), GND pin connected to ground on the Raspberry Pi and the VCC pin connected to 5V on the Raspberry Pi.
- A remote power outlet (this example uses http://www.jula.se/catalog/el-och-belysning/elinstallation/plug-in-produkter/fjarrstrombrytare/fjarrstrombrytare-408050/)

## Protocol
The actor RCSwitch sends a startbit followed by 32 data bits and is ended with a stopbit. The startbit, stopbit, onebit and zerobit are tuples of bits with their timing (in us) defined in rcswitch.calvin:

    define startbit = [{"state":1, "time":250}, {"state":0, "time":2500}]
	define stopbit = [{"state":1, "time":250}, {"state":0, "time":10000}]
	define onebit=[{"state":1, "time":250}, {"state":0, "time":1250}]
	define zerobit=[{"state":1, "time":250}, {"state":0, "time":250}]

Example, the startbit outputs 1 for 250us followed by 0 for 2500us.

## Calvin configuration

calvin.conf to include the RCSwitch actor and to use the RPi.GPIO plugin:

    {
      "global": {
        "gpio_plugin": "platform/raspberry_pi/rpigpio_impl",
        "actor_paths": ["./devactors"]
      }
    }

## Running

Start a Calvin runtime on the Raspberry Pi and deploy `rcswitch.calvin`, use the pushbutton to control the remote power socket.
