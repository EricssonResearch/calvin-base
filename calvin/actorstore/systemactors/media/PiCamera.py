from calvin.actor.actor import Actor, ActionResult, manage, condition, guard
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class PiCamera(Actor):

    """
    When input trigger goes high fetch image from given device.

    Inputs:
      trigger: binary input
    Outputs:
      stream: image stream
      image: generated image file

    """

    @manage([])
    def init(self):
        self.setup()

    def setup(self):
        self.use("calvinsys.media.camerahandler", shorthand="camera")
        self.camera = self["camera"].open('picamera', None, None)
        self.image = None

    def did_migrate(self):
        self.setup()

    def will_end(self):
        self.camera.close()

    def will_migrate(self):
        self.camera.close()

    @condition(action_input=[], action_output=['stream', 'image'])
    @guard(lambda self: self.image and self.camera.picture_taken)
    def get_image(self):
        _log.info('Opening stream and returning image')
        stream = open(self.image, 'r').read()
        image = self.image
        self.image = None
        return ActionResult(production=(stream, image))

    @condition(action_input=['trigger'], action_output=[])
    @guard(lambda self, trigger: trigger and not self.image)
    def take_picture(self, trigger):
        _log.info('Taking picture from PiCamera')
        self.image = self.camera.get_picture()
        return ActionResult()


    action_priority = (take_picture, get_image)
    requires =  ["calvinsys.media.camerahandler"]