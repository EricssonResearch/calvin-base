# Android Access Control Example #

__NOTE__: The Android Calvin contrained platform is not actively maintained, thus this example is unlikely to work out of the box.

This example shows how an access control system for a door can be used together with a Calvin runtime on an Android device.

## Setup

### Hardware

- Android device running Calvin Constrained

- Computer with a monitor

- Raspberry Pi with a servo (Futaba S3003 with a Servo Pi Hat from adafruit)

### Installation

##### Calvin Constrained Preparations

1. Make sure you have cloned [Calvin Constrained](https://github.com/EricssonResearch/calvin-constrained) from Github.

2. Follow the [instructions](https://github.com/EricssonResearch/calvin-constrained/blob/master/runtime/south/platform/android/README.md) to build and install Calvin Constrained for Android.

3. Make sure you have Android studio installed. If not, follow the [instructions](https://developer.android.com/studio/index.html) to install it.

4. Open the Android project `[calvin-constrained-dir]/runtime/south/platform/android/examples/access_control` in Android Studio, and install the application on your device.

##### Calvin Base Preparations

Install dependencies using:

    § pip install -r requirements
   
## Running

#### Start Calvin Base Runtimes

The example is most safely run using the proxy storage.

Copy the `config/calvin.conf_computer` file to the root of your Calvin installation and name it `calvin.conf`. Start the runtime on the computer by running

    ./start_computer.sh [HOST]
   
replace `[HOST]` with the IP-address of your computer.

Then open a shell on the Raspberry Pi and copy the `config/calvin.conf_raspberry` file to the root of your Calvin installation and name it `calvin.conf`. Execute the following on the Raspberry Pi to start the runtime.

    ./start_raspberry.sh [HOST] [COMPUTER]

replace `[HOST]` with the IP-address of the Raspberry PI. Also replace `[COMPUTER]` with the address of the computer (used to configure proxy storage), using the `calvinfcm` scheme and port `5001`. So, if the IP address of the computer is `192.168.0.108` then the `[COMPUTER]` field should be `calvinfcm://192.168.0.108:5001`.

#### Start the Android Runtime

Launch the Calvin application and enter the address to the computer in the "Proxy runtime URIs" field. Use the `calvinip://[HOST]:[PORT]` notation.

Tap "start" to start the Android runtime.

Launch the Access Control application on the Android device. The application will automatically register itself as a Calvin sys in the Calvin runtime.

#### Run the Example
Before running the example it can be a good idea to make sure that three runtimes are visible using the csweb tool.

To run the example, simply deploy one of the scripts in the scripts directory.
