import pytest
import json
from calvin.calvinsys.web.facebook import Facebook, FacebookUser
from facebook import GraphAPIError

"""
Configuration file for automated testing. Change with your credentials file
FACEBOOK_CREDENTIALS = $PATHTO/yourcredentials.json

The file has to be structured like the following

{
    "access_token": "<user access token>",
}
"""
FACEBOOK_CREDENTIALS = '/home/emirkomo/projects/internship/calvin-base/calvin/calvinsys/web/tests/credentials.json'


def test_correct_credentials():
    js_content = open(FACEBOOK_CREDENTIALS).read()
    credentials = json.loads(js_content)
    fb = Facebook("lol","lol")
    assert fb.set_credentials(credentials) is True


def test_wrong_credentials():
    credentials = {'access_token' : 'nonevalue'}
    fb = Facebook("lol","lol")
    assert fb.set_credentials(credentials) is False


@pytest.mark.slow
def test_correct_post_wall():
    credentials = json.loads(open(FACEBOOK_CREDENTIALS).read())
    fb = FacebookUser(credentials)
    msg = {'attachment': {'caption': 'caption',
                              'description': 'description',
                              'link': '',
                              'name': 'hi',
                              'picture': ''},
               'message': 'message_thisshouldwork'}

    assert fb.fb_user.put_wall_post(msg['message'], msg['attachment']) is not None


@pytest.mark.slow
def test_wrong_post_wall():
    credentials = {'access_token' : 'nonevalue'}
    fb = FacebookUser(credentials)
    msg = {'attachment': {'caption': 'caption',
                              'description': 'description',
                              'link': '',
                              'name': 'hi',
                              'picture': ''},
               'message': 'message_thisshouldwork'}

    with pytest.raises(GraphAPIError):
        fb.fb_user.put_wall_post(msg['message'], msg['attachment'])