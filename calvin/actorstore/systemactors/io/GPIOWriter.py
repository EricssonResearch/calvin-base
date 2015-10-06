from calvin.actor.actor import Actor, ActionResult, manage, condition


class GPIOWriter(Actor):

    """
    Set state of GPIO pin <pin>.
    Input:
      state : 1/0 for high/low
    """

    @manage(["gpio_pin"])
    def init(self, gpio_pin):
        self.gpio_pin = gpio_pin
        self.setup()

    def setup(self):
        self.use("calvinsys.io.gpiohandler", shorthand="gpiohandler")
        self.gpio = self["gpiohandler"].open(self.gpio_pin, "out")

    def will_migrate(self):
        self.gpio.close()

    def will_end(self):
        self.gpio.close()

    def did_migrate(self):
        self.setup()

    @condition(action_input=("state",))
    def set_state(self, state):
        self.gpio.set_state(state)
        return ActionResult()

    action_priority = (set_state, )
    requires = ["calvinsys.io.gpiohandler"]
