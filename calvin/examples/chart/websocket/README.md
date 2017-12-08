# Websocket example

__Note! Before running this example, make sure the chart example run as expected__

This is a small demo of how to use the WSBroadcast actor for sending charts
through a websocket.

## Setup

### Hardware

- A computer to run the script is enough.


### Installation

In addition to the dependencies introduced in the chart example, websockets
depends on an implementation in autobahn. Install it using:

    § pip install -r requirements


### Calvin configuration

A `calvin.conf` file has been prepared for loading necessary capabilities.
For the `calvin.conf` to be loaded, start the calvin script from within the
directory the `calvin.conf` file is placed. For other ways of loading the
configuration, please see the Calvin Wiki page about [Configuration](https://github.com/EricssonResearch/calvin-base/wiki/Configuration)

## Running

- In a browser open the provided index.html file.

Run one of the following commands from within the directory the `calvin.conf` file is placed:


### Without DHT

Calvin's internal registry is not strictly needed when running this small
example. To turn it off and run the application locally add `CALVIN_GLOBAL_STORAGE_TYPE=\"local\"`
to the command:

    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost --keep-alive webchart.calvin


### With DHT

    § csruntime --host localhost --keep-alive webchart.calvin

