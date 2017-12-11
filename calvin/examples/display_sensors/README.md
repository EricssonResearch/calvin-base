# Display sensor data

This example uses the Raspberry Pi with a [Sense HAT](https://www.raspberrypi.org/products/sense-hat/)
to get environmental sensor data and the Sense HAT LED matrix and/or an
[Adafruit character display](https://www.adafruit.com/products/1110) to display the sensor data.

## Setup

### Hardware

The example assumes the following devices:

- A computer 
- A Raspberry Pi with a [Sense HAT](https://www.raspberrypi.org/products/sense-hat/)
- A Raspberry Pi with an [Adafruit character display](https://www.adafruit.com/products/1110)

### Adafruit Character LCD instructions

[adafruit-16x2-character-lcd-plus-keypad-for-raspberry-pi](https://learn.adafruit.com/adafruit-16x2-character-lcd-plus-keypad-for-raspberry-pi)

### Python packages

- [`sense-hat`](https://pythonhosted.org/sense-hat/)
- [`Adafruit_Python_CharLCD`](https://github.com/adafruit/Adafruit_Python_CharLCD)


### Calvin configuration

Rename the relevant config file on each device to calvin.conf

For the Adafruit Character LCD the calvin.conf is set to use 
Adafruit Character LCD with no plate. I.e. `Adafruit_CharLCD`.
If `Adafruit_CharLCDPlate` (_with plate_) is requested, change the
calvin.conf to:

    {
        "calvinsys": {
            "capabilities": {
                "io.stdout": {
                    "module": "io.adafruit16x2lcd.raspberry_pi.Plate",
                    "attributes": {}
                }
            }
        }
    }

Note that when using __NOplate__, the pins are hardcoded to:

    lcd_rs=26
    lcd_en=21
    lcd_d4=20
    lcd_d5=13
    lcd_d6=16
    lcd_d7=19
    lcd_columns=16
    lcd_rows=2
    lcd_backlight=4


## Running

Start calvin on the computer and on the Raspberry Pi's using the accompanying
scripts. The scripts must be given the IP address of the respective devices
as arguments. In addition, make sure to run the start script from the directory
where the `calvin.conf` file is placed.

Start `csweb` and log onto one of the devices - preferably the `server`
device. If all is well, there should be three devices listed. If not, reload
the page a few times.

Click `deploy` and select the script `display_sensors.calvin`. Got to the
`Applications` view and select your application from the Application drop-down
menu.

Select the `sensor` actor from the Actor drop-down menu and migrate it to the
runtime with a configured `environmental_sensor_plugin`.

Since all runtimes are configured with an `display_plugin` the
`display` actor can be migrated to the runtime of your choosing.
