# Rotary encoder example #

Example on how to use a ky 040 rotary encoder with Calvin on a Raspberry Pi.

Running the example:

    $ csruntime --host localhost rotary.calvin --attr-file gpio-pins.json

Remember to edit `gpio-pins.json` to reflect your pin assignment if it differs from the one there, which is (BCM mode):

    clk: 22
    dt : 27
    sw : 17

Needs +3.3v (pin 1, for example). For ground, any ground pin works of course. I like pin 6 myself.