#!/usr/bin/env python

from storage_clients import LocalRegistry, index_strings
from flask import Flask, jsonify, request
from flask import abort

app = Flask(__name__)

reg = LocalRegistry()

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
        return jsonify({"result":value})
    except:
        abort(404)

#
# Indexed key/value
#
@app.route('/index/<path:key>', methods=['GET', 'POST', 'DELETE'])
def index(key):
    if request.method in ['POST', 'DELETE']:
        data = request.get_json()
        if data is None or 'value' not in data:
            abort(400)
        root_prefix_level = data.get('root_prefix_level', None)
        if root_prefix_level is not None:
            root_prefix_level = int(root_prefix_level)
        indexes = index_strings(key, root_prefix_level)
        op = reg.remove_index if request.method == 'DELETE' else reg.add_index
        try:
            op(indexes[0], indexes[1:], data['value'])
        except Exception as e:
            print "Exception", e
            abort(400)
        return ''

    # GET
    root_prefix_level = request.args.get('root_prefix_level', None)
    if root_prefix_level is not None:
        root_prefix_level = int(root_prefix_level)
    indexes = index_strings(key, root_prefix_level)
    value = list(reg.get_index(indexes[0], indexes[1:]))
    return jsonify({"result":value})


if __name__ == '__main__':
    app.run(debug=True)