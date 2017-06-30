# Control a wireless 433MHz power outlet

This example uses a pushbutton to control a self learning wireless 433MHz power
outlet.

## Setup

### Hardware

- A Raspberry Pi
- A pushbutton connected to GPIO pin 22 (BCM) and the 3.3V pin on the Raspberry
  Pi
- A 433MHz transmitter (RF-link 433 MHz sender module is used in this example)
with the data pin connected to GPIO pin 17 (BCM), GND pin connected to ground
on the Raspberry Pi and the VCC pin connected to 5V on the Raspberry Pi.
- A remote power outlet (this example uses [fjarrstrombrytare-408050](http://www.jula.se/catalog/el-och-belysning/elinstallation/plug-in-produkter/fjarrstrombrytare/fjarrstrombrytare-408050/))

__Note! Unfortunately the remote power outlet used in this example seems to be
hard to come over. The example will be updated with another power outlet in the
near future.__

### Protocol
The actor RCSwitch sends a startbit followed by 32 data bits and is ended with a
stopbit. The startbit, stopbit, onebit and zerobit are tuples of bits with their
timing (in us) defined in `rcswitch.calvin`:

    define startbit = [{"state":1, "time":250}, {"state":0, "time":2500}]
	define stopbit = [{"state":1, "time":250}, {"state":0, "time":10000}]
	define onebit=[{"state":1, "time":250}, {"state":0, "time":1250}]
	define zerobit=[{"state":1, "time":250}, {"state":0, "time":250}]

Example, the startbit outputs 1 for 250us followed by 0 for 2500us.

### Calvin configuration

A `gpio_plugin` needs to be loaded to run this script. A `calvin.conf`
file is prepared for this purpose.

For the `calvin.conf` to be loaded, start the calvin script from within
the directory the `calvin.conf` file is placed.


## Running

Start a Calvin runtime on the Raspberry Pi and deploy `rcswitch.calvin` with the
follwing command from within the directory the `calvin.conf` file is placed:

    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost --keep-alive rcswitch.calvin

- When the script is up and running, use the pushbutton to control the remote power
socket. The devices must be paired the first time the script is run, this is done
by pressing the connect button on the power outlet and then pressing the button
connected to the Raspberry Pi so that data is sent to the power outlet.


## DHT

Calvin's internal registry is not strictly needed when running this small example,
it has therefor been turned off. To turn it on and run the application with DHT
instead, remove `CALVIN_GLOBAL_STORAGE_TYPE=\"local\"` from the command. I.e:

    $ csruntime --host localhost --keep-alive rcswitch.calvin
