#!/bin/sh

mkdir -p ~/.calvin/security/runtimes
mkdir ~/.calvin/security/policies
cp ../policies/secret_room/* ~/.calvin/security/policies/
cp -r ../certificates/com.ericsson++++secret_room ~/.calvin/security/runtimes/
cp -r ../certificates/truststore_for_transport ~/.calvin/security/runtimes/