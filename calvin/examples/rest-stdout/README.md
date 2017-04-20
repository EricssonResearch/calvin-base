# REST-based stdout

A small example of how to use a rest implementation as `stdout_plugin` and thus
make the `io.Print` actor use this new standard out.


## Setup

### Hardware

- A computer to run the script is enough.


### Installation

Edit the file `server_attr.json` to reflect your receiving server. The example
assumes a webserver running on `localhost` listening on port 8087 with a service
`add_message` which receives POST-data.

For mor information about attribute files please see the Calvin Wiki page about
[Application Deployment Requirement](https://github.com/EricssonResearch/calvin-base/wiki/Application-Deployment-Requirement)

### Calvin configuration

The following plugins needs to be loaded to run this script:
- stdout_plugin

A `calvin.conf` file is prepared for this purpose. For the `calvin.conf` to be
loaded, start the calvin script from within the directory the `calvin.conf`
file is placed. For other ways of loading the configuration, please see
the Calvin Wiki page about [Configuration](https://github.com/EricssonResearch/calvin-base/wiki/Configuration)


## Running

As a simple example; run `webserver.py` from one terminal and in another
terminal run the `test1.calvin` script provided in examples/sample-scripts

Remember to start `csruntime` from within the directory the `calvin.conf` file
is placed


    $ python webserver.py

    $ csruntime --host localhost --attr-file server_attr.json ../sample-scripts/test1.calvin


The `io.Print` actor will now make use of this new standard out.
