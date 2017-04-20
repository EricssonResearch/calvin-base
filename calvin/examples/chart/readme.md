# Charts example

This example demonstrates a calvin wrapper around the google-chartwrapper for the
Google Chart API.

## Setup

### Hardware

- A computer to run the script is enough.


### Installation

Install dependencies using:

    § pip install -r requirements


### Calvin configuration

The following plugins needs to be loaded to run this script:
- chart_plugin
- image_plugin
- media_framework

A `calvin.conf` file is prepared for this purpose. For the `calvin.conf` to be
loaded, start the calvin script from within the directory the `calvin.conf`
file is placed. For other ways of loading the configuration, please see
the Calvin Wiki page about [Configuration](https://github.com/EricssonResearch/calvin-base/wiki/Configuration)


## Running
A lot of the charactericts for each chart can be set at initiation through the
`chart_parameters`in each script. Have a look at the examples for some inspiration
of how to initiate different charts.

Run one of the following commands from within the directory the `calvin.conf`
file is placed:

### With DHT

    § csruntime --host localhost --keep-alive nice_looking.calvin

### Without DHT

Calvin's internal registry is not strictly needed when running this small
example. To turn it off and run the application locally add `CALVIN_GLOBAL_STORAGE_TYPE=\"local\"`
to the command:

    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost --keep-alive nice_looking.calvin


## Additional documentation
For a more profound documentation of how to use the functionality than can be found
in the source files, please see the documentation for the
[GChartWrapper](http://justquick.github.io/google-chartwrapper-apidoc/)

All parameters supported by the Google Chart API are listed [here](https://developers.google.com/chart/image/docs/chart_params)

