FROM debian:jessie
MAINTAINER ola.angelsmark@ericsson.com
ARG branch=master
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gcc g++ python2.7 python-dev libffi-dev libssl-dev python-smbus wget ca-certificates git \
       python-pygame python-opencv\
    && rm -rf /var/lib/apt/lists/* \
    && wget https://bootstrap.pypa.io/get-pip.py -O - | python \
    && pip install requests \
    && git clone -b $branch https://github.com/EricssonResearch/calvin-base calvin-base \
    && cd /calvin-base \
    && pip install --upgrade -r requirements.txt -r test-requirements.txt -e .
WORKDIR /calvin-base

EXPOSE 5000 5001
