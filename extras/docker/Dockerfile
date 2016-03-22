FROM alpine:3.2
MAINTAINER ola.angelsmark@ericsson.com
RUN apk --update add python py-pip openssl ca-certificates && pip install -U setuptools
RUN apk --update add --virtual build-dependencies build-base git gcc python-dev musl-dev wget libffi-dev openssl-dev
RUN pip install --upgrade pip
# RUN git clone https://github.com/EricssonResearch/calvin-base calvin-base
RUN git clone -b develop https://github.com/EricssonResearch/calvin-base calvin-base
COPY docker-runtime.sh /calvin-base/
WORKDIR /calvin-base
RUN pip install --upgrade -r requirements.txt -r test-requirements.txt -e .
RUN apk del build-dependencies && rm -rf /var/cache/apk/*
WORKDIR /calvin-base
EXPOSE 5000 5001
