#!/bin/sh

mkdir -p ~/.calvin/security/runtimes
mkdir ~/.calvin/security/policies
cp ../policies/entrance/* ~/.calvin/security/policies/
cp -r ../certificates/com.ericsson++++entrance ~/.calvin/security/runtimes/
cp -r ../certificates/truststore_for_transport ~/.calvin/security/runtimes/