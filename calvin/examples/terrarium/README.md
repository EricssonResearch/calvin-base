Temperature & humidity monitor
==============================

A small app for monitoring the humidity and temperature using a Raspberry Pi SenseHat. 

Usage:

    csruntime --host localhost -w 0 monitor.calvin --attr-file twitter_credentials.json

The allowed range can be changed by modifying the following lines

    humid_range : std.SetLimits(lower=40, upper=80)
    temp_range: std.SetLimits(lower=20, upper=33)

and substituting whatever temperature and humidity is suitable. Note: Temperature is in centigrade (C).

When a value falls outside of the given interval, the background of the SenseHat display will change to red and a tweet with the offending value will be sent (if the twitter credentials are correctly configured in the twitter\_credentials.json file)

__NOTE__: Do _not_ use this application for monitoring live animals if their well-being and/or life depends on it functioning correctly! It has not been tested extensively and it cannot be guaranteed to function the way you expect it to.