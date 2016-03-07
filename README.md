# Calvin

## What is this?

Calvin is an application environment that lets things talk to things. It comprises of both a development framework for application developers, and a runtime environment that handles the running application. Calvin is based on the fundamental idea that application development should be simple and fun. There should be no unnecessary impediments between an idea and its implementation, and an app developer should not have to worry about communication protocols or hardware specifics (but will not stop you from doing it if you want to.)

There are a few [Ericsson Research blog](http://www.ericsson.com/research-blog/) posts that gives a layman introduction to some aspects of Calvin:

[Open Source release of IoT app environment Calvin](http://www.ericsson.com/research-blog/cloud/open-source-calvin/)  
[A closer look at Calvin](http://www.ericsson.com/research-blog/cloud/closer-look-calvin/)  
[Calvin means business](http://www.ericsson.com/research-blog/cloud/calvin-means-business/)  

If you could not attend the [Mobile World Congress 2016](https://www.mobileworldcongress.com) in person there is at least a teaser of what our team showed there: [Calvin smart IoT development]()

When you have gone through the material above and want to try it yourself, read the quick start section below or go to the [wiki](https://github.com/EricssonResearch/calvin-base/wiki) for more detailed information.

## Contact
This is a community project that was started by a team in Ericsson Research. If you have any suggestions, questions, or just want to say hello, you can send an e-mail to <calvinteam@ericsson.com>.

## New in this version

### New runtime capabilities

The runtime now has interfaces for reading temperature, humidity, pressure, as well as displays with limited functionality (typically LCD with just a few rows of text.) Sample implementations of the interfaces are also included, with actors and examples showing their use.

The GPIO interface has been extended with support for pule-width modulation together with an example application for controlling a micro servo. 

### New actors

The actorstore has been extended with actors for handling UDP and HTTP traffic, which makes it easier to use other services and frameworks in Calvin (and vice versa.)

### Application Deployment

It is now possible to deploy an application where some actors have unresolved requirements, or even lacking implementation on the runtime handlingdeployment. These actors cannot execute, but are instantiated as 'shadows' that can be migrated to suitable runtimes as and when they become available.

### CSWeb and Control API

The REST API has been updated to use HTTP status codes consistently, as well as some new functions. It is now possible to retrieve documentation on all actors a runtime is aware of using the API.

CSWeb has been updated with application migration as per application deployment specifications. The vizualisation is now more in line with the tool chain (csviz) to avoid confusion.

### Under the hood

A fair number of patches to increase stability and robustness.

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

### HTTPS

In order to use https with the HTTP-actors, it is necessary to include the pyOpenSSL requirement. There have been reports of problems installing this dependency on some platforms: See the corresponding [installation instructions](https://github.com/pyca/pyopenssl/blob/master/INSTALL.rst). 

For this reason, the cryptography requirements are not included by default, but kept separately in the file `crypto-requirements.txt`.
