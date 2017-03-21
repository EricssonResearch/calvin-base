#!/bin/bash

#DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DIR=~/.calvin/test_generate_cert_script
DOMAIN_NAME="testdomain"
CA_CERT=$DIR/$DOMAIN_NAME/cacert.pem

printf "dir=%s\n" $DIR
rm -rf $DIR/$DOMAIN_NAME
rm -rf $DIR/runtimes

printf "\n\n--------Generate a CA--------\n"
csmanage ca create $DOMAIN_NAME --dir=$DIR

printf "\n\n--------Generate runtimes CSRs and have CA sign them--------\n"
for RT_NBR in {1..5};
do
    NAME="testNode"$RT_NBR
    ATTRIBUTES='{"indexed_public":{"node_name":{"name":"'$NAME'","organization":"org.testexample"}}}'
    csmanage runtime do_it_all $DOMAIN_NAME $ATTRIBUTES --dir=$DIR

done
