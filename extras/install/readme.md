# Installation and Getting Started

## Installation

### Debian-based systems, installation script

The following has been tested on Raspbian Jessie (2016-05-27) and Ubuntu 16.04.

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

## Running a first example

Assuming Calvin has been installed and works as expected, create a file named `hello.calvin`, and enter the following:

    /* Actors */
    src : std.Trigger(tick=1.0, data="Hello, world")
    snk : io.Log(loglevel="INFO")
    /* Connections */
    src.data > snk.data

This is an example of _CalvinScript_ which is how an application is described in Calvin. There are two main parts to the script; First, the declaration of actors used in the application, and then a description of how they are connected. In this simple example, there are two actors, called `src` and `snk`. The first actor, `src` is of type `std.Trigger()` with the sole purpose of generating a tick to the system. To this purpose, it takes two parameters, `tick`, which is the interval, in seconds, with which to generate the data, and `data` which is what to output on each tick. The output is then sent on the `data` port of the actor.

The `snk` actor is of type `io.Log()`, it has a single parameter, loglevel, and outputs whatever data it gets on its `data` port to the runtime log.

The documentation of these types can be easily found using the `csdocs` command:

    $ csdocs std.Trigger
    std.Trigger(tick, data): Pass on given _data_ every _tick_ seconds
    Outputs: data

    $ csdocs io.Log
    io.Log(loglevel): Write data to calvin log using specified loglevel.
    Inputs: data                                                        

All valid actors can be inspected using csdocs, and they should all have some form of documentation.

Excute the following from the same directory as the file is located in:

	$ csruntime --host localhost hello.calvin

After a lot of `INFO` messages listing some information of what Calvin has found in the system w.r.t capabilities, the following should appear (the application id and number of lines may differ slightly):

    Deployed application 922a2096-bfd9-48c8-a5a4-ee900a180ca4
    2016-07-11 08:20:34,667 INFO     11202-calvin.Log: Hello, world  
    2016-07-11 08:20:35,667 INFO     11202-calvin.Log: Hello, world

and then Calvin exits. When starting Calvin this way, with a script, there is a default timeout of 3 seconds before exiting. Normally, Calvin should not exit, but when toying around with small scripts, this may be the preferred way of doing it. The timeout can changed:

    $ csruntime --host localhost -w 10 hello.calvin 

will run for 10 seconds before exiting. Use `-w 0` to run forever. 

The `--host` argument is important. For sample scripts, such as this, which only spans a single runtime `localhost`  suffices, but when running a system with several runtimes, it is important that this argument is the IPv4 address of the host running Calvin.

## A second example

We will now have a look at how to make a distributed Calvin application. Create a text file named `hello.deployjson` and enter (or copy & paste) the following:

    {
        "requirements": {
            "src":[{"op":"node_attr_match","kwargs":{"index":["node_name",{"name":"runtime-0"}]},"type":"+"}],
            "snk":[{"op":"node_attr_match","kwargs":{"index":["node_name",{"name":"runtime-1"}]},"type":"+"}]
        }
    }

Then, start two Calvin runtimes, either on the same computer, or on different computers (just make sure they can reach each other via IP)

    $ csruntime --host 192.168.2.3 --port 5000 --controlport 5001 --name runtime-0 &
    $ csruntime --host 192.168.2.3 --port 5002 --controlport 5003 --name runtime-1 &

Of course, you need to replace `192.168.2.3` with the IP of your computer. The `--port` parameter sets the port Calvin will use for its internal runtime to runtime communication, and `--controlport` is the port used for accessing the control api, which we will use to deploy the application. The internal communication uses a Calvin-specific protocol, whereas the control api is based on REST over http.

You can also use the script  `setup_system.sh` in `extras/docker` to setup this same system:

    $ ./setup_system.sh -e 192.168.2.3 -r 1 -n dht  

Now, it is time to deploy the application with the deployment requirements we created earlier. The utility `cscontrol` is a shortcut to the control api. We can deploy an application with it like this:

    $ cscontrol http://192.168.2.3:5001 deploy --reqs hello.deployjson hello.calvin

This will deploy the application, with the `src` actor being placed on runtime-0 and the `snk` actor being placed on runtime-1. When starting `csruntime` from the command line, the output will appear in the console, when using the `setup_system.sh` command, it is logged to a file corresponding to the name of the runtime, i.e. `runtime-0.log` and `runtime-1.log` in this case.

## Writing a component

CalvinScript allows you to group actors together in a component, which can then be used as a short cut when building scripts. For example, using the logging actor we used earlier, say we want to prepend "mylog:" to each logging entry. The script, amended to include this, would be:

    /* Actors */
    src : std.Trigger(tick=1.0, data="Hello, world")
    prefix: text.PrefixString(prefix="mylog:")
    snk : io.Log(loglevel="INFO")
    /* Connections */
    src.data > prefix.in
    prefix.out > snk.data

Then, later, you may find you want that same logging prefix, but on a logger with loglevel "WARNING". Rather than repeating the code, let us wrap it in a component, and parameterize the name and loglevel:

    component MyLog(logname, loglevel) data -> {
        prefix: text.PrefixString(prefix=logname)
        snk : io.Log(loglevel=loglevel)

        .data > prefix.in
        prefix.out > snk.data
    }

This defines a component named `MyLog` with two parameters `logname` and `loglevel`, one inport `data`, and no outports. Note how the ports of a component are used (prefixed with `.` but no actorname.) This component can now be used (almost) as were it an actor. 

    /* Actors */
    src : std.Trigger(tick=1.0, data="Hello, world")
    infolog : MyLog(logname="myinfolog:", loglevel="INFO")
    warnlog : MyLog(logname="mywarnlog:", loglevel="WARNING")
    /* Connections */
    src.data > infolog.data
    src.data > warnlog.data

## Writing an actor

With the currently quite limited (but growing!) selection of actors available, it is inevitable that a calvin developer will eventually end up with a problem which cannot be solved with existing actors, nor with components built from them. Consequently, writing a new actor, from scratch, is necessary. Below is a simple example, see the wiki entry on [Actors](https://github.com/EricssonResearch/calvin-base/wiki/Actors) for more.

Say you have an application where you need to divide two numbers. A straightforward problem which, likely requires two in ports with the numbers, and one output with the result.

    from calvin.actor.actor import Actor, condition, guard, ActionResult
    
    class InputDiv(Actor):
    
        """
          Divides input on port 'dividend' with input on port 'divisor'
          Inputs :
            dividend : integer
            divisor : integer
          Output :
            result
        """
    
        def init(self):
            pass
    
        @condition(action_input=[('dividend', 1), ('divisor', 1)], action_output=[('result', 1)])
        def divide(self, numerator, denumerator):
            result = numerator / denumerator
            return ActionResult(production=(result,))
    
        action_priority = (divide,)

To try it out, create a directory tree and save it there:

    actors/
        math/
            InputDiv.py

By default, calvin only uses pre-installed actors. In order to use this new one, create a file `calvin.conf` with the contents:

    {
      "global": {
        "actor_paths": ["./actors"]
      }
    }

This tells calvin to look for additional actors in the `./actors` directory.

In the same directory, create a script `mathtest.calvin`, with

    ten : std.Constant(data=10)
    five : std.Constant(data=5)
    div : math.InputDiv()
    out : io.Log(loglevel="INFO")

    ten.token > div.dividend
    five.token > div.divisor
    div.result > out.data

(You will note that this is a rather inefficient way of dividing two numbers.)

The directory structure should now be:

    calvin.conf
    mathtest.calvin
    actors/
        math/
            InputDiv.py

Run the application with

    csruntime --host localhost mathtest.calvin

Among the output should be the line

    016-07-11 11:20:39,894 INFO     52645-calvin.Log: 2

which is correct.

But what happens if the divisor is 0? (It will make the application crash.) In order to handle it somewhat gracefully, we add a second action to the actor which checks the input on the ports, and forwards an _exception token_ if the divisor is 0. Edit the file `InputDiv.py` (or copy & paste) to contain the following:

    from calvin.actor.actor import Actor, condition, guard, ActionResult
    from calvin.runtime.north.calvin_token import ExceptionToken
    
    class InputDiv(Actor):
        """
          Divides input on port 'dividend' with input on port 'divisor'
          Inputs :
            dividend : integer
            divisor : integer
          Output :
            result : an integer
        """
    
        def init(self):
            pass
    
        @condition(action_input=[('dividend', 1), ('divisor', 1)], action_output=[('result', 1)])
        @guard(lambda self, n, d: d != 0)
        def divide(self, numerator, denumerator):
            """Normal case, return division"""
            result = numerator / denumerator
            return ActionResult(production=(result,))
    
        @condition(action_input=[('dividend', 1), ('divisor', 1)], action_output=[('result', 1)])
        @guard(lambda self, n, d: d == 0)
        def divide_by_zero(self, numerator, denumerator):
            """Exceptional case: return exception token"""
            result = ExceptionToken("Division by 0")
            return ActionResult(production=(result,))
    
        action_priority = (divide_by_zero, divide)

Changing the script `mathtest.calvin` to

    ten : std.Constant(data=10)
    zero : std.Constant(data=5)
    div : math.InputDiv()
    out : io.Log(loglevel="INFO")

    ten.token > div.dividend
    zero.token > div.divisor
    div.result > out.data

will give the log entry

    2016-07-11 11:41:09,647 INFO     53133-calvin.Log: Exception '<ExceptionToken> Division by 0'

which is far better than a crash.


