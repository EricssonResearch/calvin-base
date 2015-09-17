from calvin.actor.actor import Actor, ActionResult, condition, manage
import pygame
from StringIO import StringIO


class ImageRenderer(Actor):

    """
    Render image.

    Inputs:
      image: image to render, if not an image, stop showing
    """

    @manage(['size'])
    def init(self, width=640, height=480):
        self.size = (width, height)

    @condition(action_input=('image',))
    def render_image(self, image):
        self.display = pygame.display.set_mode(self.size, 0)
        self.snapshot = pygame.surface.Surface(self.size, 0, self.display)
        img = pygame.image.load(StringIO(image))
        self.display.blit(img, (0, 0))
        pygame.display.flip()
        return ActionResult(production=())

    action_priority = (render_image, )
