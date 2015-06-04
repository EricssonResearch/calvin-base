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

## Quick start

### Download

The latest version of Calvin can be found on [github](https//github.com/EricssonResearch/calvin-base).

### Setup

To install Calvin, use the accompanying `setup.py`

    $ python setup.py install

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

Install the extra packages needed for testing

    $ pip install -r test-requirements.txt

Run the essential test suite

    $ py.test -m essential

Run the quick test suite

    $ py.test -m "not slow"


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

## Calvin internals overview 

This section deals with developing Calvin internals, for information on how to
develop actors, or applications using CalvinScript, see sections 'Writing
Actors in Python' and 'Writing CalvinScript Applications', respectively below. 

## Assumptions on a Calvin application

* An _application_ is a set of actors and a graph describing the connections
* The application graph is static during application lifetime
* Actor _classes_ are uniquely identifiable
* Actor _instances_ are uniquely identifiable
* If a actor instance is migrated it retains its unique id
* Actors run on "nodes"
* Actors communicate over _ports_
* Input ports have a one-to-one relation to an output port
* Output ports may have a one-to-many relation (fan-out) to their input port(s)
* Fan-out delivers same sequence to all readers (see open issues)

## Writing Actors in Python
A new actor can be developed easily by inheriting from the `Actor` class, which holds
similarity to CAL actors, if one is familiar with them.

### An actor

The following is an example of an actor. In this case, the only function is to pass any token recived
on the inport to the outport, optionally printing it to standard out.

    from calvin.actor.actor import Actor, ActionResult, manage, condition

    class Identity(Actor):
        """
        forward a token unchanged
        Inputs:
          token : a token
        Outputs:
          token : the same token
        """
        @manage(['dump'])
        def init(self, dump = False):
            self.dump = dump

        def log(self, data) :
            print "%s<%s>: %s" % (self.__class__.__name__, self.id, data)

        @condition(['token'], ['token'])
        def donothing(self, input):
            if self.dump : self.log(input)
            return ActionResult(tokens_consumed=1, tokens_produced=1, production=( input, ))

        action_priority = ( donothing, )


#### Actor breakdown

The first lines import the necessary parts of the Actor module.

    from calvin.actor.actor import Actor, ActionResult, manage, condition

Here, `Actor` is the base class of all actors and should always be included.
`ActionResult` is how an action reports its result to the runtime, including
how many tokens where consumed, many where produced, and of course what those
produced were.

The `manage` decorator is used to inform the runtime which attributes of the
actor should be automatically managed when migrating, and the `condition`
decorator specifies how many tokens are needed on in-ports and how much space
is required on out-ports before an action can fire. The `condition` decorator also
serves the dual purpose of specifying that the decorated function actually is an action.


An actor should _always_ inherit from the `Actor` base class.

    class Identity(Actor):

The docstring of the actor defines the ports and their names. _Note:_ This is
__required__ as it is the only way of defining ports. In this example there is
one in-port, named `token`, and one out-port, also named `token`. The `Inputs:`
and `Outputs:` headings are optional if no ports listed under heading. For
aesthetical reasons the plural 's' in the headings is optional, as is the
capitalization of the words. Also optionally document the port after the port
string. At least a whitespace is required after the portname, but the
convention is to separate port name and port documentation by " : ", i.e.
`space colon space`. It is a convention to use lowercase letters for ports,
unless there is good reason not to, e.g. a port taking a URL as input.

        """
        forward a token unchanged
        Inputs:
          token : a token
        Outputs:
          token : the same token
        """

The `manage` decorator, here used in its simplest form - giving a list of
attributes to manage. Optionally, it could be written `@manage( include =
['dump'] )`. If there are a multitude of attributes, all of which should be
included, an empty argument list, i.e. `@manage()` will ensure all of them are
included. It is also possible to only specify which attributes should be
excluded. See the documentation for `Actor.actor.manage` for further details.

        @manage(['dump'])

The `init` method serves the same purpose for actors as `__init__` does for
python classes, to initialize attributes. This is the first method called
after an actor is created and has access to all actor specific methods.
Any attribute which exists after `init` returns can be managed (see above)

        def init(self, dump = False):
            self.dump = dump

It is of course possible to define and call any number of methods in an actor.

        def log(self, data) :
            print "%s<%s>: %s" % (self.__class__.__name__, self.id, data)

An action is defined by the `@condition` decorator. In this case, it expects
one token on the in-port `token`, and one available slot on the out-port, 
also named `token`. The argument list here is actually a shortened version
of `@condition( action_input = [ ('token', 1) ], action_output = [ ('token', 1) ]`
meaning the action has as input one token from in-port 'token' and will produce one
token on out-port 'token'. See documentation for `Actor.actor.condition`.

        @condition(['token'], ['token'])

Omitted in this action is the `guard` decorator. Whereas `condition` only does a superficial
examination of the ports (number of tokens available on in-ports and space left on out-ports, mainly)
the `guard` has full access to the tokens and can examine them more thoroughly. For example, it would
be possible to handle input differently based on type by including a guard
    @guard(lambda self, a : isinstance(a, str))
on an action, and it would only be applied when the token on the in-port is a string. The
guard will always have the same signature as the action.

        def donothing(self, input):
            if self.dump : self.log(input)

The `ActionResult` returns the result of the action to the runtime. Here, one token was consumed,
one was produced, and the tokens produced is given as a sequence. [@TODO elaborate] 

            return ActionResult(tokens_consumed=1, tokens_produced=1, production=( input, ))

Finally, `action_priority` determines the priority of the actions. This is the
order in which `conditions` (and `guards`) will be evaluated to see which
actions fire. Whenever an action fires, this can cause actions of higher
priority to be ready to fire, and thus the sequence will be iterated,
restarting whenever an action fires, until no action has fired for a full
iteration.

        action_priority = ( donothing, )


## Writing CalvinScript Applications

The structure of a CalvinScript is as follows:

1. an optional list of component declarations
2. an optional program 

### A CalvinScript program

A program consists of a list of instantiations and a list of connections (and comments).

An instantiation (of an actor) is is a statement of the form:

    <actor>:<Namespace>.<ActorType>(<named_argument_list>)

e.g.

    src:std.Counter()
    output1:io.StandardOut()

where we have created two actors, `src` and `output1` of type `Counter` and
`StandardOut`, belonging to the `std` and `io` namespace, respectively.

A connection describes how actors are connected over ports using the form:

    <actor>.<outport> > <actor>.<inport>

e.g.

    src.integer > output1.token

where the integer sequence produced by `src` on its `integer` output port is
connected to the `token` input port of the `output1` actor.
The resulting application will write a sequence of integer to the log.

Together, the instantiations and connections describe the application graph.

### A CalvinScript component declaration

To provide a means for hierarchy and reuse, it is possible to declare _components_ in CalvinScript.

A component declaration has the form:

    component <ComponentName>(<argname_list>) <inport_list> -> <outport_list> {
      <program>
    }

Reading the above from left to right we have a keyword `component`, a name for
the new component, a possibly empty list of the names of the arguments to the
component instantiation, a list of input port names and a list of output port
names (either of which may be empty), and a CalvinScript program between the
curly brackets.

As always, an example might be useful:

    component DelayedCounter(delay) -> integer {
      """
      Produce a sequence of numbers with a short delay inbetween numbers
      """
    
      ctr : std.Counter()
      delay : std.Delay(delay = delay)

      ctr.integer > delay.token
      delay.token > integer
    }
    
    dctr : DelayedCounter(delay=0.5)
    out  : StandardOut()

    dctr.integer > out.token


In the above script, the component is immediately usable since it is defined in
the same source file as the program using it. For other users to enjoy its
benefits, it can be installed locally. To install a component, use the compiler
with the `--install` directive on the file where one or more components was
defined, together with the namespace under which to install the components. NB.
Only components will ever be installed, never scripts themselves nor the
program following the component declaration.

Example:

    $ csinstall --script script.calvin --all --namespace usr

This will install all components found in script `script.calvin` in namespace `usr`.
These will behave just like any other actor, and can be used by other scripts.

## The Compiler, the Deployer, and the Actor Store

The *compiler*, `cscompile` will compile a CalvinScript source file into a
JSON representation. By default, the output will be written to a file with the
same name as the input file, but with the extension replaced by 'json' instead
of whatever extension the input file had (if any).

For up-to-date information, run it with an `-h` argument.

In general, most of the time the *deployer* is used instead of directly invoking the compiler.

Invoking

    $ csdeploy <scriptfile>

with a CalvinScript file as argument will invoke the compiler for you, and then
run the resulting application. It will be silent except for prints to standard
output by default. Include `-v` to get more detailed information on the
execution. Also note that the program will exit after 3 seconds.

Finally, the *actor store* is where we can find documentation about actors.

    $ csdocs std.Join

will show the documentation for `Join` in the `std` namespace:

    std.Join(): Join two streams of tokens
    Inputs: token_1, token_2
    Outputs: token

It is also possible to get a more verbose description in markdown format:

    $ csdocs --format detailed std.Join

    #### std.Join()
    
    Join two streams of tokens
    
    
    ##### Inputs
    
    token_1
    :    first token stream
    
    token_2
    :    second token stream
    
    ##### Outputs
    
    token
    :    resulting token stream

For components, additional information on which actors they make use of is included:

    $ csdocs std.DelayedCounter

    std.DelayedCounter(delay): Counts from 0 and up, waiting 'delay' seconds between numbers
    Requires: std.Delay, std.Counter
    Outputs: integer

## Open issues

Several







