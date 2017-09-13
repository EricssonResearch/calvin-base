# Weather service example

In this example the [OpenWeatherMap](http://www.openweathermap.org) API is used to fetch information on current weather by configuring calvinsys to use it as a virtual sensor.

## Setup

### Hardware

- A computer with access to the internet is enough.

### Register for an api key 

The weather service requires an api key (called `appid`) which you get when registering on the site above. This should be entered in the configuration file `calvin.conf` by changing all occurrences of `<appid goes here>` to your api key.

## Examples

The `weather.calvin` app is configured to report the weather in New York, USA:

    $ csruntime --host localhost weather.calvin

while `localweather.calvin` will report the weather based on the location of your runtime - provided this has been configured:

    $ csruntime --host localhost localweather.calvin

The default is Stockholm, Sweden but this is configurable (for obvious reasons.) The file `attributes.json` sets the location of the runtime to London:

    $ csruntime --host localhost localweather.calvin --attr-file attributes.json

The app `weather_data.calvin` queries the service for the weather in a few cities around the world:

    $ csruntime --host localhost weather_data.calvin

The weather service can also serve as a pure sensor in, for example, the temperature or humidity apps from the Sensor Kit example:

    $ csruntime --host localhost ../sensor-kit/temperature.calvin

and

    $ csruntime --host localhost ../sensor-kit/humidity.calvin

For this case, the temperature from the location the runtime is located is used, so by changing the city and country code in `attributes.json`, you can have a thermometer placed all over the world

    $ csruntime --host localhost ../sensor-kit/temperature.calvin --attr-file attributes.json


## DHT

Running a single application on a stand-alone runtime does not required the distributed features of Calvin, thus the distributed registry has been turned off in the config. 
