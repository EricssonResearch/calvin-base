from flask import Flask, request, abort

app = Flask(__name__)


@app.route('/')
def welcome():
    return "Basic webserver, returns data received through /add_message"


@app.route('/add_message', methods=['POST'])
def add_message():
    if request.method == 'POST':
        if request.data:
            print "received:", request.data
            return request.data
        else:
            print "No data received"
            abort(204)
    else:
        print "Method not supported!"
        abort(405)

if __name__ == "__main__":
    app.run(host="localhost", port=int("8087"))
