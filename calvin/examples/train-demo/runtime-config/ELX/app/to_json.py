#!/usr/bin/env python
import json
import sys

def jsonify_file(f):
    content = None
    with open(f) as fp:
        content = fp.read()
    with open(f+".stringified", "w+") as fp:
        json.dump(content, fp)

def jsonify_files(files):
    for f in files:
        jsonify_file(f)

if __name__ == '__main__':
    assert len(sys.argv) > 1
    jsonify_files(sys.argv[1:])