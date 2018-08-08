# Pushbullet 

Here we use the [Pushbullet](http://www.pushbullet.com) API to push a message to a channel:

## Setup

### Hardware

- A computer to run the script is enough.


### Installation

Install dependencies using:

    § pip install -r requirements.txt


### Register 

In order to use the pushbullet API, you need to register at
[https://www.pushbullet.com](https://www.pushbullet.com) and
create an access token (api key) on the page "My Account."
In order to post something, it is also necessary to create a
channel on [https://www.pushbullet.com/my-channel](https://www.pushbullet.com/my-channel).

Update the calvin.conf file with the api key and channel tag (not channel name!):

    {
        "calvinsys": {
            "capabilities": [
                {
                    "name": "calvinsys.web.pushbullet.channel.post",
                    "module": "web.pushbullet.Pushbullet",
                    "attributes": {"api_key": "<api key>", "channel_tag": "<channel tag>"}
                }
            ]
        }
    }


## Running

Run the following command from within the directory the `calvin.conf`
file is placed:

    $ csruntime --host localhost pushbullet.calvin
