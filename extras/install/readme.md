# Brief Introduction to Calvin & CalvinScript

## Installation

### Debian-based systems, installation script

The following has been tested on Raspbian Jessie (2016-05-27) and Ubuntu 16.04.

The easiest way of installing Calvin on a Debian-based system (e.g. Debian, Ubuntu, Raspbian, etc) is to use the install script `extras/install/ubuntu-install.sh`. Executing it without parameters (it requires `sudo` powers) will install Calvin and all dependencies for a vanilla installation.

    $ cd extras/install
    $ ./ubuntu-install.sh

Note that this will install Calvin (and dependencies) system-wide. The script accepts a selection of arguments:

    Usage: ./ubuntu-install.sh [-b master/develop] -sweu                                    
            -b      select branch of calvin to install [master]                             
            -s      run calvin at startup [no]                                              
            -w      run web interface at startup [no]                                       
            -e      install raspberry pi example dependencies [no]                          
            -u      install non-raspberry pi example dependencies [no]                      
            -p      replace python-pip (may solve some installation issues) [no]            

#### Example

To have Calvin start on system startup, add the flag `-s` and to have the Calvin web tool available on startup, add `-w`, i.e.

    $ ./ubuntu-install.sh -s -w

This will ensure Calvin is up and running when the system boots, and that a webserver is running, presenting the calvin control GUI on port 8000 on the host. The `-b` flag lets you select which branch of Calvin to use &mdash; the `master` branch is usually more stable, but will often lack some of the more recent additions compared to `develop`. It's up to you which one you go with.

To install some useful dependencies in order to run the examples in `calvin/examples`, add `-u` and, if on a raspberry pi, add `-r`:

    $ ./ubuntu-install.sh -s -w -r -u -p

### Debian-based systems, manual installation

The following has been tested on Raspbian Jessie (2016-05-27) and Ubuntu 16.04.

    $ sudo apt-get update
	$ sudo apt-get install -y python python-dev build-essential git libssl-dev libffi-dev

As of this writing, the python-pip and python-requests packages in Debian Jessie are
out of sync. Remove the default and install a newer version - this is less than ideal.

    $ sudo apt-get remove -y python-pip
    $ curl https://bootstrap.pypa.io/get-pip.py -o - | sudo python

Get calvin

    $ git clone -b $branch https://www.github.com/EricssonResearch/calvin-base

and install its dependencies

    $ cd calvin-base
    $ sudo -H pip install -r requirements.txt -r test-requirements.txt

Finally, install it

	$ sudo pip install -e .

(Note the `.` at the end.) After this step, executing 

    $ py.test -m essential calvin

should not give any fatal errors.

### Unix-like systems

For non-debian based Linux, Mac OS X and other Unix-like systems, the installation of dependencies vary wildly. To fetch the latest release of the source, `git` is needed.

    $ git clone https://github.com/EricssonResearch/calvin-base

Calvin-base is mostly written in python2.7, so it needs to be installed as well, and to install python dependencies, `pip` is needed. Either install it using your standard packager, or from bootstrap:

    $ curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
	$ python get-pip.py

The installation of pip will likely require superuser priviledges (e.g. sudo/proot/etc).

As of Calvin 0.6, the external, non-python dependencies are

    libssl
    libffi

and needs to be installed before continuing. After that, the python dependencies are handled more or less automatically by

    $ cd calvin-base
    $ pip install -r requirements.txt -r test-requirements.txt
	$ pip install -e .

which should be executed in the top directory of the Calvin source tree. Again, it is likely that superuser priviledges are necessary.

Executing 

    $ py.test -m essential calvin

should not give any fatal errors.

### Other systems

Calvin has not been extensively tested on Windows, and it is unlikely to work out of the box. Unfortunately. Patches and instructions will probably be accepted posthaste.

## Running a first example

Assuming Calvin has been installed and works as expected, excute the following from the top directory of the calvin source tree.

    $ cd calvin/examples/sample-scripts
	$ csruntime --host localhost test1.calvin

After a lot of `INFO` messages listing some information of what Calvin has found in the system w.r.t capabilities, the following should appear (the application id and number of lines may differ slightly):

    Deployed application 922a2096-bfd9-48c8-a5a4-ee900a180ca4
	Hello, world
	Hello, world
	Hello, world

and then Calvin exits. When starting Calvin this way, with a script, there is a default timeout of 3 seconds before exiting. Normally, Calvin should not exit, but when toying around with small scripts, this may be the preferred way of doing it. The timeout can changed:

    $ csruntime --host localhost -w 10 test1.calvin 

will run for 10 seconds before exiting. Use `-w 0` to run forever. 

The `--host` argument is important. For sample scripts, such as this, which only spans a single runtime `localhost`  suffices, but when running a system with several runtimes, it is important that this argument is the IPv4 address of the host running Calvin. We will see examples of this later.

The script itself looks like this:

    /* Actors */
    src : std.Trigger(tick=1.0, data="Hello, world")
    snk : io.Print()
    /* Connections */
    src.data > snk.token

This is an example of _CalvinScript_ which is how an application is described in Calvin. There are two main parts to the script; First, the declaration of actors used in the application, and then a description of how they are connected. In this simple example, there are two actors, called `src` and `snk`. The first actor, `src` is of type `std.Trigger()` with the sole purpose of generating a tick to the system. To this purpose, it takes two parameters, `tick`, which is the interval, in seconds, with which to generate the data, and `data` which is what to output on each tick. The output is then sent on the `data` port of the actor.

The `snk` actor is of type `io.Print()`, has no parameters, and outputs whatever data it gets on its `token` port on standard out.

The documentation of these types can be easily found using the `csdocs` command:

    $ csdocs std.Trigger
    std.Trigger(tick, data): Pass on given _data_ every _tick_ seconds
    Outputs: data

    $ csdocs io.Print
    io.Print(): Print tokens to suitable device
    Inputs: token

All valid actors can be inspected using csdocs, and they should all have some form of documentation.
