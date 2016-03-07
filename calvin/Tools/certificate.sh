#!/bin/bash

[ ! -z "$TESTSCRIPT_DEBUG" ] && set -x
#[ -z "$CALVIN_CONFIG_PATH" ] && echo "Run calvin conf first!" && exit 1
OPENSSL_CONF=./openssl.conf

HELP=$(cat <<EOF
\nUsage: $0 <-r --runtime | -d --domain | -s --sign runtime.pem> [ --help]\n
\t-r, --runtime\t\tCreate new runtime certificate.\n
\t-d, --domain\t\tCreate a new domain certificate authority.\n
\t-s, --sign\t\tSign a runtime certificate.\n
\t-h, --help\t\tShow this help\n
EOF
)
while [[ $# > 0 ]]
do
key="$1"
case $key in
    -r|--runtime)
    NEW_RUNTIME=true
    shift
    ;;
    -s|--sign)
    SIGN_REQ=$2
    shift
    ;;
    -d|--domain)
    NEW_DOMAIN=true
    shift
    ;;
    -h|--help)
    echo -e $HELP
    ;;
    *)
    echo "Unknown option."
    ;;
esac
shift
done

umask 0077
#TODO: Parse the paths from the openssl.conf
dir=./demoCA      # Where everything is kept
certs=$dir/certs        # Where the issued certs are kept
crl_dir=$dir/crl      # Where the issued crl are kept
database=$dir/index.txt    # database index file.
new_certs_dir=$dir/newcerts     # default place for new certs.
private_dir=$dir/private

certificate=$dir/cacert.pem   # The CA certificate
serial=$dir/serial       # The current serial number
crl=$dir/crl.pem      # The current CRL
private_key=$private_dir/cakey.pem # The private key
RANDFILE=$dir/private/.rand    # private random number file

if [ $NEW_RUNTIME ]; then
    echo "Generating Calvin certificate for a new runtime."
    mkdir -p $new_certs_dir
    openssl req -config $OPENSSL_CONF -new -newkey rsa:2048 -nodes -out $new_certs_dir/runtime.csr -keyout $private_dir/runtime.key
fi

if [ $NEW_DOMAIN ]; then
    echo "Creating a certificate authority for a new domain."
    mkdir -p -m 700 $private_dir
    mkdir -p -m 700 $crl_dir
    chmod 700 $private_dir #Because chmod -m is not recursive
    echo 1000 > $dir/serial
    touch $dir/index.txt
    openssl rand -out $private_dir/ca_password 20
    openssl req -new -x509 -config $OPENSSL_CONF -keyout $private_key -out $certificate -passout file:$private_dir/ca_password
fi

if [ ! -z "$SIGN_REQ" ]; then
    echo "Adding new runtime certificate to domain."
    mkdir -p $certs
    openssl ca -in $new_certs_dir/$SIGN_REQ -config $OPENSSL_CONF -out $certs/runtime.pem -passin file:$private_dir/ca_password
fi

#view cert
#openssl x509 -in certificate.crt -text -noout
