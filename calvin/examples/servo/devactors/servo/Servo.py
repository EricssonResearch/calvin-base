from calvin.actor.actor import Actor, ActionResult, condition, guard


class Servo(Actor):
    """
    Move servo 180 degrees when triggered
    Inputs:
      trigger : move servo
    Outputs:
      dutycycle : dutycycle to control servo
    """

    def init(self):
        self.pos = 2.5

    @condition(action_input=['trigger'], action_output=['dutycycle'])
    @guard(lambda self, trigger: trigger)
    def move(self, trigger):
        if self.pos == 2.5:
            # right
            self.pos = 12.5
        else:
            # left
            self.pos = 2.5
        return ActionResult(production=(self.pos, ))

    @condition(action_input=['trigger'])
    def empty(self, trigger):
        return ActionResult()

    action_priority = (move, empty)
