from calvin.actor.actor import Actor, ActionResult, condition


class Environmental(Actor):

    """
    Output temperature, humidity and pressure from sensor
    Inputs:
      trigger: Trigger reading
    Outputs:
      data: Sensor data as string (T:x H:x P:p)
    """

    def init(self):
        self.setup()

    def setup(self):
        self.use("calvinsys.sensor.environmental", shorthand="sensor")
        self.sensor = self["sensor"]

    def did_migrate(self):
        self.setup()

    @condition(action_input=["trigger"], action_output=["data"])
    def get_data(self, input):
        data = "T:%s H:%s P:%s" % (int(self.sensor.get_temperature()),
                                   int(self.sensor.get_humidity()),
                                   int(self.sensor.get_pressure()))
        return ActionResult(production=(data, ))

    action_priority = (get_data, )
    requires = ["calvinsys.sensor.environmental"]
