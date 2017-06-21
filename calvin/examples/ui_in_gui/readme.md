# UI in GUI

When using a Calvin runtime together with the web-based GUI, it is possible to use virtual instances for the following components:

- io.Print
- io.Log
- io.Switch
- io.Button
- io.TiltSwitch
- io.Light
- io.Buzzer
- io.PWM
- sensor.LightBreaker
- sensor.Temperature
- sensor.Distance

To enable this feature, start the runtime that the GUI is connecting to from this directory in order for the `calvin.conf` configuration file to be activated.

When the app is run, the above components will be shown on-screen.

