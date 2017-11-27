# Temperature & humidity monitor

A small app for monitoring the humidity and temperature using a Raspberry Pi
with a [Sense HAT](https://www.raspberrypi.org/products/sense-hat/).


## Overview

The allowed range can be changed by modifying the following lines in the Calvin script.

    humid_alarm_limit : CheckLimit(lower=40, upper=80)
    temp_alarm_limit : CheckLimit(lower=20, upper=33)

and substituting whatever temperature and humidity is suitable. Note: Temperature is in centigrade (C).

When a value falls outside of the given interval, the value will be prefixed with
a WARNING note on the SenseHat display. A tweet with the offending value will
be sent (if the twitter credentials are correctly configured in the
`twitter_credentials.json` file)

__NOTE__: Do _not_ use this application for monitoring live animals if their
well-being and/or life depends on it functioning correctly! It has not been
tested extensively and it cannot be guaranteed to function the way you expect
it to.


## Setup

### Hardware

The example assumes the following devices:

- A Raspberry Pi with a [Sense HAT](https://www.raspberrypi.org/products/sense-hat/)

### Python packages

- [`sense-hat`](https://pythonhosted.org/sense-hat/)

### Installation

Using [`raspbian jessie lite`](https://www.raspberrypi.org/downloads/raspbian/), with a working calvin installation,
run `install-deps.sh` to install necessary dependencies for this example. Note: It may be a good idea to expand the file
if this is not already done using [`raspi-config`](https://www.raspberrypi.org/documentation/configuration/raspi-config.md).


### Calvin configuration

The following capabilities needs to be loaded to run this script:
- `io.temperature`
- `io.humidity`
- `io.stdout`

A `calvin.conf` file is prepared for this purpose. For the `calvin.conf` to be
loaded, start the calvin script from within the directory the `calvin.conf`
file is placed. For other ways of loading the configuration, please see
the Calvin Wiki page about [Configuration](https://github.com/EricssonResearch/calvin-base/wiki/Configuration)



## Running

Run one of the following commands from within the directory the `calvin.conf` file is placed:

    with twitter output:
    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost --keep-alive monitor-tweet.calvin --attr-file twitter_credentials.json

    or, without twitter output:
    § CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost --keep-alive monitor-print.calvin


## DHT

Calvin's internal registry is not strictly needed when running this small example,
it has therefor been turned off. To turn it on and run the application with DHT
instead, remove `CALVIN_GLOBAL_STORAGE_TYPE=\"local\"` from the command. I.e:

    with twitter output:
    $ csruntime --host localhost --keep-alive monitor-tweet.calvin --attr-file twitter_credentials.json

    or, without twitter output:
    § csruntime --host localhost --keep-alive monitor-print.calvin
