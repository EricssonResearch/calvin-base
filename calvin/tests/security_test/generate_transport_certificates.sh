#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DOMAIN_NAME="testdomain"
CA_CERT=$DIR/$DOMAIN_NAME/cacert.pem

printf $DIR
mv $DIR/runtimes/truststore_for_signing/93d58fef.0 $DIR
rm -rf $DIR/$DOMAIN_NAME
rm -rf $DIR/runtimes

printf "\n\n--------Generate a CA--------\n"
csmanage ca create $DOMAIN_NAME --dir=$DIR

printf "\n\n--------Generate runtimes CSRs and have CA sign them--------\n"
for RT_NBR in {1..4};
do
    csmanage runtime create $DOMAIN_NAME '{"indexed_public":{"node_name":{"name":"testNode'$RT_NBR'", "organization":"org.testexample"}}}' --dir=$DIR
    csmanage ca signCSR $DOMAIN_NAME $DIR/runtimes/org.testexample----testNode$RT_NBR/*.csr --dir=$DIR
done

printf "\n\n--------Export CA cert--------\n"
csmanage ca export $DOMAIN_NAME $DIR --dir=$DIR

printf "\n\n--------Import CA cert into runtimes truststore_for_transport folder--------\n"
csmanage runtime trust $DIR/fba18c26.0 transport --dir=$DIR
rm $DIR/fba18c26.0

printf "\n\n--------Copy trusted signing cert back to truststore_for_signing--------\n"
mv $DIR/93d58fef.0 $DIR/runtimes/truststore_for_signing/93d58fef.0

for file in $DIR/$DOMAIN_NAME/newcerts/*
do
    csmanage runtime import $file --dir=$DIR
done

printf "\n\n--------Copy runtime 2 and 4:s certificate into repsectives others folder--------\n"
cp $DIR/runtimes/org.testexample----testNode2/mine/* $DIR/runtimes/org.testexample----testNode4/others
cp $DIR/runtimes/org.testexample----testNode4/mine/* $DIR/runtimes/org.testexample----testNode2/others
