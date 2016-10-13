REST-based stdout
=================

Edit the file `server_attr.json` to reflect your receiving server. The example assumes a webserver running on `localhost` listening on port 8087 with a service `add_message` which receives POST-data.

    {
    	"private": {
    		"io": {
    			"stdout": {
    				"url": "http://localhost:8087/add_message"
    			}
    		}
    	}
    }

To start a runtime with this "stdout" backend, change the file `server_attr.json` to reflect the webservice you want to use (The data is sent as POST data.) Start `csruntime` with

    $ CALVIN_GLOBAL_STDOUT_IMPL=\"rest_impl\" csruntime --host <your ip> --attr-file server_attr.json

and the `io.Print` actor will now make use of this new standard out.

