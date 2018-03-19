# OPC-UA and Calvin

This (small) example demonstrates how to get Calvin to collect data from an
OPC-UA server by subscribing to a collection of parameters.

The parameters are defined for the `data.source` capability in `calvin.conf`
(see also `paramconfig` in the example.)

Format of paramconfig:

```json
{
    "endpoint": "opc.tcp://address:port",
    "namespace": "namespace (name, not id)",
    "paramconfig": {
        "tag": {
            "address": "node_id (without namespace)",
            "info": "N/A"
        }
    },
    "timeout": 10,
    "monitoring_interval": 1000
}
```

Format of data item:

```json
{
    "status": 0,
    "calvints": 1521459808.580605,
    "sourcets": 1521459807.950132,
    "value": true,
    "tag": "tag",
    "serverts": 1521459792.353072,
    "type": "Boolean",
    "id": "node_id (without namespace)"
}
```

Note: This format will likely change.

When data is coming in at a higher speed than it can be processed (e.g. when
there are connection issues) it may be necessary to persist the data to disk
in order to ensure it is not (completely) lost in case of power failure or
spurious crashes/reboots. For this, there is a persistent buffer actor which
will use the `buffer.persistent` capability to store data - see `buffer.calvin`.

Note that there are no guarantees on the ordering of the data.

## Setup

### Installation

Install dependencies using:

    $ pip install -r requirements.txt

## Running

Run the script with the following command:

    $ csruntime --host localhost opcua-subscribe.calvin

