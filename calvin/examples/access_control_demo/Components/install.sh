#!/bin/sh
echo "Installing IPCamera component to namespace media"
csinstall --script IPCamera.calvin --namespace media --component IPCamera --force
echo "Installing RedGreenLight component to namespace hue"
csinstall --script SmartLight.calvin --namespace hue --component RedGreenLight --force
