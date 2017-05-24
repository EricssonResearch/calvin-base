from calvin.runtime.south.plugins.io.led import led

class LED():

    """
    LED
    """

    def __init__(self, node, actor):
        self.led = led.LED(node, actor)

    def set_state(self, state):
        self.led.set_state(state)


def register(node=None, actor=None):
    """
        Called when the system object is first created.
    """
    return LED(node=node, actor=actor)
