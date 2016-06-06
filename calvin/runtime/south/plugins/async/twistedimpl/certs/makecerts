#!/bin/bash -eu

##############################################################################
#
# Generate Certificates for PyDTLS Unit Testing
#
# This script is invoked manually (as opposed to by the unit test suite), in
# order to generate certain certificates that are required to be valid by
# the unit test suite.
#
# This script is not portable: it has been tested on Ubuntu 13.04 only. New
# certificates are written into the current directory.
#
# Copyright 2014 Ray Brown
#
##############################################################################

DIR=`dirname "$0"`

# Generate self-signed certificate for the certificate authority
echo Generating CA...; echo
openssl req -config "$DIR/openssl_ca.cnf" -x509 -newkey rsa -nodes -keyout tmp_ca.key -out ca-cert.pem -days 3650

# Generate a certificate request
echo Generating certificate request...; echo
openssl req -config "$DIR/openssl_server.cnf" -newkey rsa -nodes -keyout tmp_server.key -out tmp_server.req

# Sign the request with the certificate authority's certificate created above
echo Signing certificate request...; echo
openssl x509 -req -in tmp_server.req -CA ca-cert.pem -CAkey tmp_ca.key -CAcreateserial -days 3650 -out server-cert.pem

# Build pem file with private and public keys, ready for unprompted server use
cat tmp_server.key server-cert.pem > keycert.pem

# Clean up
rm tmp_ca.key tmp_server.key tmp_server.req ca-cert.srl
