# Temperature

This example reads temperature from a thermometer. The thermometer could be
either a 1-wire sensor or a 


## Setup

### Hardware

The example assumes the following devices:

- A Raspberry Pi with:
  - A Sense HAT (https://www.raspberrypi.org/products/sense-hat/) __or__
  - A 1-wire temperature sensor


## SenseHat

### Calvin configuration

The following capability needs to be configured to run this script:
- `io.temperature`

A `calvin.conf` file is prepared for this purpose. For the `calvin.conf` to be
loaded, start the calvin script from within the directory the `calvin.conf`
file is placed. For other ways of loading the configuration, please see
the Calvin Wiki page about [Configuration](https://github.com/EricssonResearch/calvin-base/wiki/Configuration)


## 1-wire sensor

### Calvin configuration
In order to load the `w1temp_impl` capability, the file `calvin.conf` needs to be
updated to:

    {
        "calvinsys": {
            "capabilities": {
                "io.temperature": {
                    "comment": "This device talks 1-wire on pin GPIO4",
                    "module": "io.ds18b20thermometer.raspberry_pi.DS18B20",
                    "attributes": {"id": "n/a"}
                }
            }
        }
    }



On the Raspberry Pi, the following line needs to be added to `/boot/config.txt`

    dtoverlay=w1-gpio

__Note, for the change to have effect the Raspberry Pi needs to be restarted.__

In addition, w1-gpio and w1-therm modules needs to be added, run the following commands:

    $ sudo modprobe w1-gpio
    $ sudo modprobe w1-therm
    

## Running


Run the following command from within the directory the `calvin.conf`
file is placed:

    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost temperature.calvin

## DHT

Calvin's internal registry is not strictly needed when running this small example,
it has therefor been turned off. To turn it on and run the application with DHT
instead, remove `CALVIN_GLOBAL_STORAGE_TYPE=\"local\"` from the command. I.e:

    $ csruntime --host localhost temperature.calvin
