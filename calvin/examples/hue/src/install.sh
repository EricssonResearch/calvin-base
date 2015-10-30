#!/bin/sh

echo "Installing Alternate4 to namespace std"
csinstall --script Alternate4.calvin --namespace std --component Alternate4 --force
echo "Installing CmdBuilder to namespace hue"
csinstall --script CmdBuilder.calvin --namespace hue --component CmdBuilder --force
echo "Installing PhilipsHue to namespace hue"
csinstall --script PhilipsHue.calvin --namespace hue --component PhilipsHue --force
echo "Installing PortsToDict3 to namespace json"
csinstall --script PortsToDict3.calvin --namespace json --component PortsToDict3 --force
echo "Installing PortsToDict4 to namespace json"
csinstall --script PortsToDict4.calvin --namespace json --component PortsToDict4 --force
echo "Installing StopLight to namespace hue"
csinstall --script StopLight.calvin --namespace hue --component StopLight --force
echo "Installing URLBuilder to namespace json"
csinstall --script URLBuilder.calvin --namespace json --component URLBuilder --force

