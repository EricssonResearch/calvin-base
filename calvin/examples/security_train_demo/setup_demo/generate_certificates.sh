#!/bin/bash

SECURITY_DIR=../security
RUNTIME_ATTRIBUTES_DIR=../runtime_attributes
RUNTIMES_DIR=$SECURITY_DIR/runtimes
DOMAIN=SJ

rm -rf $SECURITY_DIR/$DOMAIN
rm -rf $RUNTIMES_DIR
#Create CA
csmanage ca create --dir $SECURITY_DIR/ $DOMAIN
#Create runtime ELX
csmanage runtime create --dir $SECURITY_DIR $DOMAIN --attr-file ../runtime_attributes/ELX.json
#Export CA cert into runtime truststore (common for all runtimes)
csmanage ca export --dir $SECURITY_DIR $DOMAIN $RUNTIMES_DIR/truststore_for_transport/
#Create runtime Servo
csmanage runtime create --dir $SECURITY_DIR $DOMAIN --attr-file ../runtime_attributes/Servo.json
#Create runtime Lund_RFID
csmanage runtime create --dir $SECURITY_DIR $DOMAIN --attr-file ../runtime_attributes/Lund_RFID.json
#Create runtime Lund_Camera_Sensehat
csmanage runtime create --dir $SECURITY_DIR $DOMAIN --attr-file ../runtime_attributes/Lund_Camera_Sensehat.json 
#Create runtime Lund_InfoBoard
csmanage runtime create --dir $SECURITY_DIR $DOMAIN --attr-file ../runtime_attributes/Lund_InfoBoard.json 
#Create runtime Sthlm_RFID
csmanage runtime create --dir $SECURITY_DIR $DOMAIN --attr-file ../runtime_attributes/Sthlm_RFID.json
#Create runtime Sthlm_Camera_Sensehat
csmanage runtime create --dir $SECURITY_DIR $DOMAIN --attr-file ../runtime_attributes/Sthlm_Camera_Sensehat.json 
#Create runtime Sthlm_InfoBoard
csmanage runtime create --dir $SECURITY_DIR $DOMAIN --attr-file ../runtime_attributes/Sthlm_InfoBoard.json 


csmanage ca signCSR --dir $SECURITY_DIR $DOMAIN $RUNTIMES_DIR/$DOMAIN++++ELX/$DOMAIN++++ELX.csr
csmanage ca signCSR --dir $SECURITY_DIR $DOMAIN $RUNTIMES_DIR/$DOMAIN++++Servo/$DOMAIN++++Servo.csr
csmanage ca signCSR --dir $SECURITY_DIR $DOMAIN $RUNTIMES_DIR/$DOMAIN++++Lund_Camera_Sensehat/$DOMAIN++++Lund_Camera_Sensehat.csr
csmanage ca signCSR --dir $SECURITY_DIR $DOMAIN $RUNTIMES_DIR/$DOMAIN++++Lund_RFID/$DOMAIN++++Lund_RFID.csr
csmanage ca signCSR --dir $SECURITY_DIR $DOMAIN $RUNTIMES_DIR/$DOMAIN++++Lund_InfoBoard/$DOMAIN++++Lund_InfoBoard.csr
csmanage ca signCSR --dir $SECURITY_DIR $DOMAIN $RUNTIMES_DIR/$DOMAIN++++Sthlm_Camera_Sensehat/$DOMAIN++++Sthlm_Camera_Sensehat.csr
csmanage ca signCSR --dir $SECURITY_DIR $DOMAIN $RUNTIMES_DIR/$DOMAIN++++Sthlm_RFID/$DOMAIN++++Sthlm_RFID.csr
csmanage ca signCSR --dir $SECURITY_DIR $DOMAIN $RUNTIMES_DIR/$DOMAIN++++Sthlm_InfoBoard/$DOMAIN++++Sthlm_InfoBoard.csr

NEWCERTS_DIR=$SECURITY_DIR/$DOMAIN/newcerts/
CERTS="$(find $NEWCERTS_DIR -type f -name '*.pem' ! -name '10*.pem' ! -name 'cacert.pem')"
echo $CERTS
for f in $CERTS
do
	echo "Importing $f"
	csmanage runtime import --dir $SECURITY_DIR $f
	cp $f $RUNTIMES_DIR/$DOMAIN++++ELX/others/
	cp $f $RUNTIMES_DIR/$DOMAIN++++Servo/others/
	cp $f $RUNTIMES_DIR/$DOMAIN++++Lund_RFID/others/
	cp $f $RUNTIMES_DIR/$DOMAIN++++Lund_InfoBoard/others/
	cp $f $RUNTIMES_DIR/$DOMAIN++++Lund_Camera_Sensehat/others/
	cp $f $RUNTIMES_DIR/$DOMAIN++++Sthlm_RFID/others/
	cp $f $RUNTIMES_DIR/$DOMAIN++++Sthlm_InfoBoard/others/
	cp $f $RUNTIMES_DIR/$DOMAIN++++Sthlm_Camera_Sensehat/others/
done

