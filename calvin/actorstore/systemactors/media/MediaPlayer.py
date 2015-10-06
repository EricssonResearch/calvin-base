from calvin.actor.actor import Actor, ActionResult, manage, condition


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
        self.use("calvinsys.media.mediaplayer", shorthand="player")
        self.player = self["player"]

    def did_migrate(self):
        self.setup()

    def will_migrate(self):
        self.player.close()

    def will_end(self):
        self.player.close()

    @condition(action_input=('play',))
    def play(self, play):
        if play:
            self.player.play(self.media_file)
        return ActionResult(production=())

    action_priority = (play, )
    requires =  ['calvinsys.media.mediaplayer']
    