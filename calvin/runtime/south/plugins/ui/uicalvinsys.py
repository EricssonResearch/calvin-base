from calvin.runtime.south.plugins.async import sse_event_source as sse
from calvin.requests import calvinresponse

_eventsource = sse.EventSource(port=7777)


_sensor_callbacks = {}
_sensor_states = {}

_actuators = []

def register_sensor(actor_id, callback):
    if callback:
        _sensor_callbacks[actor_id] = callback
    else:
        _sensor_states[actor_id] = {}

def register_actuator(actor_id):
    print "ui.calvinsys::register_actuator", actor_id
    _actuators.append(actor_id)

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

def update_ui(actor_id, data):
    if actor_id in _actuators:
        _eventsource.broadcast({"client_id":actor_id, "state":data})
        return calvinresponse.OK
    return calvinresponse.NOT_FOUND


