# Calvin

## What is this?

Calvin is an application environment that lets things talk to things. It comprises of both a development framework for application developers, and a runtime environment that handles the running application. Calvin is based on the fundamental idea that application development should be simple and fun. There should be no unnecessary impediments between an idea and its implementation, and an app developer should not have to worry about communication protocols or hardware specifics (but will not stop you from doing it if you want to.)

There are a few [Ericsson Research blog](http://www.ericsson.com/research-blog/) posts that gives a layman introduction to some aspects of Calvin:

[Open Source release of IoT app environment Calvin](http://www.ericsson.com/research-blog/cloud/open-source-calvin/)  
[A closer look at Calvin](http://www.ericsson.com/research-blog/cloud/closer-look-calvin/)  
[Calvin means business](http://www.ericsson.com/research-blog/cloud/calvin-means-business/)  

If you could not attend the [Mobile World Congress 2016](https://www.mobileworldcongress.com) in person there is at least a teaser of what our team showed there: [Calvin smart IoT development](http://www.ericsson.com/research-blog/internet-of-things/calvin/)

An early position paper on Calvin, [Calvin - Merging Cloud and IoT](http://www.sciencedirect.com/science/article/pii/S1877050915008595) describes many of the underlying ideas and overall goals with this project. There are also a growing number of Calvin related master's theses available:

* [Consistent Authentication in Distributed Networks](https://lup.lub.lu.se/student-papers/search/publication/8871006)
* [Dynamic Fault Tolerance and Task Scheduling in Distributed Systems](https://lup.lub.lu.se/student-papers/search/publication/8876351)
* [Secure Domain Transition of Calvin Actors](https://lup.lub.lu.se/student-papers/search/publication/8881650)
* [Authorization Aspects of the Distributed Dataflow-oriented IoT Framework Calvin](https://lup.lub.lu.se/student-papers/search/publication/8879081)

## Getting Started

When you have gone through the material above and want to try it yourself, there is a quick start below, but you can also dive head first into [Installing Calvin](https://github.com/EricssonResearch/calvin-base/tree/master/extras/install/) or even [Calvin and Docker](https://github.com/EricssonResearch/calvin-base/tree/master/extras/docker/) if that is your preference. There should be enough information there to set up a small system of Calvin runtimes and deploy a simple distributed application.

The next stop after that would be to have a look at the available [examples](https://github.com/EricssonResearch/calvin-base/tree/master/calvin/examples), where we have a collection of example applications. If you have a Raspberry Pi available, it should be straightforward to get most of then up and running.

There is also an abundance of detailed information on the [wiki](https://github.com/EricssonResearch/calvin-base/wiki).

## Contact
This is a community project that was started by a team in Ericsson Research. If you have questions or problems, post an issue and we'll get back go you as soon as we can.

## New in this version

The focus of this release has been to rework some of the innards of Calvin in order to prepare for future extensions. Of course, it is inevitable that some new features sneak in, such as the new authentication framework (described in the [wiki](https://github.com/EricssonResearch/calvin-base/wiki/Security)), or just plain improvements, such as the new keyword `voidport` in CalvinScript - a shortcut to mark a port as unused in a script.

### Dockers ###

The instructions for using Calvin in Dockers have been reworked and expanded. The creation of images have been simplified. See [here](https://github.com/EricssonResearch/calvin-base/tree/master/extras/docker).

### Examples ###

Some documentation have been added to the examples, and the necessary requirements are included as an option in the installation script available [here](https://github.com/EricssonResearch/calvin-base/tree/master/extras/install).

### Security ###

This version introduces a new flexible authentication framework for establishing the authenticity of the user that deploys and application, within a domain, the authentication procedure results in a set of user attributes associated with the instances of actors, the attributes are used as input for the authorization procedure. Similarly, a new flexible attribute based authorization framework  is introduced. The framework is similar to XACML but designed to be more compact and efficient, it uses JSON and JSON Web Tokens for rules and transport. The certificate and key management has been substantially updated. _Note_: As for previous releases, all security features are disabled by default.

### Under the hood ###

A lot of work has gone into restructuring and refactoring in preparation of the features planned for later this year. The parser and compiler has received a much needed overhaul in order to simplify extensions to CalvinScript, and the implementation of actor ports have been improved to allow for a more dynamic and configurable handling of tokens. 

## Quick start

### Download

The latest version of Calvin can be found on [github](https://github.com/EricssonResearch/calvin-base).

### Setup

(For more information about installation options, see [the wiki](https://github.com/EricssonResearch/calvin-base/wiki/Installation)) or the [debian/raspbian/ubuntu instructions](https://github.com/EricssonResearch/calvin-base/tree/master/extras/install)

When all pre-requisites are installed (see previous links), Calvin can be installed using the accompanying `setup.py`

    $ python setup.py install

Alternatively, install using `pip`

    $ pip install -e .

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

Note that csruntime will return until it exits; either have it run in the background (usually by adding `&` to the end of the command), or open a new terminal to continue.

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
    source : std.Trigger(tick=1, data="Hello, world")
    output : io.Print()

    source.date > output.token

Save the file, and deploy and run the program (assuming you have a runtime running on localhost):

    $ cscontrol http://localhost:5001 myfirst.calvin

The application should produce "Hello, world" once every second.

## Open issues

Several
