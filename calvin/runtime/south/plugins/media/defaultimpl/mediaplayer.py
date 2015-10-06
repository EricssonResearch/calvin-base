import pygame


class MediaPlayer(object):

    """
    Play media file
    """

    def __init__(self):
        self.channel = None
        pygame.mixer.init()

    def play(self, media_file):
        """
        Play media file
        """
        self.player = pygame.mixer.Sound(media_file)
        if self.channel is None or not self.channel.get_busy():
            self.channel = self.player.play()

    def close(self):
        """
        Close player
        """
        if not self.channel is None:
            self.channel.stop()
