from calvin.actor.actor import Actor, manage, condition, stateguard

class Datetime(Actor):
    """
    Return a dictionary with current date and time.

    The dictionary contains entries for:
    century, year, month, day, hour, minute, second, timezone

    Input:
      trigger : any token

    Output:
      datetime : dictionary
    """

    @manage()
    def init(self):
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self.use('calvinsys.native.python-time', shorthand='time')

    @condition(['trigger'], ['datetime'])
    def action(self, consume_trigger):
        return (self['time'].datetime(),)

    action_priority = (action,)
    requires = ['calvinsys.native.python-time']
