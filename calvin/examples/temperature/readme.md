# Temperature example #

Read 1-wire temperature sensor. 

On Raspberry Pi, this needs w1-gpio and w1-therm modules:

    modprobe w1-gpio
    modprobe w1-therm
    
 Do not forget to edit /boot/config.txt

        dtoverlay=w1-gpio
		
Ensure the configuration file is in the search path; either start the calvin runtime from this directory, or add this path to CALVIN\_CONFIG\_PATH.