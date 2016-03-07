#!/bin/bash
CALVIN_PATH = $1
SEARCH_ACTOR_FOLDER="$CALVIN_PATH/calvin/actorstore/systemactors"
SEARCH_APPLICATION_FOLDER="$CALVIN_PATH/calvin/scripts"

FILES=$(find $SEARCH_ACTOR_FOLDER -name "*.py")
FILES+=" "
FILES+=$(find $SEARCH_APPLICATION_FOLDER -name "*.calvin")

echo $FILES > signed_files.log

for file in $FILES; do
    openssl dgst -sha256 -sign "$CALVIN_PATH/keys/app_signer/privkey.pem" -out "$file.sign" "$file"
    cp "$CALVIN_PATH/keys/app_signer/cert.pem" "$file.cert"
done
