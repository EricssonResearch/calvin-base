# Display sensor data

This example uses the Raspberry Pi Sense HAT (https://www.raspberrypi.org/products/sense-hat/) to get environmental sensor data and the Sense HAT LED matrix and/or a Adafruit character display (https://www.adafruit.com/products/1110) to display the sensor data.

## Hardware

Raspberry Pi with an Sense HAT (https://www.raspberrypi.org/products/sense-hat/)
Raspberry Pi with an Adafruit Character LCD https://www.adafruit.com/products/1110

## Adafruit Character LCD instructions

https://learn.adafruit.com/adafruit-16x2-character-lcd-plus-keypad-for-raspberry-pi

## Python packages

https://pythonhosted.org/sense-hat/
https://github.com/adafruit/Adafruit_Python_CharLCD

## Calvin configuration

calvin.conf to use Adafruit Character LCD as display:

    {
      "global": {
        "display_plugin": "platform/raspberry_pi/adafruitcharlcd_impl",
        "actor_paths": ["./devactors"]
      }
    }

calvin.conf to use Sense HAT as display and to get sensor data:

    {
      "global": {
        "display_plugin": "platform/raspberry_pi/sensehat_impl",
        "environmental_sensor_plugin": "platform/raspberry_pi/sensehat_impl",
        "actor_paths": ["./devactors"]
      }
    }

calvin.conf to use stdout as display:

    {
      "global": {
        "display_plugin": "stdout_impl",
        "actor_paths": ["./devactors"]
      }
    }

## Running

Deploy `display_sensor.calvin` and migrate the `display` actor to a Calvin runtime with a configured `display_plugin` and the `sensor` actor to a Calvin runtime with a configured `environmental_sensor_plugin`.