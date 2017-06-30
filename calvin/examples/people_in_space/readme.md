# In space

A small app which polls the number people currenly known to be in space once per
hour and when the list changes, the people and the craft they are on is printed
to standard out.


## Setup

### Hardware

- A computer to run the script is enough.


## Running

Run the script with the following command:

Run the following command from within the directory the `calvin.conf`
file is placed:

    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost --keep-alive inspace.calvin

## DHT

Calvin's internal registry is not strictly needed when running this small example,
it has therefor been turned off. To turn it on and run the application with DHT
instead, remove `CALVIN_GLOBAL_STORAGE_TYPE=\"local\"` from the command. I.e:

    $ csruntime --host localhost --keep-alive inspace.calvin
