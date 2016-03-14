# Calvin and docker

Assuming you have a working installation of docker, either build an image using the
supplied docker files, or fetch them from dockerhub.

Building an image is straightforward. Here is how we built the images available on
dockerhub:

    $ docker build -t erctcalvin/calvin -f Dockerfile .

and

    $ docker build -t erctcalvin/calvin-rpi -f Dockerfile.RPi .
	
for the standard and the raspberry pi images, respectively. They can be pulled from dockerhub using

    $ docker pull erctcalvin/calvin

or

    $ docker pull erctcalvin/calvin-rpi
	
if you do not want to build them yourself.


Once they are available, the following should list the available actor namespaces:

    $ ./dcsdocs.sh
    Calvin: Merging cloud and IoT
    Modules: exception, io, json, media, misc, net, std, text, web

To start a runtime, use the following:

    $ ./dcsruntime.sh -i erctcalvin/calvin -e <ip> -p -n <name>

where `<ip>` is the ip of your computer (or your virtual machine if you are running e.g. docker machine.) When connecting several runtimes, this is necessary for them to find eachother. The `-p` sets this as the one in charge of the runtime registry - i.e. the place where other runtimes look up addresses and attributes.
	
To start more runtimes, use the following:

    $ ./dcsruntime.sh -i erctcalvin/calvin -e <ip> -m calvinip://<ip of previous> -n <name>
	
For example, the following will start 4 runtimes in separate containers, all using the first one are registry:

    $ ./dcsruntime.sh -i erctcalvin/calvin -e 192.168.0.120 -p -n registry
	$ ./dcsruntime.sh -i erctcalvin/calvin -e 192.168.0.120 -m calvinip://192.168.0.120 -n runtime-1
	$ ./dcsruntime.sh -i erctcalvin/calvin -e 192.168.0.120 -m calvinip://192.168.0.120 -n runtime-2
	$ ./dcsruntime.sh -i erctcalvin/calvin -e 192.168.0.120 -m calvinip://192.168.0.120 -n runtime-3

Start the web interface:

    $ ./dcsweb.sh 8000
	
and point your browser to `http://localhost:8000`. Enter the control uri of the registry runtime when asked - the default is port 5001 (`http://192.168.0.120:5001` in this example.)

The list should include all 4 runtimes with the specified names.