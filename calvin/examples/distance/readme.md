# Distance sensor

In this example a SR04 Ultrasonic distance sensor is used with Calvin on a
Raspberry Pi.


## Setup

### Hardware

- A SR04 Ultrasonic distance sensor
- A Raspberry Pi 


### Installation

Edit the file `gpio-pins.json` to reflect your pin assignment (if it differs
from the one specified in the file). The default pin-settings used in this
example are (in BCM-mode)

    Trig: 23
    Echo: 24

- Vcc needs +5v (pin 2).
- For ground, any ground pin works of course. I like pin 6 myself.


### Calvin configuration

The following plugins needs to be loaded to run this script:
- `distance_plugin`
- `gpio_plugin`

A `calvin.conf` file is prepared for this purpose. For the `calvin.conf` to be
loaded, start the calvin script from within the directory the `calvin.conf`
file is placed. For other ways of loading the configuration, please see
the Calvin Wiki page about [Configuration](https://github.com/EricssonResearch/calvin-base/wiki/Configuration)


## Running

Run one of the following commands from within the directory the `calvin.conf` file is placed:

### With DHT

    $ csruntime --host localhost --keep-alive distance.calvin --attr-file gpio-pins.json

### Without DHT

Calvin's internal registry is not strictly needed when running this small
example. To turn it off and run the application locally add `CALVIN_GLOBAL_STORAGE_TYPE=\"local\"`
to the command:

    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost --keep-alive distance.calvin --attr-file gpio-pins.json

