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
A collection of keys will be available for the application after registering.
Ensure the keys and secrets allow for the posting of updates (i.e. they need both read and write access)

Update the calvin.conf file with the keys and secrets:

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

Run the following command from within the directory the `calvin.conf`
file is placed:

    $ csruntime --host localhost tweet.calvin
