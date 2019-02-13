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

from flask import Flask, jsonify, request, abort

from calvin.runtime.north.plugins.storage.storage_clients import LocalRegistry


app = Flask(__name__)

reg = LocalRegistry(None)

# API for these methods
# - set(self, key, value) - PUT
# - get(self, key) - GET
# ? get_concat(self, key) - GET
# ? append(self, key, value) - POST
# ? remove(self, key, value) - POST
# ? delete(self, key) - DELETE
# - add_index(self, indexes, value) - POST
# - remove_index(self, indexes, value) - POST
# - get_index
# - dump - GET

@app.route('/dumpstorage', methods=['GET'])
def dumpstorage():
    data = reg.dump()
    return jsonify(data)
#
# Plain key/value => /storage/
#
@app.route('/storage/<path:key>', methods=['GET', 'POST', 'DELETE'])
def storage(key):
    if request.method == 'DELETE':
        reg.delete(key)
        return ''

    if request.method == 'POST':
        data = request.get_json()
        if data is None or 'value' not in data:
            abort(400)
        reg.set(key, data['value'])
        return ''

    # GET
    try:
        value = reg.get(key)
        return jsonify(value)
    except:
        abort(404)

#
# Don't expose, the keys we generate are not suitable for HTTP encoding 
#
# @app.route('/storage_sets/<path:key>', methods=['GET', 'POST', 'DELETE'])
# def storage_sets(key):
#     import urllib
#     key = urllib.unquote(key)
#     if request.method == 'DELETE':
#         reg.remove(key)
#         return ''
#
#     if request.method == 'POST':
#         data = request.get_json()
#         if data is None or 'value' not in data:
#             abort(400)
#         reg.append(key, data['value'])
#         return ''
#
#     # GET
#     try:
#         value = reg.get_concat(key)
#         return jsonify({"result":value})
#     except:
#         abort(404)

#
# API better suited for registry backend optimization
#
@app.route('/add_index/', methods=['POST'])
def add_index():
    data = request.get_json()
    valid_request = data and 'indexes' in data and 'value' in data
    if not valid_request:
        abort(400)
    try:
        reg.add_index(data['indexes'], data['value'])
    except Exception as e:
        print "Exception", e
        abort(400)
    return ''

@app.route('/remove_index/', methods=['POST'])
def remove_index():
    data = request.get_json()
    valid_request = data and 'indexes' in data and 'value' in data
    if not valid_request:
        abort(400)
    try:
        reg.remove_index(data['indexes'], data['value'])
    except Exception as e:
        print "Exception", e
        abort(400)
    return ''

@app.route('/get_index/', methods=['POST'])
def get_index():
    data = request.get_json()
    valid_request = data and 'indexes' in data
    if not valid_request:
        abort(400)
    try:
        reg.get_index(data['indexes'])
    except Exception as e:
        print "Exception", e
        abort(400)
    value = list(reg.get_index(data['indexes']))
    return jsonify(value)

# #
# # Indexed key/value
# #
# @app.route('/index/<path:key>', methods=['GET', 'POST', 'DELETE'])
# def index(key):
#     if request.method in ['POST', 'DELETE']:
#         data = request.get_json()
#         if data is None or 'value' not in data:
#             abort(400)
#         root_prefix_level = data.get('root_prefix_level', None)
#         if root_prefix_level is not None:
#             root_prefix_level = int(root_prefix_level)
#         indexes = index_strings(key, root_prefix_level)
#         op = reg.remove_index if request.method == 'DELETE' else reg.add_index
#         try:
#             op(indexes[0], indexes[1:], data['value'])
#         except Exception as e:
#             print "Exception", e
#             abort(400)
#         return ''
#
#     # GET
#     root_prefix_level = request.args.get('root_prefix_level', None)
#     if root_prefix_level is not None:
#         root_prefix_level = int(root_prefix_level)
#     indexes = index_strings(key, root_prefix_level)
#     value = list(reg.get_index(indexes[0], indexes[1:]))
#     return jsonify({"result":value})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', dest='host', default="localhost", type=str, help='host address')
    parser.add_argument('--port', dest='port', default=4998, type=int, help='host port')
    parser.add_argument('--debug', action='store_true', default=False, help='run in debug mode')
    
    args = parser.parse_args()
    
    app.run(host=args.host, port=args.port, debug=args.debug)
    

if __name__ == '__main__':
    main()
    
