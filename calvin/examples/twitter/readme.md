# Twitter example #

The following calvinscript uses the [http://www.twitter.com](twitter) api to tweet a message:

	msg : std.Constant(data="This is another test, please ignore.")
	out : web.Twitter()
	
	msg.token > out.status


In order to use the twitter API, you need to register got get a collection of keys. These  should be given as a private
attribute to the runtime on startup, e.g.

    $ csruntime --host localhost twitter.calvin --attr-file twitter-credentials.json

where the file `twitter-credentials.json` contains (at least)

	{
		"private": {
			"web": {
				"twitter.com": {
					"consumer_key": "<enter consumer key here>",
					"consumer_secret": "<enter consumer secret here>",
					"access_token_key": "<enter access_token_key here>",
					"access_token_secret": "<enter access_token_secret here>"
				}
			}
		}
	}

## Installation

Install dependencies using e.g. `pip install -r requirements`  
