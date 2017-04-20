# OPCUA to Calvin

The example shows how to connect Calvin to an OPCUA server and, given a
list of node id's, either poll at a given interval, or setup subscriptions and
receive updates when a value changes.

Note that this has not been extensively tested against OPCUA servers. There seems
to be some incompatibilities between some OPCUA servers and the python
implementation `freeopcua` (which Calvin uses in the implementation.) In
partiular, subscriptions does not always work, thus the polling implementation.


## Setup

### Hardware

- A computer to run the script is enough.


### Installation

Install dependencies using:

    § pip install -r requirements.txt


## Running

Run the script with one of the following commands:

### With DHT

    $ csruntime --host localhost opcua-subscribe.calvin


### Without DHT

Calvin's internal registry is not strictly needed when running this small
example. To turn it off and run the application locally add
`CALVIN_GLOBAL_STORAGE_TYPE=\"local\"` to the command:

    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost opcua-subscribe.calvin
