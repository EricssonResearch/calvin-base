# OpenWeatherMap example

The following calvinscript uses the [http://www.openweathermap.org](OpenWeatherMap) api to fetch the current weather in a small
town in southern Sweden and print it.


    weather : web.OpenWeatherMap()
    city : std.Constant(data="Ystad", n=1)
    forecast : io.Print()
    status: io.Print()
    
    city.token > weather.city
    weather.forecast > forecast.token
    weather.status > status.token


The token from weather.forecast is a json struct of the form

    {                         
      "city": "Ystad",        
      "weather": "few clouds",
      "temperature": 3.7,
      "country": "SE"
    }
	
The api call requires an api key (called `appid`) which you get when registering on the site above. It should be given as a private
attribute to the runtime on startup, e.g.

    $ csruntime --host localhost weather.calvin --attr-file weather-credentials.json

where the file `weather-credentials.json` contains (at least)

	{                             
	  "private": {                
	    "web": {                  
	      "openweathermap.com": { 
	        "appid": "<appid as given when registering>"
	      }                       
	    }                         
	  }                           
	}                             
