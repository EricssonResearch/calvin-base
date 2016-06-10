# Security Policy Example

This example shows how authorization policies can be used to deny access and 
trigger a smart migration of an actor to another runtime where access is permitted.

The application will get images from an IP camera and show the images on the laptop.
Two Raspberry Pis are used in the demo and they are able to get images from two 
different IP cameras.

The application deployment requirements specify that all actors except the camera 
actor must be placed on the laptop. For the camera actor the requirement is that 
it must be placed on a runtime that has a certain address. This address corresponds 
to the address attribute that both runtimes on the Raspberry Pis have, so the camera 
actor may be placed on any of those two devices.

One of the Raspberry Pis has a policy saying that camera access is permitted only at
a certain time of the day (the time range can easily be changed). By setting a time 
range that lets you access the camera for a minute and then denies the access, a smart
migration will be triggered. Calvin will find the other Raspberry Pi runtime, where 
camera access is permitted, and migrate the camera to that runtime. This means that
images from the other camera will be displayed instead.


## Setup

The example assumes that you have the following devices:

 - A laptop
 - Two Raspberry Pis
 - Two IP cameras (with username "root" and password "pass")

The router has been configured to give static IP addresses to all devices
(the example has to be modified if the IP addresses are changed):

 - 192.168.1.2: laptop
 - 192.168.1.3: Raspberry Pi 1
 - 192.168.1.4: IP Camera 1
 - 192.168.1.5: Raspberry Pi 2
 - 192.168.1.6: IP Camera 2


On all three devices, go to the subdirectory `setup` in this example folder and run 
one of the following scripts (choose the one that corresponds to the device): 

	./setup_laptop.sh

	./setup_raspberry1.sh

	./setup_raspberry2.sh

The setup script will copy policies and certificates to the correct directories.


## Run the example

1. On laptop: start the runtime which also acts as storage for the other runtimes
	
		./start_runtime_laptop.sh


2. On Raspberry Pi 1: change start and end time in policy (choose for example a time range 
that will result in a smart migration after a minute) and start the runtime
	
		./change_policy.sh "08:00" "10:00"
		./start_runtime_raspberry1.sh


3. On laptop: deploy the application (images from the camera will be displayed)
	
		./start_policy_demo.sh


4. On Raspberry Pi 2: start the runtime (the camera actor will be migrated to this runtime 
when access is denied on Raspberry Pi 1 and you will see images from the other camera)
	
		./start_runtime_raspberry2.sh
