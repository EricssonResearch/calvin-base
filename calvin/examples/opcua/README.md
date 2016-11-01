OPCUA to Calvin
===============

The two examples here show how to connect Calvin to an OPCUA server and, given a list of node id's, either poll at a given interval, or setup subscriptions and receive updates when a value changes.

Note that this has not been extensively tested against OPCUA servers. There seems to be some incompatibilities between some OPCUA servers and the python implementation `freeopcua` (which Calvin uses in the implementation.) In partiular, subscriptions does not always work, thus the polling implementation.