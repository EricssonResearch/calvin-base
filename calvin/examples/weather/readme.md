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

Run the script with the following command:

    $ CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host localhost weather.calvin --attr-file weather_credentials.json
    
## DHT

Calvin's internal registry is not strictly needed when running this small example,
it has therefor been turned off. To turn it on and run the application with DHT
instead, remove `CALVIN_GLOBAL_STORAGE_TYPE=\"local\"` from the command. I.e:

    $ csruntime --host localhost weather.calvin --attr-file weather_credentials.json
