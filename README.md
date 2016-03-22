# Calvin

## What is this?

Calvin is an application environment that lets things talk to things. It comprises of both a development framework for application developers, and a runtime environment that handles the running application. Calvin is based on the fundamental idea that application development should be simple and fun. There should be no unnecessary impediments between an idea and its implementation, and an app developer should not have to worry about communication protocols or hardware specifics (but will not stop you from doing it if you want to.)

There are a few [Ericsson Research blog](http://www.ericsson.com/research-blog/) posts that gives a layman introduction to some aspects of Calvin:

[Open Source release of IoT app environment Calvin](http://www.ericsson.com/research-blog/cloud/open-source-calvin/)  
[A closer look at Calvin](http://www.ericsson.com/research-blog/cloud/closer-look-calvin/)  
[Calvin means business](http://www.ericsson.com/research-blog/cloud/calvin-means-business/)  

If you could not attend the [Mobile World Congress 2016](https://www.mobileworldcongress.com) in person there is at least a teaser of what our team showed there: [Calvin smart IoT development](http://www.ericsson.com/research-blog/internet-of-things/calvin/)

When you have gone through the material above and want to try it yourself, read the quick start section below or go to the [wiki](https://github.com/EricssonResearch/calvin-base/wiki) for more detailed information.

## Contact
This is a community project that was started by a team in Ericsson Research. If you have any suggestions, questions, or just want to say hello, you can send an e-mail to <calvinteam@ericsson.com>.

## New in this version

### Dockers ###

There are now a couple of examples of how to use Calvin with [Dockers](http://www.docker.io). It is still in an early phase, but if you are somewhat familiar with dockers, then a quick way of testing Calvin is to download an image and have a look. Instructions can be found in [here](https://github.com/EricssonResearch/calvin-base/tree/master/extras/docker). 

### Capabilities ###

There is now support for some new webservices, such as [tweeting](http://twitter.com), and checking the [forecast](http://www.openweathermap.com). There is also support for some new hardware.

### Examples ###

There are a selection of new examples demonstrating how to use some features of Calvin's, such as using runtime attributes to store hardware configuration, such as which GPIO-pins are in use on a Raspberry Pi, and credentials, such as an API-key. Check the examples folder for details.

### Security ###

This version introduces signing of actors and applications, as well as verification of signatures, policy controlled runtime authorization for actors, and an option for using a secure DHT implementation for the internal registry. None of this is currently active by default.

### Visuals and use ###

If an actor is hogging the scheduler for longer than 200 ms, a warning will be issued in the log. There is a new extended trace functionality with detailed metering of actors events. CSWeb has been given a new look and supports the extended trace logging. Deployment of applications can specify and update actor requirements to guide the deployment on runtimes.

### Under the hood ###

Location of configuration files can now be specified using a special CALVIN\_CONFIG\_PATH environmental variable. There have also been changes to the configuration of the internal registry - check this if you have issues with a previously working installation. 

In addition to this, new tests have been added, as well as some refactoring for pythonisity.


## Quick start

### Download

The latest version of Calvin can be found on [github](https://github.com/EricssonResearch/calvin-base).

### Setup

(For more information about installation options, see [the wiki](https://github.com/EricssonResearch/calvin-base/wiki/Installation))

To install Calvin, use the accompanying `setup.py`

    $ python setup.py install

Alternatively, install the requirements using `pip`

    $ pip install -r requirements.txt

To verify a working installation, try

    $ csruntime --host localhost calvin/examples/sample-scripts/test1.calvin

This should produced an output similar to this:

    1
    2
    3
    4
    5
    6
    7
    8
    9
    [ ... ]

The exact output may vary; the number of lines will most likely be different between runs. 

It is also possible to start a runtime without deploying an application to it,

    $ csruntime --host <address> --controlport <controlport> --port <port>

Applications can then be deployed remotely using

    $ cscontrol http://<address>:<controlport> deploy <script-file>
    Deployed application <app id>

and stopped with

    $ cscontrol http://<address>:<controlport> applications delete <app id>

Alternatively, a nicer way of doing it is using the web interface, described next.

### Visualization

Start a runtime

    $ csruntime --host localhost --controlport 5001 --port 5000

Start web server

    $ csweb

In a web browser go to `http://localhost:8000`, enter the control uri of the runtime you wish to inspect (in this case `http://localhost:5001`)

To deploy an application to the runtime, go to the `Deploy` tab, load a script and deploy it. (_Note_: There have been issues with some browsers on this page. Only Google Chrome seems to work consistently.)

After deployment, the `Actor` tab lists the actors currently executing on this runtime, and the `Applications` tab shows all applications deployed from the current runtime. By selecting one of the application ids, it is possible to get a visual representation of the application in the form of a graph. It is also possible to turn on tracing in order to see what goes on w.r.t actions in each actor. Running applications can also be stopped here. 

### Migration

Once you have to runtimes up and running, they can be joined together to form a network with

    $ cscontrol http://<first runtime address>:<controlport> nodes add calvinip://<other runtime address>:<port>

Deploy an application to one of them (from the command line or the web interface) and visit the `Actors` tab in the web interface. It should now be possible to select an actor and migrate it to the other node.

Alternatively, this can be done from the command line using the cscontrol utility:

    $ cscontrol http://<first runtime address>:<controlport> actor migrate <actor id> <other runtime id>

Where the necessary information (runtime id, actor id) can be gathered using the same utility. USe

    $ cscontrol --help

for more information. Note that the control uri is mandatory even for most of the help commands.

### Testing

If necessary, install the extra packages needed for testing

    $ pip install -r test-requirements.txt

Run the essential test suite

    $ py.test -m essential

Run the quick test suite

    $ py.test -m "not slow"

Some tests are skipped (marked `s`), some are expected to fail (marked `x` or `X`). The important thing is that the line at the bottom is green.

## My first Calvinscript

CalvinScript is a scripting language designed to take the ugliness out of writing calvin programs. Using your favorite editor, create a file named `myfirst.calvin` containing the following:

    # myfirst.calvin
    source : std.Counter()
    output : io.Print()

    source.integer > output.token

Save the file, and deploy and run the program (assuming you have a runtime running on localhost):

    $ cscontrol http://localhost:5001 myfirst.calvin

The output should be identical to the earlier example.


## Open issues

Several
