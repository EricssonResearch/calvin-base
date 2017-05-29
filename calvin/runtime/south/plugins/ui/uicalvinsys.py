from calvin.runtime.south.plugins.async import sse_event_source as sse
from calvin.requests import calvinresponse

_eventsource = sse.EventSource(port=7777)


_sensor_callbacks = {}
_sensor_states = {}

_actuators = []

_ui_definitions = {}

_default_ui_def = {"image":"", "controls":[{"sensor":False, "type":"boolean"}]}

def add_ui_actuator(actor, ui_def):
    if ui_def is None:
        ui_def = _default_ui_def.copy()
        ui_def['image'] = "default_actuator"
    _ui_definitions[actor._type] = ui_def

    print ui_definitions()


def add_ui_sensor(actor, ui_def):
    if ui_def is None:
        ui_def = _default_ui_def.copy()
        ui_def['image'] = "default_sensor"
        ui_def['controls'][0]['sensor'] = True
    _ui_definitions[actor._type] = ui_def

    print ui_definitions()


def register_sensor(actor, callback, ui_def=None):
    if callback:
        _sensor_callbacks[actor._id] = callback
    else:
        _sensor_states[actor._id] = {}
    add_ui_sensor(actor, ui_def);


def register_actuator(actor, ui_def=None):
    _actuators.append(actor._id)
    add_ui_actuator(actor, ui_def);


def ui_definitions():
    return _ui_definitions


# FIXME: Rename update_actor
def update(data):
    actor_id = data.get('client_id')
    state = data.get('state')
    if actor_id in _sensor_callbacks:
        _sensor_callbacks[actor_id](state)
        return calvinresponse.OK
    if actor_id in _sensor_states:
        _sensor_states[actor_id] = state
        return calvinresponse.OK


def update_ui(actor, data):
    if actor._id in _actuators:
        _eventsource.broadcast({"client_id":actor._id, "state":data})
        return calvinresponse.OK
    return calvinresponse.NOT_FOUND


