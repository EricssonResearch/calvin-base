#!/bin/bash

#DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DIR=~/.calvin/test_generate_cert_script
DOMAIN_NAME="testdomain"
CA_CERT=$DIR/$DOMAIN_NAME/cacert.pem

printf "dir=%s\n" $DIR
rm -rf $DIR/$DOMAIN_NAME
rm -rf $DIR/runtimes

HOSTNAMES=("examplehostname1,examplehostname1.localdomain.com,examplehostname1.localdomain.com", "examplehostname2,examplehostname2.localdomain.com")
LEN=${#HOSTNAMES[@]}
printf "LEN=%s\n" $LEN

printf "\n\n--------Generate a CA--------\n"
csmanage ca create $DOMAIN_NAME --dir=$DIR

printf "\n\n--------Export CA cert directly into runtimes truststore--------\n"
csmanage ca export $DOMAIN_NAME $DIR/runtimes/truststore_for_transport --dir=$DIR

printf "\n\n--------Generate runtimes CSRs and have CA sign them--------\n"
for ((RT_NBR=0; RT_NBR<$LEN; RT_NBR++ ));
do
    NAME="testNode"$RT_NBR
    printf "name=%s\n" $NAME
    ATTRIBUTES='{"indexed_public":{"node_name":{"name":"'$NAME'","organization":"org.testexample"}}}'
    OUTPUT=$(csmanage runtime create $DOMAIN_NAME $ATTRIBUTES --hostnames=${HOSTNAMES[$RT_NBR]} --dir=$DIR 2>&1)
    NODE_NAME=$( echo $OUTPUT | sed -e 's/.*node_name_start<\(.*\)>node_name_stop.*/\1/')
    printf "\nnode_name = %s\n" $NODE_NAME

    OUTPUT=$(csmanage ca enrollment_password $DOMAIN_NAME $NODE_NAME --dir=$DIR 2>&1)
    ENROLLMENT_PASSWORD=$( echo $OUTPUT | sed -e 's/.*enrollment_password_start<\(.*\)>enrollment_password_stop.*/\1/')
    printf "\nenrollment password = %s\n" $ENROLLMENT_PASSWORD

    OUTPUT=$(csmanage runtime encrypt_csr $NODE_NAME $ENROLLMENT_PASSWORD --dir=$DIR 2>&1)
    ENCR_CSR_PATH=$( echo $OUTPUT | sed -e 's/.*encr_csr_path_start<\(.*\)>encr_csr_path_stop.*/\1/')
    printf "\nencrypted csr path = %s\n" $ENCR_CSR_PATH

    OUTPUT=$(csmanage ca signCSR $DOMAIN_NAME $ENCR_CSR_PATH --dir=$DIR 2>&1)
    SIGNED_CERT_PATH=$( echo $OUTPUT | sed -e 's/.*signed_cert_path_start<\(.*\)>signed_cert_path_stop.*/\1/')
    printf "\nsigned cert path = %s\n" $SIGNED_CERT_PATH

    OUTPUT=$(csmanage runtime import $NODE_NAME $SIGNED_CERT_PATH --dir=$DIR 2>&1)
    CERT_PATH=$( echo $OUTPUT | sed -e 's/.*cert_path_start<\(.*\)>cert_path_stop.*/\1/')
    printf "\ncert path = %s\n" $CERT_PATH

    printf "\n-------------\n"
done





