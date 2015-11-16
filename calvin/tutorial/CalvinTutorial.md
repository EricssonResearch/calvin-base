## Brief Introduction to Calvin & CalvinScript


### Install calvin

    $ python setup.py install

### Run script 'test.calvin' on localhost

    $ csruntime --host localhost test.calvin

### Install all components in the script to usr namespace

   $ csinstall --all --namespace std test.calvin

### Show documentation for namespace std

    $ csdocs std

### Show documentation for actor Counter in namespace std

    $ csdocs std.Counter

### Step 1

#### CalvinScript


    # File 1st.calvin
    # A small calvin example
    source : std.Counter()
    output : io.Print()
    
    source.integer > output.token

    $ csruntime --host localhost 1st.calvin
    1
    2
    3
    4
    5
    6
    7
    8
    9
    10
    ...

##### Compiled script
    $ cscompile --stdout 1st.calvin
    
    {
        "connections": {
            "1st:source.integer": [
                "1st:output.token"
            ]
        }, 
        "valid": true, 
        "actors": {
            "1st:output": {
                "signature_desc": {
                    "inports": [], 
                    "actor_type": "io.Print", 
                    "is_primitive": true, 
                    "outports": [
                        "token"
                    ]
                }, 
                "args": {}, 
                "actor_type": "io.Print", 
                "signature": "3584ba2b9a1f018a5550dfe32d998572f80b84e9bdab3da30b74146da54cf28d"
            }, 
            "1st:source": {
                "signature_desc": {
                    "inports": [
                        "integer"
                    ], 
                    "actor_type": "std.Counter", 
                    "is_primitive": true, 
                    "outports": []
                }, 
                "args": {}, 
                "actor_type": "std.Counter", 
                "signature": "21cccf799050c37bf9680ec301b59ea583c9070f8051c33f1933f3502e649225"
            }
        }
    }

### Step 2

#### CalvinScript

    # File 2nd.calvin
    source : std.Counter()
    delay : std.ClassicDelay(delay=0.5)
    output : io.Print()
    
    source.integer > delay.token
    delay.token > output.token

### Step 3

#### CalvinScript

    component DelayCounter(delay) -> integer {
    	"""An actor which counts from one, with a delay of delay """
      source : std.Counter()
      delay : std.ClassicDelay(delay=delay)
    
      source.integer > delay.token
      delay.token > integer
    }
    
    source : DelayCounter(delay=0.5)
    sink : io.Print()
    
    source.integer > sink.token

##### Compiled

    $ cscompile --stdout 3rd.calvin
    
    {
        "connections": {
            "3rd:source:source.integer": [
                "3rd:source:delay.token"
            ], 
            "3rd:source:delay.token": [
                "3rd:sink.token"
            ]
        }, 
        "valid": true, 
        "actors": {
            "3rd:sink": {
                "signature_desc": {
                    "inports": [], 
                    "actor_type": "io.Print", 
                    "is_primitive": true, 
                    "outports": [
                        "token"
                    ]
                }, 
                "args": {}, 
                "actor_type": "io.Print", 
                "signature": "3584ba2b9a1f018a5550dfe32d998572f80b84e9bdab3da30b74146da54cf28d"
            }, 
            "3rd:source:delay": {
                "signature_desc": {
                    "inports": [
                        "token"
                    ], 
                    "actor_type": "std.ClassicDelay", 
                    "is_primitive": true, 
                    "outports": [
                        "token"
                    ]
                }, 
                "args": {
                    "delay": 0.5
                }, 
                "actor_type": "std.ClassicDelay", 
                "signature": "5787838e931900c0dd74d6bee2347038577a2677016ed4992c7653889cf1678f"
            }, 
            "3rd:source:source": {
                "signature_desc": {
                    "inports": [
                        "integer"
                    ], 
                    "actor_type": "std.Counter", 
                    "is_primitive": true, 
                    "outports": []
                }, 
                "args": {}, 
                "actor_type": "std.Counter", 
                "signature": "21cccf799050c37bf9680ec301b59ea583c9070f8051c33f1933f3502e649225"
            }
        }
    }
### Step 4

#### Actor `erct/Mult.py`


    from calvin.actor.actor import Actor, ActionResult, manage, condition


    class Mult(Actor):
        """
        Multiples a value on the input with a given multiplier
        Inputs :
            integer : an integer
        Outputs :
            integer : an integer
        """
    
        @manage(['multiplier'])
        def init(self, multiplier):
            self.multiplier = multiplier
    
        @condition(action_input=[('integer', 1)], action_output=[('integer', 1)])
        def multiply(self, data):
            result = self.multiplier * data
            return ActionResult(production=(result, ))
    
        action_priority = (multiply, )

#### CalvinScript

    component DelayCounter(delay) -> integer {
      """An actor which counts from one, with a delay of delay """
      source : std.Counter()
      delay : std.ClassicDelay(delay=delay)
    
      source.integer > delay.token
      delay.token > integer
    }
    
    source : DelayCounter(delay=0.5)
    mult : erct.Mult(multiplier=2)
    sink : io.Print()
    
    source.integer > mult.integer
    mult.integer > sink.token

### Step 5

#### Actor `erct/InputMult.py`

    # File tutorial/erct/InputMult.py
    from calvin.actor.actor import Actor, condition, ActionResult
    
    class InputMult(Actor) :
        """
            Multiplies input on port 'argument' by input in port 'multiplier'
            Inputs :
              multiplier
              argument
            Output :
              result
        """
        def init(self) :
            pass
            
        @condition(action_input=['multiplier', 'argument'], action_output=['result'])
        def multiply(self, multiplier, argument) :
            result = multiplier * argument
            return ActionResult(production=(result, ))
            
        action_priority = (multiply, )

#### CalvinScript

    component DelayCounter(delay) -> integer {
      """An actor which counts from one, with a delay of delay """
      source : std.Counter()
      delay : std.ClassicDelay(delay=delay)
    
      source.integer > delay.token
      delay.token > integer
    }
    
    source : DelayCounter(delay=0.5)
    mult : erct.InputMult()
    two : std.Constant(data=2, n=10)
    sink : io.Print()
    
    source.integer > mult.argument
    two.token > mult.multiplier
    mult.result > sink.token

### Step 6

#### Actor `erct/InputDiv.py`

    from calvin.actor.actor import Actor, condition, guard, ActionResult
    from calvin.runtime.north.calvin_token import ExceptionToken
    
    
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
        @guard(lambda self, n, d: d != 0)
        def divide(self, numerator, denumerator):
            result = numerator / denumerator
            return ActionResult(production=(result,))
    
        @condition(action_input=[('dividend', 1), ('divisor', 1)], action_output=[('result', 1)])
        @guard(lambda self, n, d: d == 0)
        def divide_by_zero(self, numerator, denumerator):
            result = ExceptionToken("Division by 0")
            return ActionResult(production=(result,))
    
        action_priority = (divide_by_zero, divide)


#### CalvinScript

    component DelayCounter(delay) -> integer {
      """An actor which counts from one, with a delay of delay """
      source : std.Counter()
      delay : std.ClassicDelay(delay=delay)
    
      source.integer > delay.token
      delay.token > integer
    }
    
    source : DelayCounter(delay=0.5)
    div : erct.InputDiv()
    two : std.Constant(data=0, n=10)
    sink : io.Print()
    
    source.integer > div.dividend
    two.token > div.divisor
    div.result > sink.token

### Step 7

#### Actor `erct/Tee.py`

    # File: tutorial/erct/Tee.py
    from calvin.actor.actor import Actor, condition, ActionResult
    
    class Tee(Actor) :
        """Sends data on input port to both output ports
        
        Input :
          in
        Output :
          out_1
          out_2
        """
        
        def init(self) :
            pass
        
        @condition(action_input=[('in', 1)], action_output=[('out_1', 1), ('out_2', 1)])
        def tee(self, token) :
            return ActionResult(production = (token, token))
            
        action_priority = (tee,)

#### CalvinScript


    component DelayCounter(delay) -> integer {
    	"""An actor which counts from one, with a delay of delay """
      source : std.Counter()
      delay : std.ClassicDelay(delay=delay)
    
      source.integer > delay.token
      delay.token > integer
    }
    
    src : DelayCounter(delay=0.5)
    tee : erct.Tee()
    join : std.Join()
    output : io.Print()
    
    src.integer > tee.in
    tee.out_1 > join.token_1
    tee.out_2 > join.token_2
    join.token > output.token

### Step 8
#### CalvinScript

    // Use fan-out instead of Tee actor
    component DelayCounter(delay) -> integer {
      """An actor which counts from one, with a delay of delay """
      source : std.Counter()
      delay : std.ClassicDelay(delay=delay)
    
      source.integer > delay.token
      delay.token > integer
    }
    
    src : DelayCounter(delay=0.5)
    join : std.Join()
    output : io.Print()
    
    src.integer > join.token_1
    src.integer > join.token_2
    join.token > output.token

### 'Manual' application

    # File tutorial/dist-1.py
    from calvin.runtime.north import calvin_node
    from utilities import utils
    import time
    
    node_1 = calvin_node.dispatch_node(uri="calvinip://localhost:5000", contorl_uri="http://localhost:5001",
                                       attributes={'indexed_public':
                                            {'owner':{'organization': 'org.testexample', 'personOrGroup': 'me'},
                                             'node_name': {'organization': 'org.testexample', 'name': 'bot'}}})
    
    counter_id = utils.new_actor(node_1, 'std.Counter', 'counter')
    
    output_id = utils.new_actor(node_1, 'io.Print', 'output')

    utils.connect(output_id, 'token', node_2, node_2.id, counter_id, 'integer')
    
    time.sleep(3)
    
    utils.quit(node_1)

### Distributed application

    # File tutorial/dist-2.py
    from calvin.runtime.north import calvin_node
    from utilities import utils
    import time
    
    node_1 = calvin_node.dispatch_node(uri="calvinip://localhost:5000", contorl_uri="http://localhost:5001",
                                       attributes={'indexed_public':
                                            {'owner':{'organization': 'org.testexample', 'personOrGroup': 'me'},
                                             'node_name': {'organization': 'org.testexample', 'name': 'node-1'}}})
    node_2 = calvin_node.dispatch_node(uri="calvinip://localhost:5002", control_uri="http://localhost:5003",
                                       attributes={'indexed_public':
                                            {'owner':{'organization': 'org.testexample', 'personOrGroup': 'me'},
                                             'node_name': {'organization': 'org.testexample', 'name': 'node-2'}}})
    
    counter_id = utils.new_actor(node_1, 'std.Counter', 'counter')

    # send 'new actor' command to node_1
    output_id = utils.new_actor(node_2, 'io.Print', 'output')

    utils.peer_setup(node_1, ["calvinip://localhost:5002"])

    # allow network to stabilize
    time.sleep(1.0)

    # send connect command to node_1
    utils.connect(node_2, output_id, 'token', node_1.id, counter_id, 'integer')

    # run app for 3 seconds
    time.sleep(3.0)

    # send quit to nodes
    utils.quit(node_1)
    utils.quit(node_2)
