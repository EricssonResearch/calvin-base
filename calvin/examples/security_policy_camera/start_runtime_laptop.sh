#!/bin/sh

CALVIN_GLOBAL_STORAGE_TYPE=\"local\" csruntime --host 192.168.1.2 --port 5000 --controlport 5001 --attr-file runtime_attributes/laptop.json
