from calvin.runtime.south.plugins.web.facebook_calvin import FacebookUser
from calvin.utilities.calvinlogger import get_logger


_log = get_logger(__name__)


class Facebook(object):
    """
    Facebook module for uploading posts and pictures

    example of a credential json file
    {
        'access_token': 'your_access_token'
    }

    Also posts and pictures are uploaded as json files

    post
    {
        'message': 'your_message',
        'attachment':{
                'name' : 'post_name',
                'caption' : 'post_caption,
                'link' : 'post_link'
                'description' : 'post_description',
                'picture' : 'http://post_picture'
            }
    }
    for the attachment see FacebookPost class for a simpler use

    picture
    {
        'picture':'picture_path',
        'message' : 'message for the post',
        'album' : 'album(optional)'
    }
    """
    def __init__(self, node, actor):
        self._node = node
        self._actor = actor

        try:
            credentials = self._node.attributes.get_private("/web/facebook.com")
        except Exception as e:
            _log.error("Credentials not accessible. Error message %s" % e.message)
            credentials = None

        if credentials:
            self._fb = FacebookUser(config=credentials)
            _log.info("Successfully received credentials from node")
        else:
            _log.warning("Expected credentials /private/web/facebook.com not found")
            self._fb = None

    def set_credentials(self, facebook_credentials):
        if not self._fb:
            self._fb = FacebookUser(config=facebook_credentials)
            success = self._fb.check_atuhentication()
        else :
            _log.warning("Credentials already supplied - ignoring")
            success = False
        return success

    def post_update(self, text):
        if not self._fb:
            _log.warning("Credentials not set, cannot post")
            return
        self._fb.post_message(text['message'], text['attachment'])

    def post_picture(self, picture):
        if not self._fb:
            _log.warning("Credentials not set, cannot post")
            return
        if picture.__contains__('album'):
            self._fb.post_picture(picture['picture'].encode('utf-8'), picture['message'].encode('utf-8'), picture['album'].encode('utf-8'))
        else:
            self._fb.post_picture(picture['picture'].encode('utf-8'), picture['message'].encode('utf-8'))


def register(node, actor):
    return Facebook(node, actor)
