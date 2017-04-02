# Facebook examples #

The following calvinscript uses the [http://www.facebook.com](Facebok) API to post a status:

	msg : std.Constant(data={"attachment": {"caption": "This is a test", "description": "Sample script from a Calvin Actor", "link": "https://github.com/EricssonResearch/calvin-base","name": "Calvin", "picture": "http://www.ericsson.com/research-blog/wp-content/uploads/2015/07/Calvin_2-feature.png"},"message": "Hello from Calvin"})
	facebook : web.FacebookPost()
	msg.token > facebook.status

This one instead is for posting a picture
	
	msg : std.Constant(data={"picture" : "/pathtopicture/picture.jps", "message" : "This is Calvin" })
	facebook : web.FacebookPicture()
	msg.token > facebook.picture
	
	

In order to post a status on Facebook you need an application registered or an authentication token for the user wall you wanto to post on

    $ csruntime --host localhost facebook.calvin --attr-file facebook_credentials.json
    $ csruntime --host localhost facebook_picture.calvin --attr-file facebook_credentials.json

where the file `facebook_credentials.json` contains (at least)

	{
		"private": {
			"web": {
				"facebook.com": {
				    "access_token": "<YOUR ACCESS TOKEN>"
			
			}
		}
	}
