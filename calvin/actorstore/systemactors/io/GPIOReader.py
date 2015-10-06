from calvin.actor.actor import Actor, ActionResult, manage, condition, guard


class GPIOReader(Actor):

    """
    Read state of GPIO pin <pin>

    Outputs:
      state: 1/0 if input high/low
    """

    @manage(['gpio_pin', 'delay'])
    def init(self, gpio_pin, delay=0.2):
        self.gpio_pin = gpio_pin
        self.delay = delay
        self.gpio = None
        self.setup()

    def setup(self):
        self.use("calvinsys.io.gpiohandler", shorthand="gpiohandler")
        self.gpio = self["gpiohandler"].open(self.gpio_pin, "in", self.delay)

    def will_migrate(self):
        self.gpio.close()

    def will_end(self):
        self.gpio.close()

    def did_migrate(self):
        self.setup()

    @condition(action_output=('state',))
    @guard(lambda self: not self.gpio is None and self.gpio.has_changed())
    def read_state(self):
        state = self.gpio.get_state()
        return ActionResult(production=(state, ))

    action_priority = (read_state, )
    requires = ['calvinsys.io.gpiohandler']
