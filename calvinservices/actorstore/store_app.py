#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2015-2019 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.



import argparse
import logging

from flask import Flask, jsonify, abort

from . import store

app = Flask(__name__)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

actorstore = None

@app.route('/ping', methods=['GET'])
def ping():
    return "OK"


@app.route('/actors/', methods=['GET'])
@app.route('/actors/<path:actor_type>', methods=['GET'])
def get_tasks(actor_type=''):
    parts = [p for p in actor_type.split('/') if p.strip()]
    actor_type = ".".join(parts)
    print("parts", parts)
    print("actor_type", actor_type)
    res, src, properties = actorstore.get_info(actor_type)
    if res is store.Pathinfo.invalid:
        abort(404)
    return jsonify({'src': src, 'properties':properties})


def main():
    global actorstore
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', dest='host', default="localhost", type=str, help='host address')
    parser.add_argument('--port', dest='port', default=4999, type=int, help='host port')
    parser.add_argument('--debug', action='store_true', default=False, help='run in debug mode')
    parser.add_argument('--actorpaths', default=[], nargs='+', help='list of actor paths')

    args = parser.parse_args()

    actorstore = store.Store(args.actorpaths)

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
