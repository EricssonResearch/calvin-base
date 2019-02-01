#!flask/bin/python

import store
from flask import Flask, jsonify
from flask import abort

app = Flask(__name__)

actorstore = store.Store()

@app.route('/actors/', methods=['GET'])
@app.route('/actors/<path:actor_type>', methods=['GET'])
def get_tasks(actor_type=''):
    parts = [p for p in actor_type.split('/') if p.strip()]
    actor_type = ".".join(parts)
    print "parts", parts
    print "actor_type", actor_type
    res, src, properties = actorstore.get_info(actor_type)
    if res is store.Pathinfo.invalid:
        abort(404)
    return jsonify({'src': src, 'properties':properties})

if __name__ == '__main__':
    app.run(debug=True)