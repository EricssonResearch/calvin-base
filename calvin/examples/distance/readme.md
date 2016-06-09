# Distance sensor example #

Example on how to use a SR04 Ultrasonic distance sensor with Calvin on a Raspberry Pi.

Running the example:

    $ csruntime --host localhost distance.calvin --attr-file gpio-pins.json

Remember to edit the file `gpio-pins.json` to reflect your pin assignment (if it differs from the one specified in the file.) The default pin-settings used in this example are (in BCM-mode)

    Trig: 23
    Echo: 24

Vcc needs +5v (pin 2). For ground, any ground pin works of course. I like pin 6 myself.