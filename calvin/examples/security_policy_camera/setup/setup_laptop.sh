#!/bin/sh

mkdir -p ~/.calvin/security/runtimes
mkdir ~/.calvin/security/policies
cp -r ../identity_provider ~/.calvin/security/
cp ../policies/laptop/* ~/.calvin/security/policies/
cp -r ../certificates/com.ericsson++++laptop ~/.calvin/security/runtimes/
cp -r ../certificates/truststore_for_transport ~/.calvin/security/runtimes/