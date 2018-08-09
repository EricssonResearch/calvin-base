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
import copy
from calvin.utilities import calvinuuid
from calvin.actor import actorport
from calvin.utilities.calvinlogger import get_logger
from calvin.utilities.utils import enum
from calvin.runtime.north.calvin_token import Token, ExceptionToken
# from calvin.runtime.north import calvincontrol
from calvin.runtime.north.replicationmanager import ReplicationId
import calvin.requests.calvinresponse as response
from calvin.runtime.south.async import async
from calvin.runtime.north.plugins.authorization_checks import check_authorization_plugin_list
from calvin.utilities.calvin_callback import CalvinCB
from calvin.csparser.port_property_syntax import get_port_property_capabilities, get_port_property_runtime
from calvin.runtime.north.calvinsys import get_calvinsys
from calvin.runtime.north.calvinlib import get_calvinlib

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

    include_set = set(include) if include else set()
    exclude_set = set(exclude) if exclude else set()

    # Using wrapt since we need to preserve the signature of the wrapped signature.
    # See http://wrapt.readthedocs.org/en/latest/index.html
    # FIXME: Since we use wrapt here, we might as well use it in guard and condition too.
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        # Exclude the instance variables added by superclasses
        exclude_set.update(instance.__dict__)
        x = wrapped(*args, **kwargs)
        if include is None:
            # include set not given, so construct the implicit include set
            include_set.update(instance.__dict__)
            include_set.remove('_managed')
            include_set.difference_update(exclude_set)
        instance._managed.update(include_set)
        return x
    return wrapper


def condition(action_input=[], action_output=[]):
    """
    Decorator condition specifies the required input data and output space.
    Both parameters are lists of port names
    Return value is a tuple (did_fire, output_available, exhaust_list)
    """

    tokens_produced = len(action_output)
    tokens_consumed = len(action_input)

    def wrap(action_method):

        @functools.wraps(action_method)
        def condition_wrapper(self):
            #
            # Check if input ports have enough tokens. Note that all([]) evaluates to True
            #
            input_ok = all(self.inports[portname].tokens_available(1) for portname in action_input)
            #
            # Check if output port have enough free token slots
            #
            output_ok = all(self.outports[portname].tokens_available(1) for portname in action_output)

            if not input_ok or not output_ok:
                return (False, output_ok, ())
            #
            # Build the arguments for the action from the input port(s)
            #
            exhausted_ports = set()
            exception = False
            args = []
            for portname in action_input:
                port = self.inports[portname]
                token, exhaust = port.read()
                is_exception_token = isinstance(token, ExceptionToken)
                exception = exception or is_exception_token
                args.append(token if is_exception_token else token.value )
                if exhaust:
                   exhausted_ports.add(port)
            #
            # Check for exceptional conditions
            #
            if exception:
                # FIXME: Simplify exception handling
                production = self.exception_handler(action_method, args) or ()
            else:
                #
                # Perform the action (N.B. the method may be wrapped in a decorator)
                # Action methods not returning a production (i.e. no output ports) returns None
                # => replace with empty_production constant
                #
                production = action_method(self, *args) or ()

            valid_production = (tokens_produced == len(production))

            if not valid_production:
                #
                # Error condition
                #
                action = "%s.%s" % (self._type, action_method.__name__)
                raise Exception("%s invalid production %s, expected %s" % (action, str(production), str(tuple(action_output))))
            #
            # Write the results from the action to the output port(s)
            #
            for portname, retval in zip(action_output, production):
                port = self.outports[portname]
                port.write_token(retval if isinstance(retval, Token) else Token(retval))

            return (True, True, exhausted_ports)

        return condition_wrapper
    return wrap


def stateguard(action_guard):
    """
    Decorator guard refines the criteria for picking an action to run by stating a function
    with THE SAME signature as the guarded action returning a boolean (True if action allowed).
    If the speciified function is unbound or a lambda expression, you must account for 'self',
    e.g. 'lambda self, a, b: a>0'
    """

    def wrap(action_method):

        @functools.wraps(action_method)
        def guard_wrapper(self, *args):
            if not action_guard(self):
                return (False, True, ())
            return action_method(self, *args)

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


def _implements_state(obj):
    """Helper method to check if foreign object supports setting/getting state."""
    return hasattr(obj, 'state') and callable(getattr(obj, 'state')) and \
        hasattr(obj, 'set_state') and callable(getattr(obj, 'set_state'))

class calvinsys(object):

    """
    Calvinsys interface exposed to actors
    """

    @staticmethod
    def open(actor, name, **kwargs):
        return get_calvinsys().open(name, actor, **kwargs)

    @staticmethod
    def can_write(ref):
        return get_calvinsys().can_write(ref)

    @staticmethod
    def write(ref, data):
        return get_calvinsys().write(ref, data)


    @staticmethod
    def can_read(ref):
        return get_calvinsys().can_read(ref)


    @staticmethod
    def read(ref):
        return get_calvinsys().read(ref)

    @staticmethod
    def close(ref):
        return get_calvinsys().close(ref)


class calvinlib(object):

    """
    CalvinLib interface exposed to actors
    """

    @staticmethod
    def use(name, **kwargs):
        return get_calvinlib().use(name, **kwargs)


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

    # These are the security variables that will always be serialized, see serialize()/deserialize() below
    _security_state_keys = ('_subject_attributes')

    # These are the instance variables that will always be serialized, see serialize()/deserialize() below
    _private_state_keys = ('_id', '_name', '_has_started', '_deployment_requirements',
                           '_signature', '_migration_info', "_port_property_capabilities", "_replication_id")

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

    STATUS = enum('LOADED', 'READY', 'PENDING', 'ENABLED', 'DENIED', 'MIGRATABLE')

    VALID_TRANSITIONS = {
        STATUS.LOADED    : [STATUS.READY],
        STATUS.READY     : [STATUS.PENDING, STATUS.ENABLED, STATUS.DENIED],
        STATUS.PENDING   : [STATUS.READY, STATUS.PENDING, STATUS.ENABLED],
        STATUS.ENABLED   : [STATUS.READY, STATUS.PENDING, STATUS.DENIED],
        STATUS.DENIED    : [STATUS.ENABLED, STATUS.MIGRATABLE, STATUS.PENDING],
        STATUS.MIGRATABLE: [STATUS.READY, STATUS.DENIED]
    }

    test_args = ()
    test_kwargs = {}

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def migration_info(self):
        return self._migration_info

    # What are the arguments, really?
    def __init__(self, actor_type, name='', allow_invalid_transitions=True, disable_transition_checks=False,
                 disable_state_checks=False, actor_id=None, security=None):
        """Should _not_ be overridden in subclasses."""
        super(Actor, self).__init__()
        self._type = actor_type
        self._name = name  # optional: human_readable_name
        self._id = actor_id or calvinuuid.uuid("ACTOR")
        _log.debug("New actor id: %s, supplied actor id %s" % (self._id, actor_id))
        self._deployment_requirements = []
        self._port_property_capabilities = None
        self._signature = None
        self._component_members = set([self._id])  # We are only part of component if this is extended
        self._managed = set()
        self._has_started = False
        # self.control = calvincontrol.get_calvincontrol()
        self._migration_info = None
        self._migrating_to = None  # During migration while on the previous node set to the next node id
        self._migration_connected = True  # False while setup the migrated actor, to prevent further migrations
        self._last_time_warning = 0.0
        self.sec = security
        self._subject_attributes = self.sec.get_subject_attributes() if self.sec is not None else None
        self.authorization_checks = None
        self._replication_id = ReplicationId()
        self._exhaust_cb = None
        self._pressure_event = 0  # Time of last pressure event time (not in state only local)

        self.inports = {p: actorport.InPort(p, self, pp) for p, pp in self.inport_properties.items()}
        self.outports = {p: actorport.OutPort(p, self, pp) for p, pp in self.outport_properties.items()}

        hooks = {
            (Actor.STATUS.PENDING, Actor.STATUS.ENABLED): self._will_start,
            (Actor.STATUS.ENABLED, Actor.STATUS.PENDING): self.will_stop,
        }
        self.fsm = Actor.FSM(Actor.STATUS, Actor.STATUS.LOADED, Actor.VALID_TRANSITIONS, hooks,
                             allow_invalid_transitions=allow_invalid_transitions,
                             disable_transition_checks=disable_transition_checks,
                             disable_state_checks=disable_state_checks)

    def set_authorization_checks(self, authorization_checks):
        self.authorization_checks = authorization_checks

    @verify_status([STATUS.LOADED])
    def setup_complete(self):
        self.fsm.transition_to(Actor.STATUS.READY)

    def init(self):
        raise Exception("Implementing 'init()' is mandatory.")

    def _will_start(self):
        """Ensure will_start() is only called once"""
        if not self._has_started:
            self.will_start()
            self._has_started = True

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

    def _will_end(self):
        if hasattr(self, "will_end") and callable(self.will_end):
            self.will_end()
        get_calvinsys().close_all(self)

    def did_replicate(self, index):
        """Override in actor subclass if actions need to be taken after replication."""
        pass

    def __str__(self):
        ip = ""
        for p in self.inports.values():
            ip = ip + str(p)
        op = ""
        for p in self.outports.values():
            op = op + str(p)
        s = "Actor: '%s' class '%s'\nstatus: %s\ninports: %s\noutports:%s" % (
            self._name, self._type, self.fsm, ip, op)
        return s

    @verify_status([STATUS.READY, STATUS.PENDING, STATUS.ENABLED])
    def did_connect(self, port):
        """Called when a port is connected, checks actor is fully connected."""
        if self.fsm.state() == Actor.STATUS.ENABLED:
            # We already was enabled thats fine now with dynamic port connections
            return
        _log.debug("actor.did_connect BEGIN %s %s " % (self._name, self._id))
        # If we happen to be in READY, go to PENDING
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
        _log.debug("actor.did_connect ENABLED %s %s " % (self._name, self._id))


    @verify_status([STATUS.ENABLED, STATUS.PENDING, STATUS.DENIED, STATUS.MIGRATABLE])
    def did_disconnect(self, port):
        """Called when a port is disconnected, checks actor is fully disconnected."""
        # If the actor is MIGRATABLE, return since it will be migrated soon.
        _log.debug("Actor %s did_disconnect %s" % (self._id, Actor.STATUS.reverse_mapping[self.fsm.state()]))
        if self.fsm.state() == Actor.STATUS.MIGRATABLE:
            return
        # If we happen to be in ENABLED/DENIED, go to PENDING
        if self.fsm.state() != Actor.STATUS.PENDING:
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

    def exhaust(self, callback):
        self._exhaust_cb = callback

    def get_pressure(self):
        _log.debug("get_pressure %s" % self._replication_id.measure_pressure())
        if not self._replication_id.measure_pressure():
            return None
        t = time.time()
        pressure = {}
        for port in self.inports.values():
            for e in port.endpoints:
                PRESSURE_LENGTH = len(e.pressure)
                pressure[port.id + "," + e.peer_id] = {'last': e.pressure_last, 'count': e.pressure_count,
                    'pressure': [e.pressure[i % PRESSURE_LENGTH] for i in range(
                                        max(0, e.pressure_count - PRESSURE_LENGTH), e.pressure_count)]}
        pressure_event = False
        for p in pressure.values():
            if len(p['pressure']) < 2:
                continue
            if ((p['pressure'][-1][1] - p['pressure'][-2][1]) < 10 and
                 p['pressure'][-1][1] > self._pressure_event):
                # Less than 10 sec between queue full and not reported, maybe scale out
                self._pressure_event = max(p['pressure'][-1][1], self._pressure_event)
                pressure_event = True
                break
            if (p['pressure'][-1][1] < (t - 30) and
                p['last'] > p['pressure'][-1][0] + 3 and
                p['pressure'][-1][1] > self._pressure_event):
                # More than 30 sec since queue full, received at least 3 tokens and not reported, maybe scale in
                self._pressure_event = max(p['pressure'][-1][1], self._pressure_event)
                pressure_event = True
                break
        pressure['time'] = t
        _log.debug("get_pressure pressure_event:%s, pressure: %s" % (pressure_event, pressure))
        return pressure if pressure_event else None

    #
    # FIXME: The following methods (_authorized, _warn_slow_actor, _handle_exhaustion) were
    #        extracted from fire() to make the logic easier to follow
    # FIXME: Responsibility of scheduler, not actor class
    #
    def _authorized(self):
        authorized = self.check_authorization_decision()
        if not authorized:
            _log.info("Access denied for actor %s(%s)" % ( self._type, self._id))
            # The authorization decision is not valid anymore.
            # Change actor status to DENIED.
            self.fsm.transition_to(Actor.STATUS.DENIED)
            # Try to migrate actor.
            self.sec.authorization_runtime_search(self._id, self._signature, callback=CalvinCB(self.set_migration_info))
        return authorized

    def _warn_slow_actor(self, time_spent, start_time):
        time_since_warning = start_time - self._last_time_warning
        if time_since_warning < 120.0:
            return
        self._last_time_warning = start_time
        _log.warning("%s (%s) actor blocked for %f sec" % (self._name, self._type, time_spent))

    def _handle_exhaustion(self, exhausted_ports, output_ok):
        _log.debug("actor_fire %s test exhaust %s, %s, %s" % (self._id, self._exhaust_cb is not None, exhausted_ports, output_ok))
        for port in exhausted_ports:
            # Might result in actor changing to PENDING
            try:
                port.finished_exhaustion()
            except:
                _log.exception("FINSIHED EXHAUSTION FAILED")
        if (output_ok and self._exhaust_cb is not None and
            not any([p.any_outstanding_exhaustion_tokens() for p in self.inports.values()])):
            _log.debug("actor %s exhausted" % self._id)
            # We are in exhaustion, got all exhaustion tokens from peer ports
            # but stopped firing while outport token slots available, i.e. exhausted inports or deadlock
            # FIXME handle exhaustion deadlock
            # Initiate disconnect of outports and destroy the actor
            async.DelayedCall(0, self._exhaust_cb, status=response.CalvinResponse(True))
            self._exhaust_cb = None

    @verify_status([STATUS.ENABLED])
    def fire(self):
        """
        Fire an actor.
        Returns tuple (did_fire, output_ok, exhausted)
        """
        #
        # Go over the action priority list once
        #
        for action_method in self.__class__.action_priority:
            did_fire, output_ok, exhausted = action_method(self)
            # Action firing should fire the first action that can fire
            if did_fire:
                break
        return did_fire, output_ok, exhausted

    def enabled(self):
        # We want to run even if not fully connected during exhaustion
        r = self.fsm.state() == Actor.STATUS.ENABLED or self._exhaust_cb is not None
        if not r:
            _log.debug("Actor %s %s not enabled" % (self._name, self._id))
        return r

    def denied(self):
        return self.fsm.state() == Actor.STATUS.DENIED

    def migratable(self):
        return self.fsm.state() == Actor.STATUS.MIGRATABLE

    @verify_status([STATUS.DENIED])
    def enable_or_migrate(self):
        """Enable actor if access is permitted. Try to migrate if access still denied."""
        if self.check_authorization_decision():
            self.fsm.transition_to(Actor.STATUS.ENABLED)
        else:
            # Try to migrate actor.
            self.sec.authorization_runtime_search(self._id, self._signature, callback=CalvinCB(self.set_migration_info))

    # DEPRECATED: Only here for backwards compatibility
    @verify_status([STATUS.ENABLED])
    def enable(self):
        self.fsm.transition_to(Actor.STATUS.ENABLED)

    @verify_status([STATUS.READY, STATUS.PENDING, STATUS.LOADED])
    # DEPRECATED: Only here for backwards compatibility
    def disable(self):
        self.fsm.transition_to(Actor.STATUS.PENDING)

    # TODO verify status should only allow reading connections when and after being fully connected (enabled)
    @verify_status([STATUS.ENABLED, STATUS.READY, STATUS.PENDING, STATUS.MIGRATABLE])
    def connections(self, node_id):
        c = {'actor_id': self._id, 'actor_name': self._name}
        inports = {}
        for port in self.inports.values():
            peers = [
                (node_id, p[1]) if p[0] == 'local' else p for p in port.get_peers()]
            inports[port.id] = peers
        c['inports'] = inports
        outports = {}
        for port in self.outports.values():
            peers = [
                (node_id, p[1]) if p[0] == 'local' else p for p in port.get_peers()]
            outports[port.id] = peers
        c['outports'] = outports
        return c

    def state(self):
        """Serialize custom state, implement in subclass if necessary"""
        return {}

    def set_state(self, state):
        """Deserialize and set custom state, implement in subclass if necessary"""
        pass

    def _private_state(self):
        """Serialize state common to all actors"""
        state = {}
        state['inports'] = {
            port: self.inports[port]._state() for port in self.inports}
        state['outports'] = {
            port: self.outports[port]._state() for port in self.outports}
        state['_component_members'] = list(self._component_members)
        # Place requires in state, in the event we become a ShadowActor
        state['_requires'] = self.requires if hasattr(self, 'requires') else []

        # FIXME: The objects in _private_state_keys are well known, they are private after all,
        #        and we shouldn't need this generic handler.
        for key in self._private_state_keys:
            obj = self.__dict__[key]
            if _implements_state(obj):
                    state[key] = obj.state()
            else:
                state[key] = obj

        state["_calvinsys"] = get_calvinsys().serialize(actor=self)

        return state

    def _set_private_state(self, state):
        """Deserialize and apply state common to all actors"""
        if "_calvinsys" in state:
            get_calvinsys().deserialize(actor=self, csobjects=state["_calvinsys"])
        for port in state['inports']:
            # Uses setdefault to support shadow actor
            self.inports.setdefault(port, actorport.InPort(port, self))._set_state(state['inports'][port])
        for port in state['outports']:
            # Uses setdefault to support shadow actor
            self.outports.setdefault(port, actorport.OutPort(port, self))._set_state(state['outports'][port])
        self._component_members= set(state['_component_members'])

        # FIXME: The objects in _private_state_keys are well known, they are private after all,
        #        and we shouldn't need this generic handler.
        for key in self._private_state_keys:
            if key not in self.__dict__:
                self.__dict__[key] = state.get(key, None)
            else:
                obj = self.__dict__[key]
                if _implements_state(obj):
                    obj.set_state(state.get(key))
                else:
                    self.__dict__[key] = state.get(key, None)

    def _replication_state(self):
        return None

    def _set_replication_state(self, state):
        """Deserialize and apply state related to a replicating actor """
        pass

    def _security_state(self):
        """
        Serialize security state.
        Security state can only contain objects that can be JSON-serialized.
        """
        return {'_subject_attributes':self._subject_attributes}

    def _set_security_state(self, state):
        """
        Deserialize and apply security state.
        Security state can only contain objects that can be JSON-serialized.
        """
        pass

    def _managed_state(self):
        """
        Serialize managed state.
        Managed state can only contain objects that can be JSON-serialized.
        """
        state = {key: self.__dict__[key]  for key in self._managed}
        return state

    def _set_managed_state(self, state):
        """
        Deserialize and apply managed state.
        Managed state can only contain objects that can be JSON-serialized.
        """
        self._managed.update(set(state.keys()))
        for key, val in state.iteritems():
            self.__dict__[key] = val

    def serialize(self):
        """Returns the serialized state of an actor."""
        state = {}
        state['private'] = self._private_state()
        rstate = self._replication_state()
        if rstate is not None:
            state['replication'] = rstate
        state['managed'] = self._managed_state()
        state['security']= self._security_state()
        state['custom'] = self.state()
        return state

    def deserialize(self, state):
        """Restore an actor's state from the serialized state."""
        self._set_private_state(state['private'])
        self._set_replication_state(state.get('replication', None))
        self._set_security_state(state['security'])
        self._set_managed_state(state['managed'])
        self.set_state(state['custom'])

    def exception_handler(self, action, args):
        """Defult handler when encountering ExceptionTokens"""
        _log.error("ExceptionToken encountered\n  name: %s\n  type: %s\n  action: %s\n  args: %s\n" %
                   (self._name, self._type, action.__name__, args))
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
        return len(self._component_members - set([self._id]))>0

    def component_members(self):
        return self._component_members

    def requirements_add(self, deploy_reqs, extend=False):
        if extend:
            self._deployment_requirements.extend(deploy_reqs)
        else:
            self._deployment_requirements = deploy_reqs

    def requirements_get(self):
        if self._port_property_capabilities is None:
            self._port_property_capabilities = self._derive_port_property_capabilities()
        capability_port = [{
                'op': 'port_property_match',
                'kwargs': {'port_property': self._port_property_capabilities},
                'type': '+'
            }]
        if hasattr(self, 'requires') and self.requires:
            capability_require = [{
                'op': 'actor_reqs_match',
                'kwargs': {'requires': self.requires},
                'type': '+'
            }]
        else:
            capability_require = []

        return (self._deployment_requirements + capability_require +
                capability_port + self._replication_id._placement_req)

    def _derive_port_property_capabilities(self):
        port_property_capabilities = set([])
        for port in self.inports.values():
            port_property_capabilities.update(get_port_property_capabilities(port.properties))
        for port in self.outports.values():
            port_property_capabilities.update(get_port_property_capabilities(port.properties))
        _log.debug("derive_port_property_capabilities:" + str(port_property_capabilities))
        return get_port_property_runtime(port_property_capabilities)

    def signature_set(self, signature):
        if self._signature is None:
            self._signature = signature

    def check_authorization_decision(self):
        """Check if authorization decision is still valid"""
        if self.authorization_checks:
            if any(isinstance(elem, list) for elem in self.authorization_checks):
                # If list of lists, True must be found in each list.
                for plugin_list in self.authorization_checks:
                    if not check_authorization_plugin_list(plugin_list):
                        return False
                return True
            else:
                return check_authorization_plugin_list(self.authorization_checks)
        return True

    @verify_status([STATUS.DENIED])
    def set_migration_info(self, reply):
        if reply and reply.status == 200 and reply.data["node_id"]:
            self._migration_info = reply.data
            self.fsm.transition_to(Actor.STATUS.MIGRATABLE)
            _log.info("Migrate actor %s to node %s" % (self._name, self._migration_info["node_id"]))
            # Inform the scheduler that the actor is ready to migrate.
            get_calvinsys().scheduler_maintenance_wakeup()
        else:
            _log.info("No possible migration destination found for actor %s" % self._name)
            # Try to enable/migrate actor again after a delay.
            get_calvinsys().scheduler_maintenance_wakeup(delay=True)

    @verify_status([STATUS.MIGRATABLE, STATUS.READY])
    def remove_migration_info(self, status):
        if status.status != 200:
            self._migration_info = None
            # FIXME: destroy() in actormanager.py was called before trying to migrate.
            #        Need to make the actor runnable again before transition to DENIED.
            #self.fsm.transition_to(Actor.STATUS.DENIED)

    def is_shadow(self):
        return False


class ShadowActor(Actor):
    """A shadow actor try to behave as another actor but don't have any implementation"""
    def __init__(self, actor_type, name='', allow_invalid_transitions=True, disable_transition_checks=False,
                 disable_state_checks=False, actor_id=None, security=None):
        self.inport_properties = {}
        self.outport_properties = {}
        self.calvinsys_state = {}
        self.requires = None
        self._replication_state_data = None
        super(ShadowActor, self).__init__(actor_type, name, allow_invalid_transitions=allow_invalid_transitions,
                                            disable_transition_checks=disable_transition_checks,
                                            disable_state_checks=disable_state_checks, actor_id=actor_id,
                                            security=security)

    @manage(['_shadow_args'])
    def init(self, **args):
        self._shadow_args = args

    def is_shadow(self):
        return True

    def create_shadow_port(self, port_name, port_dir, port_id=None):
        # TODO check if we should create port against meta info
        if port_dir == "in":
            self.inport_properties[port_name] = {}
            port = actorport.InPort(port_name, self)
            self.inports[port_name] = port
        else:
            self.outport_properties[port_name] = {}
            port = actorport.OutPort(port_name, self)
            self.outports[port_name] = port
        return port

    def enabled(self):
        return False

    def did_connect(self, port):
        # Do nothing
        return

    def did_disconnect(self, port):
        # Do nothing
        return

    def requirements_get(self):
        # Get standard actor requirements first
        reqs = super(ShadowActor, self).requirements_get()
        if self._signature and hasattr(self, '_shadow_args') and self.requires is None:
            # Fresh ShadowActor, needs to find placement based on signature
            # Since actor requires is not known locally
            reqs += [{'op': 'shadow_actor_reqs_match',
                     'kwargs': {'signature': self._signature,
                                'shadow_params': self._shadow_args.keys()},
                     'type': '+'}]
        return reqs

    def _set_private_state(self, state):
        """Pop _calvinsys state, set requires and call super class"""
        self.calvinsys_state = state.pop("_calvinsys")
        # Done only in ShadowActor since requires is normally part of the real Actor sub-class
        self.requires = state['_requires']
        super(ShadowActor, self)._set_private_state(state)

    def _private_state(self):
        """Call super class and add stored calvinsys state"""
        state = super(ShadowActor, self)._private_state()
        state["_calvinsys"] = self.calvinsys_state
        return state

    def _set_replication_state(self, state):
        """ Save the replication state, besides ports since they are already handled on the shadow instance """
        super(ShadowActor, self)._set_replication_state(state)
        # Need copy since remove the ports, which is needed for connect
        self._replication_state_data = copy.copy(state)
        if state is None:
            return

    def _replication_state(self):
        return self._replication_state_data
