from calvin.runtime.south.async import sse_event_source as sse
from calvin.requests import calvinresponse

try:
    _eventsource = sse.EventSource(port=7777)
except:
    _eventsource = None


_sensor_callbacks = {}
_sensor_states = {}

_actuators = []

_ui_definitions = {}

def add_ui_actuator(actor, ui_def):
    if ui_def is None:
        ui_def = {"image":"KY-016", "control":{"sensor":False, "type":"boolean", "default":False}}
    _ui_definitions[actor._type] = ui_def

def add_ui_sensor(actor, ui_def):
    if ui_def is None:
        ui_def = {"image":"KY-004", "control":{"sensor":True, "type":"boolean", "default":False}}
    _ui_definitions[actor._type] = ui_def

def register_sensor(actor, callback, ui_def=None):
    if callback:
        _sensor_callbacks[actor._id] = callback
    else:
        try:
            default = ui_def['control']['default']
        except:
            default = 0
        _sensor_states[actor._id] = default;
    add_ui_sensor(actor, ui_def);


def register_actuator(actor, ui_def=None):
    _actuators.append(actor._id)
    add_ui_actuator(actor, ui_def);

def ui_definitions():
    return _ui_definitions

#
# Track/update state
#
def _default_state(actor):
    try:
        state = _ui_definitions[actor._type]['control']['default']
    except:
        state = 0
    return state

def sensor_state(actor):
    return _sensor_states.get(actor._id, _default_state(actor))

# FIXME: Rename update_actor
# Sensors
def update(data):
    actor_id = data.get('client_id')
    state = data.get('state')
    if actor_id in _sensor_callbacks:
        _sensor_callbacks[actor_id](state)
        return calvinresponse.OK
    if actor_id in _sensor_states:
        _sensor_states[actor_id] = state
        return calvinresponse.OK
    return calvinresponse.NOT_FOUND

# Actuators
def update_ui(actor, data):
    if _eventsource and actor._id in _actuators:
        _eventsource.broadcast({"client_id":actor._id, "state":data})
        return calvinresponse.OK
    return calvinresponse.NOT_FOUND


