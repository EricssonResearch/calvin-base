import picamera as pi
import time
import datetime
from calvin.runtime.south.plugins.async.twistedimpl import threads
from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)

class CalvinPiCamera(object):

    def __init__(self):
        self.camera = pi.PiCamera()
        self._in_progress = None
        self.picture_taken = False

    def _post_picture(self, *args, **kwargs):
        self.picture_taken = True
        self._in_progress = None

    def _err_picture(self, *args, **kwargs):
        _log.error('%s %s' % (args, kwargs))
        self._in_progress = None

    def get_picture(self):
        self.picture_taken = False
        ts = time.time()
        pict_name = 'picture-%s.jpg' % datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        self._in_progress = threads.defer_to_thread(self.camera.capture, pict_name)
        self._in_progress.addCallback(self._post_picture)
        return pict_name

    def get_picture_stream(self):
        picture = self.get_picture()
        return open(picture).read()

    def close(self):
        self.camera.close()


def register(node=None, actor=None):
    return CalvinPiCamera()