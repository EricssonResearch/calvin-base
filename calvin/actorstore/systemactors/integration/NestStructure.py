from calvin.actor.actor import Actor, ActionResult, manage, condition, guard
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)


class NestStructure(Actor):
    """
    Calvin Actor which acts as a Nest Structure. Possible operations (at the moment):
        -List all devices
        ... more coming!

    Inputs:
        structure_name: the structure's to analyze
        operation: the operation input to run (list,..., more coming)

    Outputs:
        devices: the list of the devices available in the structure
    """

    @manage()
    def init(self):
        self.structure_name = None
        self.operation = None
        self.setup()

    def setup(self):
        self.use('calvinsys.integration.nest', shorthand='nest')
        self.structure = None
        self.nest = self['nest']

    def did_migrate(self):
        self.setup()

    @condition(action_input=['structure_name'], action_output=[])
    @guard(lambda self, structure_name:self.nest is not None and self.structure is None)
    def set_structure(self, structure_name):
        self.structure_name = structure_name
        self.structure = self['nest'].get_structure_by_name(self.structure_name)
        return ActionResult()

    @condition(action_input=['operation'], action_output=[])
    @guard(lambda self, operation: self.operation is None)
    def set_operation(self, operation):
        self.operation = True
        return ActionResult()

    @condition([], ['devices'])
    @guard(lambda self:self.nest._in_progress is None and self.structure is not None and self.operation == "list")
    def get_devices(self):
        res = self['nest'].list_devices_by_structure(self.structure_name)
        self.operation = None
        return ActionResult(production=(res,))

    action_priority = (set_structure, set_operation, get_devices)
    requires = ['calvinsys.integration.nest']
