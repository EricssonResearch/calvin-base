#!/bin/sh

cscontrol http://192.168.1.2:5001 deploy policy_demo.calvin --credentials '{"testdomain":{"user": "tomas", "password": "demo"}}' --reqs policy_demo.deployjson