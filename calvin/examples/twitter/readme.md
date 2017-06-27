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
Ensure the keys and secrets allow for the posting of updates (i.e. they need both read and write access)

Update the calvin.conf file with the keys and secret:

    {
        "calvinsys": {
            "capabilities": [
                {
                    "name": "calvinsys.web.twitter.post",
                    "module": "web.twitter.tweepy.Twitter",
                    "attributes": {"consumer_key": "<api key>", "consumer_secret": "<api secret>", "access_token_key": "<app key>", "access_token_secret": "<app secret>"}
                }
            ]
        }
    }


## Running

Run one of the following commands from within the directory the `calvin.conf` file is placed:

### With DHT

    $ csruntime --host localhost tweet.calvin

### Without DHT

Calvin's internal registry is not strictly needed when running this small
example. To turn it off and run the application locally add `CALVIN_GLOBAL_STORAGE_TYPE=\"local\"`
to the command:

    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost tweet.calvin

