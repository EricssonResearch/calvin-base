# Temperature example #

Read temeprature from a thermometor.

## 1-wire sensor

On Raspberry Pi, this needs w1-gpio and w1-therm modules:

    modprobe w1-gpio
    modprobe w1-therm
    
Do not forget to edit `/boot/config.txt` and add

        dtoverlay=w1-gpio

and create a file `calvin.conf` with the following contents:

    {
        "global": {
            "environmental_sensor_plugin": "platform/raspberry_pi/w1temp_impl",
        }
    }

## SenseHat

Create a file `calvin.conf` with the following contents:

    {
        "global": {
            "environmental_sensor_plugin": "platform/raspberry_pi/sensehat_impl",
        }
    }

## Running the example

Ensure the configuration file is in the search path; either start the calvin runtime from this directory, or add this path to CALVIN\_CONFIG\_PATH. Then execute

    $ csruntime --host localhost temperature.calvin
