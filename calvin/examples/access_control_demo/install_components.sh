#!/bin/sh
echo "Installing StopLight component from examples/hue/FlashStopLight.calvin"
if [ ! -d ../hue ]; then
    echo "ERROR: Directory: ../hue not available"
    echo "Component not installed"
    exit
fi
if [ ! -f ../hue/FlashingStopLight.calvin ]; then
    echo "ERROR: File ../hue/FlashingStopLight.calvin not available"
    echo "Component not installed"
    exit
fi

csmanage install component --namespace hue --script ../hue/FlashingStopLight.calvin --component StopLight 
