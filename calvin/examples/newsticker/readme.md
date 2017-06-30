# A retro-style news-ticker written in Calvin

Continuously print e.g. commit messages from the Calvin repo as they happen, in
a news-ticker fashion (dot-matrix printer not included).


## Overview

Get the latest commit and extract commit timestamp and ETag, print a nicely
formatted commit line. Periodically check repo for changes by comparing the
response header's ETag to our latest known ETag. If the ETag has changed, get
the commits since our last recorded timestamp and print them, update timestamp
and ETag.
 

## Setup

### Hardware

- A computer to run the script is enough.


## Running

Run the script with the following command:

    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost newsticker.calvin


## DHT

Calvin's internal registry is not strictly needed when running this small example,
it has therefor been turned off. To turn it on and run the application with DHT
instead, remove `CALVIN_GLOBAL_STORAGE_TYPE=\"local\"` from the command. I.e:

    $ csruntime --host localhost newsticker.calvin

