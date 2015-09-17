from calvin.actor.actor import Actor, ActionResult, condition, manage
import cv2
import os
import numpy


class FaceDetect(Actor) :
    """
    Detect faces in a jpg-image

    @TODO : Use cv2 rejectLevels to ignore unlikely faces

    Inputs:
        image: Image to analyze
    Outputs:
        faces: non-zero if face detected
    """

    def init(self):
        self.setup()

    def setup(self):
        self.num_images = 0
        linux_prefix = "/usr/share/opencv"
        mac_prefix = "/usr/local/share/OpenCV"
        suffix = "/haarcascades/haarcascade_frontalface_default.xml"
        linux_path = linux_prefix + suffix
        mac_path = mac_prefix + suffix
        
        if os.path.exists(linux_path) :
            cpath = linux_path
        elif os.path.exists(mac_path) :
            cpath = mac_path
        else :
            raise Exception("No Haarcascade found")
        self.classifier = cv2.CascadeClassifier(cpath)

    def did_migrate(self):
        self.setup()

    def decode(self, imdata):
        jpg = numpy.fromstring(imdata, numpy.int8)
        image = cv2.imdecode(jpg, 1)
        return image

    @condition(['image'], ['faces'])
    def detect(self, image):
        image = self.decode(image)
        faces = self.classifier.detectMultiScale(image)
        found = False
        if len(faces) > 0 :
            for (x,y,w,h) in faces :
                if w < 120 :
                    # Too small to be a nearby face
                    continue
                found = True

        return ActionResult(production=(found, ))

    action_priority = (detect, )
