__NOTE__: This is mostly obsolete. Rather than running the installation script, follow the recommended [Installation](https://www.github.com/EricssonResearch/calvin-base/wiki/Installation) description, and then install extra requirements as needed by the `calvinsys`-plugins used.

# Installation

The following has been tested on Raspbian Jessie (2016-05-27) and Ubuntu 16.04. It is mainly aimed at simplifying the installation of Calvin on systems that will not be used for much else, such as Raspberry Pi's or in virtual machines. It is not the recommended way of installing Calvin on your production server. See [the installation descriptions](https://www.github.com/EricssonResearch/calvin-base/wiki/Installation) for the recommended way of installing Calvin.

### Debian-based systems, installation script

The easiest way of installing Calvin on a Debian-based system (e.g. Debian, Ubuntu, Raspbian, etc) is to use the install script `extras/install/ubuntu-install.sh`. Executing it without parameters (it requires `sudo` powers) will install Calvin and all dependencies for a vanilla installation.

Fetch the script with

    $ curl -o ubuntu-install.sh https://raw.githubusercontent.com/EricssonResearch/calvin-base/master/extras/install/ubuntu-install.sh

And execute with

    $ ./ubuntu-install.sh

Note that this will install Calvin (and dependencies) system-wide. The script accepts a selection of arguments:

    Usage: ./ubuntu-install.sh [-b master/develop] -sweu                                    
            -b      select branch of calvin to install [master]                             
            -s      run calvin at startup [no]                                              
            -w      run web interface at startup [no]                                       
            -e      install raspberry pi example dependencies [no]                          
            -u      install non-raspberry pi example dependencies [no]                      
            -p      replace python-pip (may solve some installation issues) [no]            

For Raspberry Pi users, the flag `-e` is of special importance. It will include all external dependencies requiered for executing the examples. 

#### Example

To have Calvin start on system startup, add the flag `-s` and to have the Calvin web tool available on startup, add `-w`, i.e.

    $ ./ubuntu-install.sh -s -w

This will ensure Calvin is up and running when the system boots, and that a webserver is running, presenting the calvin control GUI on port 8000 on the host. The `-b` flag lets you select which branch of Calvin to use &mdash; the `master` branch is usually more stable, but will often lack some of the more recent additions compared to `develop`. It's up to you which one you go with.

To install some useful dependencies in order to run the examples in `calvin/examples`, add `-u` and, if on a raspberry pi, add `-e`:

    $ ./ubuntu-install.sh -s -w -e -u -p

Note: This will take some time - be patient.

Once the installation is finished, skip ahead to "Running a first example" below.

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

The examples have additional dependencies. See their respective directories.

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

