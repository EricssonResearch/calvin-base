# Twitter

In this example the [twitter](http://www.twitter.com) API is used to tweet a message:


## Setup

### Hardware

- A computer to run the script is enough.


### Installation

Install dependencies using:

    § pip install -r requirements.txt


### Register 

In order to use the twitter API, you need to register an application at
[https://dev.twitter.com/apps](https://dev.twitter.com/apps)
A collection of keys will be available for the application after registering,
these should be given as private attributes to the runtime on startup.

Update the following rows of the file `twitter_credentials.json` with the
received keys and secrets:

    "consumer_key": "<enter consumer key here>",
    "consumer_secret": "<enter consumer secret here>",
    "access_token_key": "<enter access_token_key here>",
    "access_token_secret": "<enter access_token_secret here>"


## Running

Run one of the following commands from within the directory the `calvin.conf` file is placed:

### With DHT

    $ csruntime --host localhost tweet.calvin --attr-file twitter_credentials.json


### Without DHT

Calvin's internal registry is not strictly needed when running this small
example. To turn it off and run the application locally add `CALVIN_GLOBAL_STORAGE_TYPE=\"local\"`
to the command:

    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost tweet.calvin --attr-file twitter_credentials.json

