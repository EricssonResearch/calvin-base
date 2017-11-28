# Rotary encoder

Example on how to use a Keyes KY-040 Rotary Encoder with Calvin on a Raspberry Pi.


## Setup

### Hardware

- A Keyes KY-040 Rotary Encoder
- A Raspberry Pi 


### Installation

Edit the attributes in `calvin.conf` to reflect your pin assignment (if it differs
from the one specified in the file). The default pin-settings used in this
example are (in BCM-mode)

    clk: 22
    dt : 27
    sw : 17

- Needs +3.3v (pin 1, for example).
- For ground, any ground pin works of course. I like pin 6 myself.


### Calvin configuration

The following capabilities needs to be loaded to run this script:
- `io.button`
- `io.knob`

A `calvin.conf` file is prepared for this purpose. For the `calvin.conf` to be
loaded, start the calvin script from within the directory the `calvin.conf`
file is placed. For other ways of loading the configuration, please see
the Calvin Wiki page about [Configuration](https://github.com/EricssonResearch/calvin-base/wiki/Configuration)


## Running

Run the following command from within the directory the `calvin.conf`
file is placed:

    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost --keep-alive rotary.calvin

## DHT

Calvin's internal registry is not strictly needed when running this small example,
it has therefor been turned off. To turn it on and run the application with DHT
instead, remove `CALVIN_GLOBAL_STORAGE_TYPE=\"local\"` from the command. I.e:

    $ csruntime --host localhost --keep-alive rotary.calvin
