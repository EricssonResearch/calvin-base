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
    
@app.route('/storage/<path:prefix_key>', methods=['GET', 'POST'])
def storage(prefix_key):
    if request.method == 'POST':
        data = request.get_json()
        if data is None:
            abort(500)
        try:
            reg.set(prefix_key, data['value'])    
            return ''
        except:
            abort(500)
    # GET    
    try:
        value = reg.get(prefix_key)
        return jsonify({"result":value})
    except:
        abort(404)
    
@app.route('/index/<path:key>', methods=['GET', 'POST', 'DELETE'])
def index(key):
    if request.method in ['POST', 'DELETE']:
        data = request.get_json()
        if data is None:
            abort(500)
        data.get('root_prefix_level', None)
        indexes = index_strings(key, root_prefix_level)
        if request.method == 'DELETE':
            reg.remove_index(indexes, data[value])
        else:
            reg.add_index(indexes, data[value])
        return ''    
    # GET
    root_prefix_level = request.args.get('root_prefix_level', None)
    if root_prefix_level is not None:
        root_prefix_level = int(root_prefix_level)
    indexes = index_strings(key, root_prefix_level)
    value = list(reg.get_index(indexes))
    return jsonify({"result":value})


if __name__ == '__main__':
    app.run(debug=True)