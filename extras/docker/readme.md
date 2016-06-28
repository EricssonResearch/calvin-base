# Calvin and docker #

Assuming you have a working installation of docker, either build an image using the
supplied docker files, or fetch them from dockerhub.

## Building an image ##

Building an image is straightforward. Here is how we built the images available on
dockerhub:

    $ make master

for the image of the GitHub master branch, and 

    $ make develop

for the develop branch.

It is of course also possible to build them manually, e.g.

    $ docker build -t erctcalvin/calvin -f Dockerfile .

for the standard and the raspberry pi images, respectively. They can be pulled from dockerhub using

    $ docker pull erctcalvin/calvin:master

and

    $ docker pull erctcalvin/calvin:develop

for the master and develop images, respectively.

There is also a make target for when you have made changes (on the develop branch) and just want to
include them:

    $ make local

will build an image based on the develop image with the changes in the current repository. See the Makefile for details; among other things, it assumes the calvin-base repo is located in `../../`. If you want to use another namespace than the official erctcalvin, pass your preference to the Makefile, e.g.

    $ make NAMESPACE=mycalvin develop

will build the develop branch image, and name it `mycalvin/calvin:develop`.

Once they are available, the following should list the available actor namespaces:

    $ ./dcsdocs.sh
    Calvin: Merging cloud and IoT
    Modules: exception, io, json, media, misc, net, std, text, web

## Interactive use ##

In order to use calvin interactively in the image, start it as

    $ docker run -ti erctcalvin/calvin:master
	
and you will get a prompt, with the current path being the root of the Calvin installation. To run an example, try

    $ cd calvin/examples/sample-scripts
	$ csruntime --host localhost test1.calvin


## Starting Calvin ##

To start a runtime, use the following:

    $ ./dcsruntime.sh -e <ip> -p -n <name>

where `<ip>` is the ip of your computer (or your virtual machine if you are running e.g. docker machine.) When connecting several runtimes, this is necessary for them to find eachother. The `-p` sets this as the one in charge of the runtime registry - i.e. the place where other runtimes look up addresses and attributes. There is an optional argument `-i` which sets which image to use. The default is `erctcalvin/calvin:master`
	
To start more runtimes, use the following:

    $ ./dcsruntime.sh -e <ip> -m calvinip://<ip of previous> -n <name>
	
For example, the following will start 4 runtimes in separate containers, using the address 192.168.99.100, with the first one as registry:

    $ ./dcsruntime.sh -e 192.168.99.100 -p -n registry
	$ ./dcsruntime.sh -e 192.168.99.100 -m calvinip://192.168.99.100 -n runtime-1
	$ ./dcsruntime.sh -e 192.168.99.100 -m calvinip://192.168.99.100 -n runtime-2
	$ ./dcsruntime.sh -e 192.168.00.100 -m calvinip://192.168.99.100 -n runtime-3

Start the web interface:

    $ ./dcsweb.sh 8000
	
and point your browser to `http://localhost:8000` (if you are using e.g. dockermachine, then this should be the ip of the VM hosting the containers). Enter the control uri of the registry runtime when asked - the default is port 5001 (`http://192.168.99.100:5001` in this example.)

The list should include all 4 runtimes with the specified names.

