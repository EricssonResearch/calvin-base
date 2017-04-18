FROM alpine:3.2
RUN apk update && apk add gcc git python python-dev musl-dev
RUN wget https://bootstrap.pypa.io/ez_setup.py -O - | python
RUN easy_install pip
RUN git clone -b develop https://github.com/EricssonResearch/calvin-base calvin-base
RUN cd calvin-base && pip install -e .
RUN apk del git gcc python-dev musl-dev && rm -rf /var/cache/apk/*
ENTRYPOINT ["/bin/sh"]
