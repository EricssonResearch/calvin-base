from calvin.actor.actor import Actor, ActionResult, manage, condition, guard


class GPIOReader(Actor):

    """
    Read GPIO pin <pin> on RaspberryPi with delay <delay>.

    Outputs:
      state: True/False if input high/low
    """

    @manage(['gpio_pin', 'delay'])
    def init(self, pin, delay):
        self.gpio_pin = pin
        self.delay = delay
        self.timer = None
        self.gpio_lib = None
        self.setup()

    def setup(self):
        try:
            import RPi.GPIO as GPIO
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN, initial=0)
            self.gpio_lib = GPIO
            self.timer = self.calvinsys.events.timer.repeat(self.delay)
        except:
            pass

    def will_end(self):
        if self.timer is not None:
            self.timer.cancel()

    def will_migrate(self):
        if self.timer is not None:
            self.timer.cancel()

    def did_migrate(self):
        self.setup()

    @condition(action_output=('state',))
    @guard(lambda self: self.timer is not None and self.timer.triggered)
    def read_state(self):
        self.timer.ack()
        state = self.gpio_lib.input(self.gpio_pin)
        return ActionResult(production=(state, ))

    action_priority = (read_state, )
