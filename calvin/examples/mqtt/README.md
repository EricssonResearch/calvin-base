# MQTT example

In this example the `paho-mqtt` implementation of the __mqtt-plugin__, is used
to subscribe and publish messages over mqtt.


## Setup

### Hardware

- Two devices capable of running a Calvin script.


### Installation

Install dependencies using:

    § pip install -r requirements.txt


### Calvin configuration

The following plugins needs to be loaded to run this script:
- mqtt_plugin

A `calvin.conf` file is prepared for this purpose. For the `calvin.conf` to be
loaded, start the calvin script from within the directory the `calvin.conf`
file is placed. For other ways of loading the configuration, please see
the Calvin Wiki page about [Configuration](https://github.com/EricssonResearch/calvin-base/wiki/Configuration)


## Running

The scripts needs to be run from within the directory the `calvin.conf` file is
placed. To run the scripts, execute the following commands:

### Subscribing device

    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost --keep-alive mqtt_sub_test.calvin

### Publishing device

Run the following command:

    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost --keep-alive mqtt_pub_test.calvin


## DHT

Calvin's internal registry is not strictly needed when running this small example,
it has therefor been turned off. To turn it on and run the application with DHT
remove `CALVIN_GLOBAL_STORAGE_TYPE=\"local\"` from the commands.
