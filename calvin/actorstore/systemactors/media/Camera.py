from calvin.actor.actor import Actor, ActionResult, manage, condition, guard


class Camera(Actor):

    """
    When input trigger goes high fetch image from given device.

    Inputs:
      trigger: binary input
    Outputs:
      image: generated image
    """

    @manage(['device', 'width', 'height'])
    def init(self, device=0, width=640, height=480):
        self.device = device
        self.width = width
        self.height = height
        self.setup()

    def setup(self):
        self.use("calvinsys.media.camerahandler", shorthand="camera")
        self.camera = self["camera"].open(self.device, self.width, self.height)

    def did_migrate(self):
        self.setup()

    def will_end(self):
        self.camera.close()

    def will_migrate(self):
        self.camera.close()

    @condition(action_input=['trigger'], action_output=['image'])
    @guard(lambda self, trigger : trigger)
    def get_image(self, trigger):
        image = self.camera.get_image()
        return ActionResult(production=(image, ))

    @condition(action_input=['trigger'])
    def empty(self, trigger):
        return ActionResult()

    action_priority = (get_image, empty)
    requires =  ['calvinsys.media.camerahandler']
