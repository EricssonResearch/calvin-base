# Calvin and docker #

Assuming you have a working installation of docker, either build an image using the
supplied docker files, or fetch them from dockerhub.

## Building a docker image ##

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

Once an image is available, the following should list the available actor namespaces:

    $ ./dcsdocs.sh
    Calvin: Merging cloud and IoT
    Modules: exception, io, json, media, misc, net, std, text, web

## Interactive use ##

In order to use calvin interactively in the image, start it as

    $ docker run -ti erctcalvin/calvin:master
	
and you will get a prompt, with the current path being the root of the Calvin installation. To run an example, try

    $ cd calvin/examples/sample-scripts
	$ csruntime --host localhost test1.calvin

Note that in a distributed Calvin-system, the runtimes need to know their externally visible IP. 

## Starting Calvin ##

When running Calvin distributed, there are two options for the registry, which is how Calvin handles discovery and information sharing between runtimes. Either have a designated Calvin runtime handling the registry for the system, or have it distributed in a DHT (distributed hash table). It is also possible to have a mixture of these in the same system, but for simplicity we only cover the clean cut cases.

### Designated registry

The registry runtime needs to be started first, before any of the others. The following command starts a runtime, names it "registry" and sets it to not use an external registry - i.e. it handles its own registry. Of course, it also needs an externally visible ip address for the other runtimes to use when communicating with it, and a port to use for the runtime to runtime communication. It is also prudent to expose a port for the control API using the `-c` option. More on that later.

    ./dcsruntime.sh -e <ip> -l -n registry -p <port> -c <another port>

We recommend `5000` and `5001`, respectively. There is an optional argument `-i` which sets which image to use. The default is `erctcalvin/calvin:master`
	
To start more runtimes, use the following:

    $ ./dcsruntime.sh -e <ip> -r <previous pi>:<previous port> -n <name>
	
The naming is optional, and can be omitted (in which case the runtime will get the name of the docker container it is running in.) The `-r` option tells the runtime that the registry is handled by the runtime located at `<ip>:<port>`. For example, the following will start 4 runtimes in separate containers, using the address `192.168.99.100`, with the first one as registry:

    $ ./dcsruntime.sh -e 192.168.99.100 -l -n registry -p 5000 -c 5001
	$ ./dcsruntime.sh -e 192.168.99.100 -r 192.168.99.100:5000 -n runtime-1
	$ ./dcsruntime.sh -e 192.168.99.100 -r 192.168.99.100:5000 -n runtime-2
	$ ./dcsruntime.sh -e 192.168.99.100 -r 192.168.99.100:5000 -n runtime-3


Start the web interface:

    $ ./dcsweb.sh 8000
	
and point your browser at `http://localhost:8000` (if you are using e.g. dockermachine, then `localhost` will not work - in that case it should be the ip of the VM hosting the containers). Enter the control uri of the registry runtime when asked - `http://192.168.99.100:5001` in this example.

The list should include all 4 runtimes with the specified names.

