FROM alpine:3.2
MAINTAINER ola.angelsmark@ericsson.com
ARG branch=master
RUN apk --update add python py-pip openssl ca-certificates \
      && apk --update add --virtual build-dependencies build-base git gcc python-dev libffi-dev openssl-dev \
      && pip install --upgrade pip \
      && git clone -b $branch https://github.com/EricssonResearch/calvin-base calvin-base \
      && cd /calvin-base \
      && pip install --upgrade -r requirements.txt -r test-requirements.txt -e . \
      && apk del build-dependencies && rm -rf /var/cache/apk/*
RUN apk --update add curl
WORKDIR /calvin-base/
EXPOSE 5000 5001

