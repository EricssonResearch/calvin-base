from calvin.requests import calvinresponse


_sensor_callbacks = {}
_sensor_states = {}

def register_sensor(actor_id, callback):
    if callback:
        _sensor_callbacks[actor_id] = callback
    else:
        _sensor_states[actor_id] = {}

    print _sensor_callbacks, _sensor_states


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
