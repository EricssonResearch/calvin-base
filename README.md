# Calvin

## What is this?

Calvin is an application environment that lets things talk to things. It
comprises of both a development framework for application developers, and a
runtime environment that handles the running application. Calvin is based on
the fundamental idea that application development should be simple and fun.
There should be no unnecessary impediments between an idea and its
implementation, and an app developer should not have to worry about
communication protocols or hardware specifics (but will not stop you from
doing it if you want to.)


See the [wiki](https://github.com/EricssonResearch/calvin-base/wiki) for more
detailed information, or continue reading.

## Quick start

### Download

The latest version of Calvin can be found on [github](https://github.com/EricssonResearch/calvin-base).

### Setup

To install Calvin, use the accompanying `setup.py`

    $ python setup.py install

Alternatively, install the requirements using `pip`

    $ pip install -r requirements.txt

To verify a working installation, try

    $ csdeploy calvin/scripts/test1.calvin

This should produced an output similar to this:

    [Time INFO] StandardOut<[Actor UUID]>: 1
    [Time INFO] StandardOut<[Actor UUID]>: 2
    [Time INFO] StandardOut<[Actor UUID]>: 3
    [Time INFO] StandardOut<[Actor UUID]>: 4
    [Time INFO] StandardOut<[Actor UUID]>: 5
    [Time INFO] StandardOut<[Actor UUID]>: 6
    [Time INFO] StandardOut<[Actor UUID]>: 7
    [Time INFO] StandardOut<[Actor UUID]>: 8
    [Time INFO] StandardOut<[Actor UUID]>: 9
    [ ... ]

The exact output may vary; the number of lines and the UUID of the actor will most likely be different between runs.

It is also possible to start a runtime without deploying an application to it,

    $ csdeploy --start-only --host <address> --controlport 5001 --port 5000 --keep-alive

Applications can then be deployed remotely using

    $ csdeploy --deploy-only --host <address> --controlport 5001 --port 5000 <script-file>
    Deployed application <app id>

and stopped with 

    $ csdeploy --host <address> --controlport 5001 --port 5000 --kill <app id>

Alternatively, a nicer way of doing it is using the web interface, described next.

### Visualization

Start a runtime

    $ csdeploy --start-only --host localhost --controlport 5001 --port 5000 --keep-alive

Start web server

    $ csweb

In a web browser go to `http://localhost:8000`, enter the control uri of the runtime you wish to inspect
(in this case `http://localhost:5001`)

To deploy an application to the runtime, go to the `Deploy` tab, load a script and deploy it. 
(_Note_: There have been issues with some browsers on this page. Only Google Chrome seems to work
consistently.)

After deployment, the `Actor` tab lists the actors currently executing on this runtime, and the
`Applications` tab shows all applications deployed from the current runtime. By selecting one of the
application ids, it is possible to get a visual representation of the application in the form of a graph.
It is also possible to turn on tracing in order to see what goes on w.r.t actions in each actor. Running
applications can also be stopped here.

### Migration

Once you have two runtimes up and running, executing the following will allow you to migrate actors between them;

    $ csdeploy --host <address> --port <port> --peer calvinip://<other node address>:<other node port>

Deploy an application to one of them (from the command line or the web interface) and visit the `Actors` tab
in the web interface. It should now be possible to select an actor and migrate it to the other node.

### Testing

If necessary, install the extra packages needed for testing

    $ pip install -r test-requirements.txt

Run the essential test suite

    $ py.test -m essential

Run the quick test suite

    $ py.test -m "not slow"

Some tests are skipped (marked `s`), some are expected to fail (marked `x` or `X`). The important
thing is that the line at the bottom is green.

## My first Calvinscript

CalvinScript is a scripting language designed to take the ugliness out of writing calvin programs.
Using your favorite editor, create a file named `myfirst.calvin` containing the following:

    # myfirst.calvin
    source : std.Counter()
    output : io.StandardOut()

    source.integer > output.token

Save the file, and deploy and run the program

    $ csdeploy myfirst.calvin

The output should be identical to the earlier example.

## Open issues

Several







