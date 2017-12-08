# Charts example

This example demonstrates a calvin wrapper around the google-chartwrapper for the
Google Chart API.

## Setup

### Hardware

- A computer to run the script is enough.


### Installation

Install dependencies using:

    § pip install -r requirements.txt


### Calvin configuration

A `calvin.conf` file has been prepared for loading necessary capabilities.
For the `calvin.conf` to be loaded, start the calvin script from within the
directory the `calvin.conf` file is placed. For other ways of loading the
configuration, please see the Calvin Wiki page about [Configuration](https://github.com/EricssonResearch/calvin-base/wiki/Configuration)


## Running
A lot of the charactericts for each chart can be set at initiation through the
`chart_parameters`in each script.

    /////////////////////////////////////////////////
    //              Chart definitions              //
    /////////////////////////////////////////////////
    define CHART_PARAMETERS = {"chart_title": ["More parameters", "3AB8E1", 24],
                               "chart_bar": [20, 30],
                               "chart_size": [600, 450],
                               "chart_scale": [0, 1000],
                               "chart_color": ["72BCD4"],
                               "chart_grid": [0, 10, 1, 1],
                               "chart_line": [4,3,0],
                               "chart_margin": [100, 100, 75, 100],
                               "chart_fill": [["c", "lg", 45, "white", 0, "EFEFEF", 0.75]["bg", "lg", 45, "EFEFEF", 0, "CDCDCD", 0.75]]
                               "axes_type": "xxyy",
                               "axes_label": [[1, "Time"], [3, "Value"]],
                               "axes_range": [2, 0, 1000, 250],
                               "axes_style": [[1, "3AB8E1", 14],[3, "3AB8E1", 14]]}

Have a look at the examples for some inspiration of how to initiate different
charts. If the examples isn't enough, the functions for setting the parameters
in [chart.py](https://github.com/EricssonResearch/calvin-base/blob/develop/calvin/runtime/south/plugins/charts/google_charts_impl/chart.py)
will hopefully be of help.

Run the following command from within the directory the `calvin.conf`
file is placed:

    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost --keep-alive nice_looking.calvin

## DHT

Calvin's internal registry is not strictly needed when running this small example,
it has therefor been turned off. To turn it on and run the application with DHT
instead, remove `CALVIN_GLOBAL_STORAGE_TYPE=\"local\"` from the command. I.e:

    $ csruntime --host localhost --keep-alive nice_looking.calvin


## Other examples

In the command above `nice_looking.calvin` is the name of the script to run but
other examples are also available. Change `nice_looking.calvin` to run another
example:

- `dynamic_hbar.calvin`
- `dynamic_line.calvin`
- `dynamic_vbar.calvin`
- `meter.calvin`
- `static_hbar.calvin`
- `static_vbar.calvin`


In addition an example for sending charts over a websocket are available in the [websocket](./websocket)
directory.


## Additional documentation
For a more profound documentation of how to use the functionality than can be found
in the source files, please see the documentation for the
[GChartWrapper](http://justquick.github.io/google-chartwrapper-apidoc/)

All parameters supported by the Google Chart API are listed [here](https://developers.google.com/chart/image/docs/chart_params)

