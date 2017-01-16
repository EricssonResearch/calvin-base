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
        self.trigger = False
        self.pos = 2.5

    @guard(lambda self: trigger is True)
    @condition(action_output=['dutycycle'])
    def move(self, trigger):
        self.trigger = None
        if self.pos == 2.5:
            # right
            self.pos = 12.5
        else:
            # left
            self.pos = 2.5
        return ActionResult(production=(self.pos, ))

    @guard(lambda trigger: self.trigger is None)
    @condition(action_input=['trigger'])
    def empty(self, trigger):
        self.trigger = True if bool(trigger) else None
        return ActionResult()

    action_priority = (move, empty)
