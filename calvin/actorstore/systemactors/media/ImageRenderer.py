from calvin.actor.actor import Actor, ActionResult, condition, manage


class ImageRenderer(Actor):

    """
    Render image.

    Inputs:
      image: image to render
    """

    @manage(['width', 'height'])
    def init(self, width=640, height=480):
        self.width = width
        self.height = height
        self.setup()

    def setup(self):
        self.use("calvinsys.media.image", shorthand="image")
        self.image = self["image"]

    def did_migrate(self):
        self.setup()

    def will_end(self):
        self.image.close()

    def will_migrate(self):
        self.image.close()

    @condition(action_input=('image',))
    def render_image(self, image):
        if image is not None:
            self.image.show_image(image, self.width, self.height)
        return ActionResult(production=())

    action_priority = (render_image, )
    requires =  ['calvinsys.media.image']
