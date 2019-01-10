#!flask/bin/python

import newstore
from flask import Flask, jsonify
from flask import abort

app = Flask(__name__)

store = newstore.Store()

@app.route('/actors/<path:actor_type>', methods=['GET'])
def get_tasks(actor_type):
    actor_type = actor_type.replace('/', '.')
    res, src, properties = store.get(actor_type)
    if res is not newstore.Pathinfo.actor:
        abort(404)
    return jsonify({'src': src, 'properties':properties})

if __name__ == '__main__':
    app.run(debug=True)