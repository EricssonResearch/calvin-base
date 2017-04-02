# Facebook and face detection example #

The following calvinscript uses the PiCamera to shot picture every 0.5 seconds. If a human face is detected
the picture will be uploaded on the user's Facebook wall

	source : std.Counter()
	delay : std.ClassicDelay(delay=0.5)
    msg : std.Constant(data="Alert Message")
    facebook : web.FacebookPicture()
    pi : media.PiCamera()
    detector : media.FaceDetect()
    json : json.FbPictureJson()
    if : std.Select()
    terminator : std.Terminator()
    
    source.integer > delay.token
    delay.token > pi.trigger
    pi.stream > detector.image
    msg.token > json.message
    pi.image > json.picture
    detector.faces > if.select
    json.json > if.data
    if.case_true > facebook.picture
    if.case_false > terminator.void


	
Run the script with 
    $ csruntime --host localhost facebook_detection.calvin --attr-file facebook_credentials.json

where the file `facebook_credentials.json` contains (at least)

	{
		"private": {
			"web": {
				"facebook.com": {
				    "access_token": "<YOUR ACCESS TOKEN>"
			
			}
		}
	}
