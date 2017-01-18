from calvin.actor.actor import Actor, condition


class FaceDetect(Actor) :
    """
    Detect faces in a jpg-image

    Inputs:
        image: Image to analyze
    Outputs:
        faces: non-zero if face detected
    """

    def init(self):
        self.setup()

    def setup(self):
        self.use("calvinsys.media.image", shorthand="image")
        self.image = self["image"]

    def did_migrate(self):
        self.setup()

    @condition(['image'], ['faces'])
    def detect(self, image):
        found = self.image.detect_face(image)
        return (found, )

    action_priority = (detect, )
    requires =  ['calvinsys.media.image']
