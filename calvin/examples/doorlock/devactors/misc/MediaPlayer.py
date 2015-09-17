from calvin.actor.actor import Actor, ActionResult, manage, condition
import pygame


class MediaPlayer(Actor):

    """
    Play media file  <mediafile>.

    Inputs:
      play: Play <mediafile> when True
    """

    @manage(['media_file'])
    def init(self, media_file):
        self.media_file = media_file
        self.setup()

    def setup(self):
        pygame.mixer.init()
        self.player = pygame.mixer.Sound(self.media_file)
        self.channel = None

    def did_migrate(self):
        self.setup()

    @condition(action_input=('play',))
    def play(self, play):
        if play:
            if self.channel is None or not self.channel.get_busy():
                # not playing anything, start
                self.channel = self.player.play()
            else:
                # we are playing something, ignore
                pass
        return ActionResult(production=())

    action_priority = (play, )

