# -*- coding: utf-8 -*-

# Copyright (c) 2015-2016 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import wrapt
import functools
import time
from calvin.utilities import calvinuuid
from calvin.utilities.security import Security
from calvin.actor import actorport
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.utils import enum
from calvin.runtime.north.calvin_token import Token, ExceptionToken
from calvin.runtime.north import calvincontrol
from calvin.runtime.north import metering

_log = get_logger(__name__)


# Tests in test_manage_decorator.py
def manage(include=None, exclude=None):

    """
    Decorator for Actor::init() providing automatic management of state variables.
    Usage:
        @manage()                     # Manage every instance variable known upon completion of __init__
        @manage(include = [])         # Manage nothing
        @manage(include = [foo, bar]) # Manage self.foo and self.bar only. Equivalent to @manage([foo, bar])
        @manage(exclude = [foo, bar]) # Manage everything except self.foo and self.bar
        @manage(exclude = [])         # Same as @manage()
        @manage(<list>)               # Same as @manage(include = <list>)

    N.B. If include and exclude are both present, exclude will be disregarded.

    """

    if include and type(include) is not list or exclude and type(exclude) is not list:
        raise Exception("@manage decorator: Must use list as argument")

    include = set(include) if include else set()
    exclude = set(exclude) if exclude else set()

    # Using wrapt since we need to preserve the signature of the wrapped signature.
    # See http://wrapt.readthedocs.org/en/latest/index.html
    # FIXME: Since we use wrapt here, we might as well use it in guard and condition too.
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        # Exclude the instance variables added by superclasses
        exclude.update(instance.__dict__)
        x = wrapped(*args, **kwargs)
        if not include:
            # include set not given, so construct the implicit include set
            include.update(instance.__dict__)
            include.remove('_managed')
            include.difference_update(exclude)
        instance._managed.update(include)
        return x
    return wrapper


def condition(action_input=[], action_output=[]):
    """
    Decorator condition specifies the required input data and output space.
    Both parameters are lists of tuples: (port, #tokens consumed/produced)
    Optionally, the port spec can be a port only, meaning #tokens is 1.
    Return value is an ActionResult object

    FIXME:
    - Modify ActionResult to specify how many tokens were read/written from/to each port
      E.g. ActionResult.tokens_consumed/produced are dicts: {'port1':4, 'port2':1, ...}
      Since reading is done in the wrapper, tokens_consumed is fixed and given by action_input.
      The action fills in tokens_produced and the wrapper uses that info when writing to ports.
    - We can keep the @condition syntax by making the change in the normalize step below.
    """
    #
    # Normalize argument list (fill in a default repeat of 1 if not stated)
    #
    action_input = [p if isinstance(p, (list, tuple)) else (p, 1) for p in action_input]
    action_output = [p if isinstance(p, (list, tuple)) else (p, 1) for p in action_output]
    contract_output = tuple(n for _, n in action_output)
    tokens_produced = sum(contract_output)
    tokens_consumed = sum([n for _, n in action_input])

    def wrap(action_method):

        @functools.wraps(action_method)
        def condition_wrapper(self):
            #
            # Check if input ports have enough tokens. Note that all([]) evaluates to True
            #
            input_ok = all(
                [self.inports[portname].available_tokens() >= repeat for (portname, repeat) in action_input]
            )
            #
            # Check if output port have enough free token slots
            #
            output_ok = all(
                [self.outports[portname].available_tokens() >= repeat for (portname, repeat) in action_output]
            )

            if not input_ok or not output_ok:
                _log.debug("%s.%s not runnable (%s, %s)" % (self.name, action_method.__name__, input_ok, output_ok))
                return ActionResult(did_fire=False)
            #
            # Build the arguments for the action from the input port(s)
            #
            args = []
            ex = {}
            for (portname, repeat) in action_input:
                port = self.inports[portname]
                tokenlist = []
                for i in range(repeat):
                    token = port.peek_token()
                    is_exception = isinstance(token, ExceptionToken)
                    if is_exception:
                        ex.setdefault(portname, []).append(i)
                    tokenlist.append(token if is_exception else token.value)
                args.append(tokenlist if len(tokenlist) > 1 else tokenlist[0])

            #
            # Check for exceptional conditions
            #
            if ex:
                action_result = self.exception_handler(action_method, args, {'exceptions': ex})
            else:
                #
                # Perform the action (N.B. the method may be wrapped in a guard)
                #
                action_result = action_method(self, *args)

            valid_production = False
            if action_result.did_fire and (len(contract_output) == len(action_result.production)):
                valid_production = True
                for repeat, prod in zip(contract_output, action_result.production):
                    if repeat > 1 and len(prod) != repeat:
                        valid_production = False
                        break

            if action_result.did_fire and valid_production:
                #
                # Commit to the read from the FIFOs
                #
                for (portname, _) in action_input:
                    self.inports[portname].commit_peek_as_read()
                #
                # Write the results from the action to the output port(s)
                #
                for (portname, repeat), retval in zip(action_output, action_result.production):
                    port = self.outports[portname]
                    for data in retval if repeat > 1 else [retval]:
                        port.write_token(data if isinstance(data, Token) else Token(data))
                #
                # Bookkeeping
                #
                action_result.tokens_consumed = tokens_consumed
                action_result.tokens_produced = tokens_produced
            else:
                #
                # Rewind the read from the FIFOs
                #
                for (portname, _) in action_input:
                    self.inports[portname].peek_rewind()

            if action_result.did_fire and not valid_production:
                action = "%s.%s" % (self._type, action_method.__name__)
                raise Exception("%s invalid production %s, expected %s" % (action, str(action_result.production), str(tuple(action_output))))

            return action_result
        condition_wrapper.action_input = action_input
        condition_wrapper.action_output = action_output
        return condition_wrapper
    return wrap


def guard(action_guard):
    """
    Decorator guard refines the criteria for picking an action to run by stating a function
    with THE SAME signature as the guarded action returning a boolean (True if action allowed).
    If the speciified function is unbound or a lambda expression, you must account for 'self',
    e.g. 'lambda self, a, b: a>0'
    """

    def wrap(action_method):

        @functools.wraps(action_method)
        def guard_wrapper(self, *args):
            retval = ActionResult(did_fire=False)
            guard_ok = action_guard(self, *args)
            _log.debug("%s.%s guard returned %s" % (self.name, action_method.__name__, guard_ok))
            if guard_ok:
                retval = action_method(self, *args)
            return retval

        return guard_wrapper
    return wrap


def verify_status(valid_status_list, raise_=False):
    """
    Decorator to help with debugging of state transitions
    If a decorated is called when the actors status is not in valid_status_list
    it will log (or raise exception if raise_ is True) the attempt.
    """
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        # Exclude the instance variables added by superclasses
        if not instance.fsm.disable_state_checks and instance.fsm.state() not in valid_status_list:
            msg = "Invalid status %s for operation %s" % (instance.fsm, wrapped.__name__)
            if raise_:
                raise Exception(msg)
            else:
                _log.info(msg)
        x = wrapped(*args, **kwargs)
        return x
    return wrapper


class ActionResult(object):

    """Return type from action and @guard"""

    def __init__(self, did_fire=True, production=()):
        super(ActionResult, self).__init__()
        self.did_fire = did_fire
        self.tokens_consumed = 0
        self.tokens_produced = 0
        self.production = production

    def __str__(self):
        fmtstr = "%s - did_fire:%s, consumed:%d, produced:%d"
        return fmtstr % (self.__class__.__name__, str(self.did_fire), self.tokens_consumed, self.tokens_produced)

    def merge(self, other_result):
        """
        Update this ActionResult by mergin data from other_result:
             did_fire will be OR:ed together
             any tokens_consumed will be ADDED
             any tokens_produced will be ADDED
             production will be DISCARDED
        """
        self.did_fire |= other_result.did_fire
        self.tokens_consumed += other_result.tokens_consumed
        self.tokens_produced += other_result.tokens_produced


def _implements_state(obj):
    """Helper method to check if foreign object supports setting/getting state."""
    return hasattr(obj, 'state') and callable(getattr(obj, 'state')) and \
        hasattr(obj, 'set_state') and callable(getattr(obj, 'set_state'))


class Actor(object):

    """
    Base class for all actors
    Need a name supplied.
    Subclasses need to declare the parameter
    calvinsys if they want access to system
    interface on the node, this parameter
    will be supplied by the node and not by user
    """

    # Class variable controls action priority order
    action_priority = tuple()

    # Internal state (status)
    class FSM(object):

        def __init__(self, states, initial, transitions, hooks=None, allow_invalid_transitions=True,
                     disable_transition_checks=False, disable_state_checks=False):
            self.states = states
            self._state = initial
            self.transitions = transitions
            self.hooks = hooks or {}
            self.allow_invalid_transitions = allow_invalid_transitions
            self.disable_transition_checks = disable_transition_checks
            # disable_state_checks is used in the verify_status decorator
            self.disable_state_checks = disable_state_checks

        def state(self):
            return self._state

        def transition_to(self, new_state):
            if new_state in self.transitions[self._state] or self.disable_transition_checks:
                hook = self.hooks.get((self._state, new_state), None)
                if hook:
                    hook()
                self._state = new_state
            else:
                msg = "Invalid transition %s -> %s" % (self, self.printable(new_state))
                if self.allow_invalid_transitions:
                    _log.warning("ALLOWING " + msg)
                    self._state = new_state
                else:
                    raise Exception(msg)

        def printable(self, state):
            return self.states.reverse_mapping[state]

        def __str__(self):
            return self.printable(self._state)

    STATUS = enum('LOADED', 'READY', 'PENDING', 'ENABLED')

    VALID_TRANSITIONS = {
        STATUS.LOADED : [STATUS.READY],
        STATUS.READY  : [STATUS.PENDING, STATUS.ENABLED],
        STATUS.PENDING: [STATUS.READY, STATUS.PENDING, STATUS.ENABLED],
        STATUS.ENABLED: [STATUS.READY, STATUS.PENDING]
    }

    test_args = ()
    test_kwargs = {}

    # What are the arguments, really?
    def __init__(self, actor_type, name='', allow_invalid_transitions=True, disable_transition_checks=False,
                 disable_state_checks=False, actor_id=None):
        """Should _not_ be overridden in subclasses."""
        super(Actor, self).__init__()
        self._type = actor_type
        self.name = name  # optional: human_readable_name
        self.id = actor_id or calvinuuid.uuid("ACTOR")
        _log.debug("New actor id: %s, supplied actor id %s" % (self.id, actor_id))
        self._deployment_requirements = []
        self._signature = None
        self._component_members = set([self.id])  # We are only part of component if this is extended
        self._managed = set(('id', 'name', '_deployment_requirements', '_signature', 'credentials'))
        self._calvinsys = None
        self._using = {}
        self.control = calvincontrol.get_calvincontrol()
        self.metering = metering.get_metering()
        self._migrating_to = None  # During migration while on the previous node set to the next node id
        self._last_time_warning = 0.0
        self.credentials = None

        self.inports = {p: actorport.InPort(p, self) for p in self.inport_names}
        self.outports = {p: actorport.OutPort(p, self) for p in self.outport_names}

        hooks = {
            (Actor.STATUS.PENDING, Actor.STATUS.ENABLED): self.will_start,
            (Actor.STATUS.ENABLED, Actor.STATUS.PENDING): self.will_stop,
        }
        self.fsm = Actor.FSM(Actor.STATUS, Actor.STATUS.LOADED, Actor.VALID_TRANSITIONS, hooks,
                             allow_invalid_transitions=allow_invalid_transitions,
                             disable_transition_checks=disable_transition_checks,
                             disable_state_checks=disable_state_checks)
        self.metering.add_actor_info(self)

    def set_credentials(self, credentials, security=None):
        """ Sets the credentials the actor operates under
            This will trigger an authentication of the credentials
            Optionally an authenticated Security instance can be supplied,
            to reduce the needed authentication processing.
        """
        _log.debug("actor.py: set_credentials: %s" % credentials)
        if credentials is None:
            return
        self.credentials = credentials
        if security:
            self.sec = security
        else:
            self.sec = Security()
            self.sec.set_principal(self.credentials)
            self.sec.authenticate_principal()

    def get_credentials(self):
        _log.debug("actor.py: get_credentials: %s" % self.credentials)
        return self.credentials

    @verify_status([STATUS.LOADED])
    def setup_complete(self):
        self.fsm.transition_to(Actor.STATUS.READY)

    def init(self):
        raise Exception("Implementing 'init()' is mandatory.")

    def will_start(self):
        """Override in actor subclass if actions need to be taken before starting."""
        pass

    def will_stop(self):
        """Override in actor subclass if actions need to be taken before stopping."""
        pass

    def will_migrate(self):
        """Override in actor subclass if actions need to be taken before migrating."""
        pass

    def did_migrate(self):
        """Override in actor subclass if actions need to be taken after migrating."""
        pass

    def will_end(self):
        """Override in actor subclass if actions need to be taken before destruction."""
        pass

    @verify_status([STATUS.LOADED])
    def check_requirements(self):
        """ Checks that all requirements are available and accessable in calvinsys """
        # Check the runtime and calvinsys execution access rights
        # Note when no credentials set no verification done
        if hasattr(self, 'sec') and not self.sec.check_security_actor_requirements(['runtime'] +
                                            (self.requires if hasattr(self, "requires") else [])):
            _log.debug("Security check on actor requirements failed")
            raise Exception('actor calvinsys security requirement not fullfilled')
        # Check availability of calvinsys subsystems
        if hasattr(self, "requires"):
            for req in self.requires:
                if not self._calvinsys.has_capability(req):
                    raise Exception("%s requires %s" % (self.id, req))

    def __getitem__(self, attr):
        if attr in self._using:
            return self._using[attr]
        raise KeyError(attr)

    def use(self, requirement, shorthand):
        self._using[shorthand] = self._calvinsys.use_requirement(self, requirement)

    def __str__(self):
        ip = ""
        for p in self.inports.values():
            ip = ip + str(p)
        op = ""
        for p in self.outports.values():
            op = op + str(p)
        s = "Actor: '%s' class '%s'\nstatus: %s\ninports: %s\noutports:%s" % (
            self.name, self._type, self.fsm, ip, op)
        return s

    @verify_status([STATUS.READY])
    def set_port_property(self, port_type, port_name, port_property, value):
        """Change a port property. Currently, setting 'fanout' on output ports is only allowed operation."""

        if port_type not in ('in', 'out'):
            _log.error("Illegal port type '%s' for actor '%s' of type '%s'" % (port_type, self.name, self._type))
            return False
        ports = self.outports if port_type == 'out' else self.inports
        if port_name not in ports:
            _log.error("Illegal %sport name '%s' for actor '%s' of type '%s'" %
                       (port_type, port_name, self.name, self._type))
            return False
        port = ports[port_name]
        if not hasattr(port, port_property):
            _log.error("Illegal property '%s' for %sport '%s' in actor '%s' of type '%s'" %
                       (port_property, port_type, port_name, self.name, self._type))
            return False
        setattr(port, port_property, value)
        return True

    @verify_status([STATUS.READY, STATUS.PENDING])
    def did_connect(self, port):
        """Called when a port is connected, checks actor is fully connected."""
        # If we happen to by in READY, go to PENDING
        if self.fsm.state() == Actor.STATUS.READY:
            self.fsm.transition_to(Actor.STATUS.PENDING)
        # Three non-patological options:
        # have inports, have outports, or have in- and outports

        if self.inports:
            for p in self.inports.values():
                if not p.is_connected():
                    return

        if self.outports:
            for p in self.outports.values():
                if not p.is_connected():
                    return

        # If we made it here, all ports are connected
        self.fsm.transition_to(Actor.STATUS.ENABLED)

        # Actor enabled, inform scheduler
        self._calvinsys.scheduler_wakeup()

    @verify_status([STATUS.ENABLED, STATUS.PENDING])
    def did_disconnect(self, port):
        """Called when a port is disconnected, checks actor is fully disconnected."""
        # If we happen to by in ENABLED, go to PENDING
        if self.fsm.state() == Actor.STATUS.ENABLED:
            self.fsm.transition_to(Actor.STATUS.PENDING)

        # Three non-patological options:
        # have inports, have outports, or have in- and outports
        if self.inports:
            for p in self.inports.values():
                if p.is_connected():
                    return

        if self.outports:
            for p in self.outports.values():
                if p.is_connected():
                    return

        # If we made it here, all ports are disconnected
        self.fsm.transition_to(Actor.STATUS.READY)

    @verify_status([STATUS.ENABLED])
    def fire(self):
        start_time = time.time()
        total_result = ActionResult(did_fire=False)
        while True:
            # Re-try action in list order after EVERY firing
            for action_method in self.__class__.action_priority:
                action_result = action_method(self)
                total_result.merge(action_result)
                # Action firing should fire the first action that can fire,
                # hence when fired start from the beginning
                if action_result.did_fire:
                    # FIXME: Make this a hook for the runtime too use, don't
                    #        import and use calvin_control or metering in actor
                    self.metering.fired(self.id, action_method.__name__)
                    self.control.log_actor_firing(
                        self.id,
                        action_method.__name__,
                        action_result.tokens_produced,
                        action_result.tokens_consumed,
                        action_result.production)
                    _log.debug("Actor %s(%s) did fire %s -> %s" % (
                        self._type, self.id,
                        action_method.__name__,
                        str(action_result)))
                    break

            if not action_result.did_fire:
                diff = time.time() - start_time
                if diff > 0.2 and start_time - self._last_time_warning > 120.0:
                    # Every other minute warn if an actor runs for longer than 200 ms
                    self._last_time_warning = start_time
                    _log.warning("%s (%s) actor blocked for %f sec" % (self.name, self._type, diff))
                # We reached the end of the list without ANY firing => return
                return total_result
        # Redundant as of now, kept as reminder for when rewriting exeption handling.
        raise Exception('Exit from fire should ALWAYS be from previous line.')

    def enabled(self):
        return self.fsm.state() == Actor.STATUS.ENABLED

    # DEPRECATED: Only here for backwards compatibility
    @verify_status([STATUS.ENABLED])
    def enable(self):
        self.fsm.transition_to(Actor.STATUS.ENABLED)

    @verify_status([STATUS.READY, STATUS.PENDING, STATUS.LOADED])
    # DEPRECATED: Only here for backwards compatibility
    def disable(self):
        self.fsm.transition_to(Actor.STATUS.PENDING)

    @verify_status([STATUS.LOADED, STATUS.READY, STATUS.PENDING])
    def state(self):
        state = {}
        # Manual state handling
        # Not available until after __init__ completes
        state['_managed'] = list(self._managed)
        state['inports'] = {port: self.inports[port]._state()
                            for port in self.inports}
        state['outports'] = {
            port: self.outports[port]._state() for port in self.outports}
        state['_component_members'] = list(self._component_members)

        # Managed state handling
        for key in self._managed:
            obj = self.__dict__[key]
            if _implements_state(obj):
                state[key] = obj.state()
            else:
                state[key] = obj

        return state

    @verify_status([STATUS.LOADED, STATUS.READY, STATUS.PENDING])
    def _set_state(self, state):
        # Managed state handling

        # Update since if previously a shadow actor the init has been called first
        # which potentially have altered the managed attributes set compared
        # with the recorded state
        self._managed.update(set(state['_managed']))

        for key in state['_managed']:
            if key not in self.__dict__:
                self.__dict__[key] = state.pop(key)
            else:
                obj = self.__dict__[key]
                if _implements_state(obj):
                    obj.set_state(state.pop(key))
                else:
                    self.__dict__[key] = state.pop(key)

        # Manual state handling
        for port in state['inports']:
            # Uses setdefault to support shadow actor
            self.inports.setdefault(port, actorport.InPort(port, self))._set_state(state['inports'][port])
        for port in state['outports']:
            # Uses setdefault to support shadow actor
            self.outports.setdefault(port, actorport.OutPort(port, self))._set_state(state['outports'][port])
        self._component_members= set(state['_component_members'])

    # TODO verify status should only allow reading connections when and after being fully connected (enabled)
    @verify_status([STATUS.ENABLED, STATUS.READY, STATUS.PENDING])
    def connections(self, node_id):
        c = {'actor_id': self.id, 'actor_name': self.name}
        inports = {}
        for port in self.inports.values():
            peer = port.get_peer()
            if peer[0] == 'local':
                peer = (node_id, peer[1])
            inports[port.id] = peer
        c['inports'] = inports
        outports = {}
        for port in self.outports.values():
            peers = [
                (node_id, p[1]) if p[0] == 'local' else p for p in port.get_peers()]
            outports[port.id] = peers
        c['outports'] = outports
        return c

    def serialize(self):
        return self.state()

    def deserialize(self, data):
        self._set_state(data)

    def exception_handler(self, action, args, context):
        """Defult handler when encountering ExceptionTokens"""
        _log.error("ExceptionToken encountered\n  name: %s\n  type: %s\n  action: %s\n  args: %s\n  context: %s\n" %
                   (self.name, self._type, action.__name__, args, context))
        raise Exception("ExceptionToken NOT HANDLED")

    def events(self):
        return []

    def component_add(self, actor_ids):
        if not isinstance(actor_ids, (set, list, tuple)):
            actor_ids = [actor_ids]
        self._component_members.update(actor_ids)

    def component_remove(self, actor_ids):
        if not isinstance(actor_ids, (set, list, tuple)):
            actor_ids = [actor_ids]
        self._component_members -= set(actor_ids)

    def part_of_component(self):
        return len(self._component_members - set([self.id]))>0

    def component_members(self):
        return self._component_members

    def requirements_add(self, deploy_reqs, extend=False):
        if extend:
            self._deployment_requirements.extend(deploy_reqs)
        else:
            self._deployment_requirements = deploy_reqs

    def requirements_get(self):
        return self._deployment_requirements + (
                [{'op': 'actor_reqs_match',
                  'kwargs': {'requires': self.requires},
                  'type': '+'}]
                if hasattr(self, 'requires') else [])

    def signature_set(self, signature):
        if self._signature is None:
            self._signature = signature


class ShadowActor(Actor):
    """A shadow actor try to behave as another actor but don't have any implementation"""
    def __init__(self, actor_type, name='', allow_invalid_transitions=True, disable_transition_checks=False,
                 disable_state_checks=False, actor_id=None):
        self.inport_names = []
        self.outport_names = []
        super(ShadowActor, self).__init__(actor_type, name, allow_invalid_transitions=allow_invalid_transitions,
                                            disable_transition_checks=disable_transition_checks,
                                            disable_state_checks=disable_state_checks, actor_id=actor_id)

    @manage(['_shadow_args'])
    def init(self, **args):
        self._shadow_args = args

    def create_shadow_port(self, port_name, port_dir, port_id=None):
        # TODO check if we should create port against meta info
        if port_dir == "in":
            self.inport_names.append(port_name)
            port = actorport.InPort(port_name, self)
            self.inports[port_name] = port
        else:
            self.outport_names.append(port_name)
            port = actorport.OutPort(port_name, self)
            self.outports[port_name] = port
        return port

    def enabled(self):
        return False

    def requirements_get(self):
        # If missing signature we can't add requirement for finding actor's requires.
        if self._signature:
            return self._deployment_requirements + [{'op': 'shadow_actor_reqs_match',
                                                 'kwargs': {'signature': self._signature,
                                                            'shadow_params': self._shadow_args.keys()},
                                                 'type': '+'}]
        else:
            _log.error("Shadow actor %s - %s miss signature" % (self.name, self.id))
            return self._deployment_requirements
