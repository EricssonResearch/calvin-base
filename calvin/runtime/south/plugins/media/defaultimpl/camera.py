import cv2
import numpy

class Camera(object):

    """
    Capture image from device
    """

    def __init__(self, device, width, height):
        """
        Initialize camera
        """
        self.cap = cv2.VideoCapture(device)
        self.cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, height)

    def get_image(self):
        """
        Captures an image
        returns: Image as jpeg encoded binary string, None if no frame
        """
        ret, frame = self.cap.read()
        if ret:
            ret, jpeg = cv2.imencode(".jpg", frame)
            if ret:
                data = numpy.array(jpeg)
                return data.tostring()

    def close(self):
        """
        Uninitialize camera
        """
        self.cap.release()