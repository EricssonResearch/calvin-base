from calvin.actor.actor import Actor, manage, condition, stateguard


class StrfTime(Actor):
    """
    Return the current time as a string

    Detailed information

    Input:
      trigger : any token

    Output:
      timestamp : a string on the choosen format
    """

    @manage()
    def init(self, formating):
        self.setup(formating)

    def did_migrate(self):
        self.setup()

    def setup(self, formating):
        self.formating = formating
        self.use('calvinsys.native.python-time', shorthand='time')

    @condition(['trigger'], ['timestamp'])
    def action(self, consume_trigger):
        return (self['time'].strftime(self.formating),)

    action_priority = (action,)
    requires = ['calvinsys.native.python-time']
