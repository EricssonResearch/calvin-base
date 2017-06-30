# Philips Hue example

In this example the Philips Hue API is used to build a Calvin application which
controls a Philips Hue lamp.


## Setup

### Hardware

 - A computer or other device capable of deploying the calvin script.
 - A Philips Hue Lamp.

### Installation

Before running this example, make sure the Philips Hue is available via the API.
Follow the steps in [Philips Hue Getting started](https://www.developers.meethue.com/documentation/getting-started)
to get information about:
- __address__ (_the bridges ip address_)
- __username__ (_this will be a randomly generated username that the bridge creates for you_)
- __lightno__ (_the id of the lamp_)

Now, in the `FlashingStopLight.calvin`, update the line:

    flash : FlashStopLight(address="philips-hue", username="username", lightno=1, interval=2.0)

to reflect your setup - i.e. __address__, __username__, __lightno__ should all be according to
your configuration.


## Running

Run the script with the following command:

    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost --keep-alive FlashingStopLight.calvin

## DHT

Calvin's internal registry is not strictly needed when running this small example,
it has therefor been turned off. To turn it on and run the application with DHT
instead, remove `CALVIN_GLOBAL_STORAGE_TYPE=\"local\"` from the command. I.e:

    $ csruntime --host localhost --keep-alive FlashingStopLight.calvin






