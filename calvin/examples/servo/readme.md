# Servo control

This example uses a pushbutton to control a micro servo connected to a Raspberry Pi.

## Hardware

- A Raspberry Pi
- A pushbutton connected to GPIO pin 23 (BCM)
- A Tower PRO SG90 micro servo connected to GPIO pin 17 (BCM)

## Calvin configuration

calvin.conf to include the Servo actor and to use the RPi.GPIO plugin:

    {
      "global": {
        "gpio_plugin": "platform/raspberry_pi/rpigpio_impl",
        "actor_paths": ["./devactors"]
      }
    }

## Running

Start a Calvin runtime on the Raspberry Pi and deply `servo.calvin`, use the pushbutton to move the servo to its left and right position.
