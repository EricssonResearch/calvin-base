from calvin.actor.actor import Actor, ActionResult, manage, condition, guard
from calvin.utilities.calvinlogger import get_logger
import nest

_log = get_logger(__name__)


class TestNest(Actor):

    """
    Input:
      username : URL to get
      password : Optional parameters to request as a JSON dictionary
    Output:
      devices : body of request
    """

    @manage()
    def init(self):
        self.nest = None
        self.setup()

    def did_migrate(self):
        self.setup()

    def setup(self):
        self.reset_request()
        #self.use('calvinsys.network.httpclienthandler', shorthand='http')

    def reset_request(self):
        self.request = None
        self.received_headers = False

    @condition(action_input=['username', 'password'])
    @guard(lambda self, username, password: self.nest is None)
    def new_request(self, username, password):
        self.nest = nest.Nest(username, password)
        return ActionResult()

    @condition(action_output=['devices'])
    @guard(lambda self: self.nest is not None)
    def list_devices(self):

        structure = next(iter(self.nest.structures), None)

        if not structure:
            return ActionResult(production=(("no structures",)))

        output = ""
        for device in structure.devices:
            output += device.name + " "
        return ActionResult(production=(output, ))

    action_priority = (new_request, list_devices)



