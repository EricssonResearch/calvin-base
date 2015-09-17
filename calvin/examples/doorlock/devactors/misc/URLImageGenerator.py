from calvin.actor.actor import Actor, ActionResult, manage, condition, guard
import urllib2


class URLImageGenerator(Actor):

    """
    When input trigger goes high fetch image from given URL.

    Inputs:
      trigger: binary input
    Outputs:
      image: generated image
    """

    @manage(['url', 'user', 'passwd'])
    def init(self, url, user="", passwd=""):
        self.url = url
        self.user = user
        self.passwd = passwd
        self.setup()

    def setup(self):
        pwd_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
        if len(self.user) != 0:
            pwd_manager.add_password(None, self.url, self.user, self.passwd)
            handler = urllib2.HTTPBasicAuthHandler(pwd_manager)
            self.opener = urllib2.build_opener(handler)
        else:
            self.opener = urllib2.open

    def did_migrate(self):
        self.setup()

    @condition(action_input=['trigger'], action_output=['image'])
    @guard(lambda self, trigger : trigger)
    def get_image(self, trigger):
        image = self.opener.open(self.url).read()
        return ActionResult(production=(image, ))

    @condition(action_input=['trigger'])
    def empty(self, trigger):
        return ActionResult()

    action_priority = (get_image, empty)

