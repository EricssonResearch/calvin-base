## Brief Introduction to Calvin & CalvinScript


### Install calvin

    $ python setup.py install

### Run script 'test.calvin'

    $ csdeploy test.calvin

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
    output : io.StandardOut()
    
    source.integer > output.token

    $ csdeploy 1st.calvin
    [date] [time] INFO     calvin.StandardOut: StandardOut<[actor uuid]>: 1
    [date] [time] INFO     calvin.StandardOut: StandardOut<[actor uuid]>: 2
    [date] [time] INFO     calvin.StandardOut: StandardOut<[actor uuid]>: 3
    [date] [time] INFO     calvin.StandardOut: StandardOut<[actor uuid]>: 4
    [date] [time] INFO     calvin.StandardOut: StandardOut<[actor uuid]>: 5
    [date] [time] INFO     calvin.StandardOut: StandardOut<[actor uuid]>: 6
    [date] [time] INFO     calvin.StandardOut: StandardOut<[actor uuid]>: 7
    [date] [time] INFO     calvin.StandardOut: StandardOut<[actor uuid]>: 8
    [date] [time] INFO     calvin.StandardOut: StandardOut<[actor uuid]>: 9
    [date] [time] INFO     calvin.StandardOut: StandardOut<[actor uuid]>: 10
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
                "args": {}, 
                "actor_type": "io.StandardOut"
            }, 
            "1st:source": {
                "args": {}, 
                "actor_type": "std.Counter"
            }
        }
    }

### Step 2

#### CalvinScript

    # File 2nd.calvin
    source : std.Counter()
    delay : std.Delay(delay=0.5)
    output : io.StandardOut()
    
    source.integer > delay.token
    delay.token > output.token

### Step 3

#### CalvinScript

    component DelayCounter(delay) -> integer {
    	"""An actor which counts from one, with a delay of delay """
      source : std.Counter()
      delay : std.Delay(delay=delay)
    
      source.integer > delay.token
      delay.token > integer
    }
    
    source : DelayCounter(delay=0.5)
    sink : io.StandardOut()
    
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
                "args": {}, 
                "actor_type": "io.StandardOut"
            }, 
            "3rd:source:delay": {
                "args": {
                    "delay": 0.5
                }, 
                "actor_type": "std.Delay"
            }, 
            "3rd:source:source": {
                "args": {}, 
                "actor_type": "std.Counter"
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
            return ActionResult(tokens_consumed=1, tokens_produced=1, production=(result, ))
    
        action_priority = (multiply, )

#### CalvinScript

    component DelayCounter(delay) -> integer {
      """An actor which counts from one, with a delay of delay """
      source : std.Counter()
      delay : std.Delay(delay=delay)
    
      source.integer > delay.token
      delay.token > integer
    }
    
    source : DelayCounter(delay=0.5)
    mult : erct.Mult(multiplier=2)
    sink : io.StandardOut()
    
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
            return ActionResult(tokens_consumed=2, tokens_produced=1, production=(result, ))
            
        action_priority = (multiply, )

#### CalvinScript
    component DelayCounter(delay) -> integer {
      """An actor which counts from one, with a delay of delay """
      source : std.Counter()
      delay : std.Delay(delay=delay)
    
      source.integer > delay.token
      delay.token > integer
    }
    
    source : DelayCounter(delay=0.5)
    mult : erct.InputMult()
    two : std.Constant(data=2, n=10)
    sink : io.StandardOut()
    
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
            return ActionResult(tokens_consumed=2, tokens_produced=1, production=(result,))
    
        @condition(action_input=[('dividend', 1), ('divisor', 1)], action_output=[('result', 1)])
        @guard(lambda self, n, d: d == 0)
        def divide_by_zero(self, numerator, denumerator):
            result = ExceptionToken("Division by 0")
            return ActionResult(tokens_consumed=2, tokens_produced=1, production=(result,))
    
        action_priority = (divide_by_zero, divide)


#### CalvinScript

    component DelayCounter(delay) -> integer {
      """An actor which counts from one, with a delay of delay """
      source : std.Counter()
      delay : std.Delay(delay=delay)
    
      source.integer > delay.token
      delay.token > integer
    }
    
    source : DelayCounter(delay=0.5)
    div : erct.InputDiv()
    two : std.Constant(data=0, n=10)
    sink : io.StandardOut()
    
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
            return ActionResult(tokens_consumed=1, tokens_produced=2, production = (token, token))
            
        action_priority = (tee,)

#### CalvinScript


    component DelayCounter(delay) -> integer {
    	"""An actor which counts from one, with a delay of delay """
      source : std.Counter()
      delay : std.Delay(delay=delay)
    
      source.integer > delay.token
      delay.token > integer
    }
    
    src : DelayCounter(delay=0.5)
    tee : erct.Tee()
    join : std.Join()
    output : io.StandardOut()
    
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
      delay : std.Delay(delay=delay)
    
      source.integer > delay.token
      delay.token > integer
    }
    
    src : DelayCounter(delay=0.5)
    join : std.Join()
    output : io.StandardOut()
    
    src.integer > join.token_1
    src.integer > join.token_2
    join.token > output.token

### 'Manual' application
    # File tutorial/dist-1.py
    from calvin.runtime.north import calvin_node
    from utilities import utils
    import time
    
    node_1 = calvin_node.dispatch_node(uri="calvinip://localhost:5000", contorl_uri="http://localhost:5001", attributes={'name': 'node-1'})
    
    counter_id = utils.new_actor(node_1, 'std.Counter', 'counter')
    
    output_id = utils.new_actor(node_1, 'io.StandardOut', 'output')

    utils.connect(output_id, 'token', node_2, node_2.id, counter_id, 'integer')
    
    time.sleep(3)
    
    utils.quit(node_1)

### Distributed application

    # File tutorial/dist-2.py
    from calvin.runtime.north import calvin_node
    from utilities import utils
    import time
    
    node_1 = calvin_node.dispatch_node(uri="calvinip://localhost:5000", contorl_uri="http://localhost:5001", attributes={'name': 'node-1'})
    node_2 = calvin_node.dispatch_node(uri="calvinip://localhost:5002", control_uri="http://localhost:5003", attributes={'name': 'node-2'})
    
    counter_id = utils.new_actor(node_1, 'std.Counter', 'counter')

    # send 'new actor' command to node_1
    output_id = utils.new_actor(node_2, 'io.StandardOut', 'output')

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
