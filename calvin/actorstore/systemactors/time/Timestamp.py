from calvin.actor.actor import Actor, ActionResult, manage, condition, guard

class Timestamp(Actor):
    """
    Return the (UTC) time in seconds since Jan 1st 1970

    Detailed information

    Input:
      trigger : any token

    Output:
      timestamp : floating point number
    """

    @manage()
    def init(self):
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self.use('calvinsys.native.python-time', shorthand='time')

    @condition(['trigger'], ['timestamp'])
    def action(self, consume_trigger):
        return ActionResult(production=(self['time'].timestamp(),))

    action_priority = (action,)
    requires = ['calvinsys.native.python-time']
