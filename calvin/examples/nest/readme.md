# Nest Device interaction example #

The following calvinscript uses an actor to interact with a generic Nest Device 
and get the current temperature from a thermostat


    source : std.Counter()
    delay : std.ClassicDelay(delay=1)
    devid : std.Constant(data="DFF9", n=1000)
    operation : std.Constant(data="get", n=1000)
    property : std.Constant(data="temperature", n=1000)
    thermostat : integration.NestDevice()
    io : io.Print()
    void : std.Void()
    
    source.integer > delay.token
    delay.token > thermostat.trigger
    operation.token > thermostat.operation
    void.void > thermostat.value
    devid.token > thermostat.device
    property.token > thermostat.property_name
    thermostat.result > io.token


	
Run the script with 
    $ csruntime --host localhost nest_device.calvin --attr-file nest_credentials.json


# Nest Structure interaction example #

    structure : integration.NestStructure(structure_name="HomeTest")
    io : io.Print()
    source : std.Counter()
    delay : std.ClassicDelay(delay=1)
    
    source.integer > delay.token
    delay.token > structure.trigger
    structure.devices > io.token
    
Run the script with 
    $ csruntime --host localhost nest_structure.calvin --attr-file nest_credentials.json

where the file `nest_credentials.json` contains (at least)

	{
        "private": {
                "web": {
                    "nest.com": {
                          "username": "<YOUR USERNAME OR EMAIL>",
                          "password": "<YOUR PASSWORD>"
                    }
                }
	}


