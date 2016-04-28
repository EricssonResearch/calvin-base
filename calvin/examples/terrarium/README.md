Temperature & humidity monitor
==============================

A small app for monitoring the humidity and temperature using a Raspberry Pi SenseHat. 

Usage:

    csruntime --host localhost -w 0 monitor.calvin --attr-file twitter_credentials.json

The allowed range can be changed by modifying the following lines

    humid_range : std.SetLimits(lower=40, upper=80)
    temp_range: std.SetLimits(lower=20, upper=33)

and substituting whatever temperature and humidity is suitable. Note: Temperature is in centigrade (C).

When a value falls outside of the given interval, the background of the SenseHat display will change to red and a tweet with the offending value will be sent (if the twitter credentials are correctly configured in the twitter\_credentials.json file)

__NOTE__: Do _not_ use this application for monitoring live animals if their well-being and/or life depends on it functioning correctly! It has not been tested extensively and it cannot be guaranteed to function the way you expect it to.

Installation
============

Using raspbian image [`2016-03-08-raspbian-jessie-lite.img`](https://www.raspberrypi.org/downloads/raspbian/), the following installs Calvin and necessary dependencies:

- Expand file system to use entire sd-card using [`raspi-config`](https://www.raspberrypi.org/documentation/configuration/raspi-config.md)(if necessary)
- `apt-get update`
- `apt-get install -y python python-dev build-essential git libssl-dev libffi-dev sense-hat`
- `apt-get remove python-pip`
- `easy_install -U pip` 
- `git clone https://www.github.com/EricssonResearch/calvin-base`
- `cd calvin-base`
- `pip install -r requirements.txt -r test-requirements.txt`
- `pip install --upgrade pyasn1 setuptools six`
- `pip install -e .`


