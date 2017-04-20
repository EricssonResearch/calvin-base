# OpenWeatherMap example

In this example the [OpenWeatherMap](http://www.openweathermap.org) API is used
to fetch the current weather in a small town in southern Sweden and print it.

## Setup

### Hardware

- A computer to run the script is enough.


### Register 

The api call requires an api key (called `appid`) which you get when registering
on the site above, it should be given as a private attribute to the runtime on
startup.

Update the following row of the file `weather-credentials.json` with the
received `appid`:

    "appid": "<appid as given when registering>"


## Running

Run the script with one of the following commands:

### With DHT

    $ csruntime --host localhost weather.calvin --attr-file weather_credentials.json


### Without DHT

Calvin's internal registry is not strictly needed when running this small
example. To turn it off and run the application locally add `CALVIN_GLOBAL_STORAGE_TYPE=\"local\"`
to the command:

    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost weather.calvin --attr-file weather_credentials.json
