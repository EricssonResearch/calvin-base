from calvin.actor.actor import Actor, ActionResult, manage, condition
import requests
import json


class StopLight(Actor):

    """
    Changes light on Philips hue as per input (Red for False, Green for True).

    Inputs:
      state: 0 or 1 for Green/Red
    """

    @manage(['url, state'])
    def init(self, address, username, light=1, initial_state=False):
        self.url = "http://" + address + "/api/" + username + "/lights/" + str(light) + "/state"
        self.state = initial_state
        self.update()

    def update(self):
        data = {'on' : True, 'sat' : 255, 'bri' : 100}
        if self.state :
            data['hue'] = 26000
        else :
            data['hue'] = 1000
        requests.put(self.url, data=json.dumps(data))

    @condition(action_input=['state'])
    def write_state(self, state):
        self.state = state
        self.update()
        return ActionResult(production=())

    action_priority = (write_state, )

