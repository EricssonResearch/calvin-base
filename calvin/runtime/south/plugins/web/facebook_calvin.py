from calvin.runtime.south.plugins.async.twistedimpl import async, threads
import facebook
from facebook import GraphAPIError
import json
import ast
from datetime import datetime

from calvin.utilities.calvinlogger import get_logger

_log = get_logger(__name__)



class FacebookPost(object):

    def __init__(self):
        self.name = None
        self.link = None
        self.caption = None
        self.description = None
        self.picture = None

    def _try(self, dict):
        try:
            return dict.__dict__
        except:
            return str(dict)

    def to_JSON(self):
        return ast.literal_eval(json.dumps(self, default=lambda val: self._try(val),
                          sort_keys=True, indent=0, separators=(',',':')).replace('\n', ''))


class FacebookUser(object):

    def __init__(self, config):
        self._in_progress = None
        self._previous_message = None
        self._delayed_call = None
        self._next_message = None
        self._time_last_message = None
        self._previous_picture = None
        self._next_picture = None
        self.fb_user = facebook.GraphAPI(access_token=config['access_token'])

    def check_atuhentication(self):
        auth = False

        try:
            self.fb_user.put_like('-1')
            auth = True
        except GraphAPIError as ex:
           if not ex.message.__contains__("Invalid OAuth access token"):
               auth = True
        return auth

    def cb_post_update(self, *args, **kwargs):
        if self._next_message:
            text = self._next_message
            self._next_message = None
            self._post_message(text)
        else:
            self._in_progress = None

    def cb_error(self, *args, **kwargs):
        _log.error("%r %r" % (args, kwargs))
        self._in_progress = None

    def _post_message(self, fb_message):
        (msg, attch) = fb_message
        if not self._in_progress:
            self._in_progress = threads.defer_to_thread(self.fb_user.put_wall_post, message=msg, attachment=attch)
            self._in_progress.addCallback(self.cb_post_update)
            self._in_progress.addErrback(self.cb_error)
            self._time_last_message = datetime.now()
            self._previous_message = (msg, attch)
        else:
            self.next_message = (msg, attch)

    def post_message(self, message, attachment):
        try:
            _log.info('posting message %s' % message)
            if (message, attachment) != self._previous_message:
                if self._delayed_call:
                    self._delayed_call.cancel()
                delay_call = False
                if self._time_last_message:
                    # limit the rate of updates to at most 1 per 10 sec.
                    d = datetime.now() - self._time_last_message
                    if d.seconds < 10:
                        delay_call = True
                if delay_call:
                    self._delayed_call = async.DelayedCall(10, self._post_message, fb_message=(message, attachment))
                else:
                    self._post_message(fb_message=(message, attachment))
            else:
                _log.info("Skipping duplicate message '%s'" % message)
        except Exception as e:
            _log.error('Failed to post message %s because of error: %s' % (message, e.message))

    def cb_picture_update(self, *args, **kwargs):
        if self._next_picture:
            pict = self._next_picture
            self._next_picture = None
            self._post_picture(pict)
        else:
            self._in_progress = None

    def cb_picture_error(self, *args, **kwargs):
        _log.error("%r %r" % (args, kwargs))
        self._in_progress = None

    def _post_picture(self, fb_picture):

        (pict, msg, album) = fb_picture
        if not self._in_progress:
            #_log.info('Posting picture with name %s' % pict)
            fb_pict = open(pict, 'rb')
            if album is None:
                self._in_progress = threads.defer_to_thread(self.fb_user.put_photo, image=fb_pict, message=msg)
            else:
                self._in_progress = threads.defer_to_thread(self.fb_user.put_photo, image=fb_pict, message=msg, album_path= album)
            self._in_progress.addCallback(self.cb_picture_update)
            self._in_progress.addErrback(self.cb_picture_error)
            self._time_last_message = datetime.now()
            self._previous_picture = fb_picture
        else:
            self._next_picture = fb_picture

    def post_picture(self, picture, message, album = None):
        try:
            _log.info('posting message %s with picture %s' % (message, picture))

            if (picture, message, album) != self._previous_picture:
                if self._delayed_call:
                    self._delayed_call.cancel()
                delay_call = False
                if self._time_last_message:
                    # limit the rate of updates to at most 1 per 10 sec.
                    d = datetime.now() - self._time_last_message
                    if d.seconds < 10:
                        delay_call = True
                if delay_call:
                    self._delayed_call = async.DelayedCall(10, self._post_picture, fb_picture=(picture, message, album))
                else:
                    self._post_picture(fb_picture=(picture, message, album))
            else:
                _log.info("Skipping duplicate picture '%s'" % picture)
        except Exception as e:
            _log.error('Failed to post picture %s because of error: %s' % (picture, e.message))
