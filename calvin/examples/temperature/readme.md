Read 1-wire temperature sensor. Needs w1-gpio and w1-therm modules:
    modprobe w1-gpio
    modprobe w1-therm
    
    Do not forget to edit /boot/config.txt
        dtoverlay=w1-gpio